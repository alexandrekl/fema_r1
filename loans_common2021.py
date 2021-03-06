#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Aoril 12 2021
Common code for loans_BLS_2021.ipynb
Main difference from loans_common.py: Column names in PPP data changed substantially
@author: aligo
"""

import glob
import pandas as pd
import zipfile
import numpy as np
#import fuzzymatcher


NEstates = ['CT','MA','ME','NH','RI','VT']
NEstfips = ['09','25','23','33','44','50']

def OverrideNAICS2(df):
    # adjusts 2-digit NAICS that are joint, e.g. NAICS 31-33 Manufacturing
    df.loc[df['NAICS2'].eq('31'),'NAICS2'] = '31-33'
    df.loc[df['NAICS2'].eq('33'),'NAICS2'] = '31-33'
    df.loc[df['NAICS2'].eq('44'),'NAICS2'] = '44-45' # NAICS 44-45 Retail trade
    df.loc[df['NAICS2'].eq('45'),'NAICS2'] = '44-45' # NAICS 44-45 Retail trade
    df.loc[df['NAICS2'].eq('48'),'NAICS2'] = '48-49' # 	NAICS 48-49 Transportation and warehousing
    df.loc[df['NAICS2'].eq('49'),'NAICS2'] = '48-49' # 	NAICS 48-49 Transportation and warehousing
    return df

def ReadPPPdata(naics, fpath):
    # read PPP loan data

    csv_files = glob.glob(fpath + '*.csv')

    list_df = []
    for csv_file in csv_files:
        print(csv_file)
        df = pd.read_csv(csv_file, dtype={'Zip':'object', 'NAICSCode':'object'})
        # do df manipulations
        list_df.append(df)

    df = pd.concat(list_df)
    if (naics == 'NAICS2'):
        df = df.assign( NAICS2 = df.NAICSCode.str.slice(start=0, stop=2))
    else:
        df = df.assign( NAICS3 = df.NAICSCode.str.slice(start=0, stop=3))
    
    # keep loan data for New England only
    loansNE = df[df['BorrowerState'].isin(NEstates)]
    print('loans in NE: ' + str(loansNE.shape[0]))
    loansNE = loansNE[~loansNE.NAICSCode.isna()]   # only non-empty NAICS codes
    print('loans in NE with valid NAICS: ' + str(loansNE.shape[0]))
    #fpath = '/Users/aligo/Downloads/FEMA recovery data/PPP_loans_from_SBA/'
    #loansNE.to_csv(fpath + 'PPP_loans_NEWENGLAND.csv')
    #loansNE = loansNE.set_index('Zip')

#    loansNE.to_csv('/Users/aligo/Downloads/FEMA recovery data/PPPloansNE2021.csv')

    # list and save Loans' business types 
    totLoans = loansNE.shape[0]
    totAmnt = loansNE['CurrentApprovalAmount'].sum()
    print('Total Number of PPP loans to New England with valid NAICS and Zipcode: ' + str(totLoans))
    print('Total PPP loan Amount to New England with valid NAICS and Zipcode: {0:,.0f}'.format(totAmnt) )
    biztypes = loansNE.groupby('BusinessType').agg({'BorrowerState':'count','CurrentApprovalAmount':'sum'})
    idx = loansNE['BusinessType'].isna()
    biztypes.loc['UNKNOWN'] = [idx.sum(), loansNE.loc[idx,'CurrentApprovalAmount'].sum()]
    biztypes['NLoansPercent'] = biztypes['BorrowerState'] / totLoans
    biztypes['LoanAmtPercent'] = biztypes['CurrentApprovalAmount'] / totAmnt
    fpath = '/Users/aligo/Downloads/FEMA recovery data/PPP_loans_from_SBA/'
#    with pd.ExcelWriter(fpath + 'PPP_business_types2021.xlsx') as writer:
#        biztypes[['NLoansPercent','LoanAmtPercent']].to_excel(writer, sheet_name='PPP', index=True)
    print(biztypes)
    return loansNE

def MatchLoanDraws(loans):
    # match loans that have a first and a second draw
    # matches loans using Probabilistic record linkage with Business name and address
    # Note that draws MUST share the same zipcode
    print( 'ProcessingMethod', loans['ProcessingMethod'].unique() )
    
    import recordlinkage
    import recordlinkage.preprocessing
    import datetime

    # cleaning
    loansc = loans.assign( BorrowerNameC = recordlinkage.preprocessing.clean(loans['BorrowerName'])
                          , BorrowerAddressC = recordlinkage.preprocessing.clean(loans['BorrowerAddress'])
                          , BorrowerCityC = recordlinkage.preprocessing.clean(loans['BorrowerCity'])
                          , Zip5 = recordlinkage.preprocessing.clean(loans['BorrowerCity']).str.slice(0,5) 
                    ).set_index('LoanNumber')
                     
    l1 = loansc[loansc['ProcessingMethod']=='PPP']                            # DEBUG
    l2 = loansc[(loansc['ProcessingMethod']=='PPS')] # & (pd.to_datetime(loansc['DateApproved'])>'2021-01-25')]
    print( f'{l1.shape[0]:,} 1st draws and {l2.shape[0]:,} second draws to match' )
        
    # block by city
    indexer = recordlinkage.Index()
    blk_cols = ['StateAbb','BorrowerCityC']
    indexer.block(left_on=blk_cols, right_on=blk_cols)
    candidates = indexer.index(l1, l2)        
    print( f'MatchLoanDraws for block {blk_cols} at {datetime.datetime.now().time():%H:%M:%S}; Number of pairs to match: {len(candidates):,} (takes 8 min for 60 million pairs)' )
    
    compare = recordlinkage.Compare( n_jobs=5 )
    compare.string('BorrowerNameC', 'BorrowerNameC', threshold=0.85, label='BorrowerName')
    compare.string('BorrowerAddressC', 'BorrowerAddressC', # method='jarowinkler',
            threshold=0.85, label='BorrowerAddress' )
#    compare.string('BorrowerCity', 'BorrowerCity', threshold=0.85, label='BorrowerCity' )
    compare.exact('Zip5', 'Zip5', label='BorrowerZip' )
    features = compare.compute(candidates, l1, l2)

    print( f'MatchLoanDraws finished at {datetime.datetime.now().time():%H:%M:%S}' )
    return features

    # block by county - TOO slow
    list_df = []
    for index, row in loans[['StateAbb','COUNTYName']].drop_duplicates().iterrows(): 
        st, cty = row[['StateAbb','COUNTYName']]

        idx = (loans['StateAbb']==st) & (loans['COUNTYName']==cty)

        l1 = loans[idx & (loans['ProcessingMethod']=='PPP')]
        l2 = loans[idx & (loans['ProcessingMethod']=='PPS')]  #[['LoanNumber',id_cols,'CurrentApprovalAmount']]

        indexer = recordlinkage.Index()
        indexer.full()
#    indexer.block(left_on='BorrowerState', right_on='BorrowerState')
#        id_cols = ["LoanNumber","BorrowerCity", "StateAbb"]
#        candidates = indexer.index(l1[id_cols], l2[id_cols])        
        candidates = indexer.index(l1, l2)        
        print( f'MatchLoanDraws for st {st}, cty {cty} at {datetime.datetime.now().time()}; Number of pairs to match: {len(candidates):,}' )
  
        # comparison
        compare = recordlinkage.Compare()
        # compare.exact('City', 'Provider City', label='City')
        compare.string('BorrowerNameC', 'BorrowerNameC',
            threshold=0.85, label='BorrowerNameC')
        compare.string('BorrowerAddressC', 'BorrowerAddressC', # method='jarowinkler',
            threshold=0.85 )
        compare.string('BorrowerCityC', 'BorrowerCityC', threshold=0.85 )
        compare.string('BorrowerZip', 'BorrowerZip', threshold=0.85 )
        features = compare.compute(candidates, l1, l2)
        list_df.append( features )

        break
    
    return pd.concat(list_df)
    
    # unique zipcodes
    # lz = loans.assign( Zip5 = loans['BorrowerZip'].str.slice(start=0, stop=5) )
    # zips = lz['Zip5'].unique()
    # id_cols = ["BorrowerName", "BorrowerAddress", "BorrowerCity", "BorrowerState"] # ,"BorrowerZip"]
    # list_df = []
    # for i in range(len(zips)):
    #     zipcd = zips[i]
    #     l1 = lz[(lz['Zip5']==zipcd) & (lz['ProcessingMethod']=='PPP')]
    #     n1 = l1.shape[0]
    #     l2 = lz[(lz['Zip5']==zipcd) & (lz['ProcessingMethod']=='PPS')]  #[['LoanNumber',id_cols,'CurrentApprovalAmount']]
    #     n2 = l2.shape[0]
    #     print( f"Zipcode {zipcd} ({i}/{len(zips)}): Number of 1st-draw loans: {n1}; "
    #            f"Number of 2nd-draw loans: {n2}; Combined: {n1*n2:,}            ", end='\r' )
    #     if ( n1 > 0 ):        
    #         if ( n2 > 0 ):
    #             matched_results = fuzzymatcher.fuzzy_left_join(l1, l2, left_on=id_cols, right_on=id_cols,
    #                                             left_id_col='LoanNumber', right_id_col='LoanNumber')
    #             list_df.append(matched_results)
    #         else:
    #             list_df.append( l1.add_suffix('_left') )
            

    # res = pd.concat(list_df)

    # return res
    
# def FilterLoans(loans):
#     # Keep only loans from 2021  
#     res = loans.assign( date = pd.to_datetime(loans['DateApproved']) )
#     return res[res['date'] > '2020-08-08']
    
def MatchCounties(loans, excsole, naics):
    # Add county info to each loan, first based on city 
    # and then on zipcode for the unmatched with city
    
    # Join County info into each loan 
    loansc = loans.reset_index().drop(columns='index')
    loansc['cityc'] = loansc['BorrowerCity'].str.upper()
    loansc['cityc'] = loansc['cityc'].str.replace(r'[^A-Z ]+','', regex=True).str.strip()
    loancities = loansc[['BorrowerState','cityc']].drop_duplicates().reset_index().drop(
                        columns='index').rename(columns={'BorrowerState':'StateAbb'})
    tmp = loansc.rename(columns={'BorrowerState':'StateAbb'}).set_index(['StateAbb','cityc'])
    tmp = tmp[~tmp.index.duplicated(keep='first')]
    loancities = loancities.set_index(['StateAbb','cityc']).join(tmp[['BorrowerCity','BorrowerAddress','BorrowerZip']])

    #'https://www2.census.gov/geo/docs/maps-data/data/comp/cousub_comparabilityxls.zip'
    fpath = '/Users/aligo/Downloads/FEMA recovery data/'
    zf = zipfile.ZipFile( fpath + 'cousub_comparabilityxls.zip') 
    citycounty = pd.read_excel(zf.open('Cousub_comparability.xlsx'), engine='openpyxl'
                           , dtype={'STATEFP10':'object','COUNTYFP10':'object'})
    citycounty = citycounty[citycounty.STATEFP10.isin(NEstfips)
                & ~citycounty['NAMELSAD10'].eq('County subdivisions not defined')]
    tmp = pd.DataFrame(index=NEstfips, data=NEstates, columns=['StateAbb'])
    citycounty = citycounty.set_index('STATEFP10').join(tmp).reset_index().rename(
                                                columns={"index": "STATEFP10"} )
    citycounty['COUNTYName'] = citycounty['FULLNAMELSAD10'].str.extract(
                                                        '(, .*(?= County,))')
    citycounty['COUNTYName'] = citycounty['COUNTYName'].str[2:]

    # clean 'city', 'town' etc from city name
    remove_words = ['town', 'city'] #, 'plantation']
    pat = r'\b(?:{})\b'.format('|'.join(remove_words))
    citycounty['cityc'] = citycounty['NAMELSAD10'].str.replace(pat, '').str.upper().str.strip()

    tmp = citycounty.set_index(['StateAbb','cityc'])
    tmp = tmp[~tmp.index.duplicated(keep='last')]
    loancities = loancities.join(tmp)[['BorrowerCity','STATEFP10','COUNTYFP10','NAMELSAD10'
                                ,'FULLNAMELSAD10','COUNTYName']].reset_index()
    print('unique cities in loan dataset: ' + str(loancities.shape[0]))
    print('Unique matches: ' + str(loancities['COUNTYName'].notna().sum()))
    print('Unique non-matches: ' + str(loancities['COUNTYName'].isna().sum()))
    loancities.to_excel('/Users/aligo/Downloads/tmp/ppp addresses 2021.xlsx')

    loancities['COUNTYfips'] = loancities['STATEFP10'] + loancities['COUNTYFP10']
    tmp = loansc.rename(columns={'BorrowerState':'StateAbb'}).set_index(['StateAbb','cityc'])
    tmp2 = loancities.set_index(['StateAbb','cityc'])[['COUNTYfips','COUNTYName']]
    loansc = tmp.join(tmp2)
    print('loans in loan dataset: ' + str(loansc.shape[0]))
    print('loans with matches: ' + str(loansc['COUNTYName'].notna().sum()))
    print('loans non-matches: ' + str(loansc['COUNTYName'].isna().sum()))

    # ZIPcode to County Code crosswalk from https://www.huduser.gov/portal/datasets/usps_crosswalk.html#data
    zipcounty = pd.read_excel('/Users/aligo/Downloads/FEMA recovery data/ZIP_COUNTY_092020.xlsx'
                      , engine='openpyxl', usecols=['ZIP','COUNTY','TOT_RATIO']
                , dtype={'ZIP':'object','COUNTY':'object','TOT_RATIO':'float64'})
    zipcounty = zipcounty[zipcounty['COUNTY'].str[:2].isin(NEstfips)].reset_index()
    nzc = zipcounty.shape[0]
    print('zip-county pairs in New Englad: ' + str(nzc))
    #zipcounty = zipcounty.drop_duplicates(subset='ZIP', keep=False)
    zipcounty['maxtot'] = zipcounty.groupby(['ZIP'])['TOT_RATIO'].transform(max)
    zipcounty = zipcounty[zipcounty['TOT_RATIO']==zipcounty['maxtot']].drop(
                                                columns=['TOT_RATIO','maxtot'])
    nz = zipcounty.shape[0]
    print('zip-county pairs in New England, deduplicated: ' + str(nz))

    tmp = citycounty.assign( COUNTY = citycounty['STATEFP10'] + citycounty['COUNTYFP10'] )
    countyfips = tmp[['COUNTY','StateAbb','COUNTYName']].drop_duplicates()
    countyfips.columns=['COUNTY','State','COUNTYName']
    #zipcounty = zipcounty[['ZIP','COUNTY']].reset_index().set_index('COUNTY').join(
    #                                countyfips.set_index('COUNTY'),how='inner').reset_index()
    zipcounty = zipcounty.set_index('COUNTY').join(
                                countyfips.set_index('COUNTY')).reset_index()
    zipcounty = zipcounty.drop(columns=['index'])
    zipcounty.columns=['COUNTYfips','Zip','State','COUNTYName']

    zipcounty = zipcounty[['Zip','State','COUNTYfips','COUNTYName']].set_index('Zip')

    tmp = loansc.reset_index()
    tmp['Zip5'] = tmp['BorrowerZip'].str.slice(start=0,stop=5) # 5 first digits of Zip
    loans_y = tmp[tmp['COUNTYName'].notna()]  # already matched
    loans_n = tmp[tmp['COUNTYName'].isna()]  # not yet matched
    cols = loans_y.columns

    #loansc = loans.join(zipcounty['COUNTYfips']).reset_index() # loans with County fips and name
    tmp = loans_n.set_index('Zip5').drop(columns=['COUNTYfips','COUNTYName'])
    tmp2 = tmp.join(zipcounty[['COUNTYfips','COUNTYName']]).reset_index().rename(columns={'index':'Zip5'})
    loansc = pd.concat([loans_y[cols], tmp2[cols]])

    # Manual fix of remaining non-matches
    loans_y = loansc[loansc['COUNTYName'].notna()]  # already matched
    loans_n = loansc[loansc['COUNTYName'].isna()]
    print('loans in loan dataset: ' + str(loansc.shape[0]))
    print('1st draw loans: ', loansc[loansc['ProcessingMethod']=='PPP'].shape[0])
    print('2nd draw loans: ', loansc[loansc['ProcessingMethod']=='PPS'].shape[0])
    print('After ZIP match: loans with matches: ', loans_y.shape[0])
    print('After ZIP match: loans non-matches: ', loans_n.shape[0])


    fpath = '/Users/aligo/Downloads/FEMA recovery data/'
    if excsole:
        s = 'nosole'
    else:
        s = 'withall'
    fname = fpath + 'ppp addresses MISS' + s + '2021.xlsx'
    loans_n.to_excel(fname)
    print( 'MANUALLY FIX THE COUNTIES IN EXCEL FILE ' + fname + '\n AND CHANGE ITS NAME FROM MISS TO MANUAL')
    
    return [loans_y, countyfips]

def AddManualCounties(loans_y, excsole, naics):
    tmp = loans_y.dtypes
    fpath = '/Users/aligo/Downloads/FEMA recovery data/'
    if excsole:
        s = 'nosole'
    else:
        s = 'withall'
    fname = fpath + 'ppp addresses MANUAL' + s + '2021.xlsx'

    loans_n = pd.read_excel(fname, engine='openpyxl', dtype=tmp.to_dict() )
    loansc = pd.concat([loans_y, loans_n])
    print('loans in loan dataset: ' + str(loansc.shape[0]))
    print('loans with matches: ' + str(loansc['COUNTYName'].notna().sum()))
    print('loans non-matches: ' + str(loansc['COUNTYName'].isna().sum()))

    loansc = loansc[loansc['COUNTYName'].notna()]   # only non-empty NAICS codes

    if (naics == 'NAICS2'):
        # adjusts 2-digit NAICS that are joint, e.g. NAICS 31-33 Manufacturing
        loansc = OverrideNAICS2(loansc)

    return loansc

def AggregateLoans(loansc, naics):
    # Number of loans per county and NAICS sector
    tmp = loansc.assign( zipcity = loansc['Zip5'] + ', '+ loansc['cityc'] )
#    loansum = tmp.groupby(['COUNTYfips',naics]).agg({'zipcity':'first', 'LoanNumber':'count','CurrentApprovalAmount':'sum', 'JobsReported':'sum'})
    loansum = tmp.groupby(['COUNTYfips',naics]).agg(mod = ('zipcity', lambda x: x.value_counts().index[0]),
                                        l=('LoanNumber','count'), c=('CurrentApprovalAmount','sum'), j=('JobsReported','sum') )
    loansum.columns=['zipcity','NLoans','TotLoanAmount','TotJobsReported']
    
    # debug
#    with pd.ExcelWriter('/Users/aligo/Downloads/tmp/ppp_loans_counts_2021.xlsx') as writer:
#        loansc.reset_index().to_excel(writer, sheet_name='loans')

    return loansum

    
def CalcPenetration(loansum, cnt, naics):
    # Calculate PPP penetration from counts of loans and counties/sectors
    
    cnt = cnt.set_index(['COUNTYfips',naics])
    assert loansum.index.duplicated().sum() == 0, "loansum index not unique"
    pen = cnt.join(loansum) #, rsuffix='loan')
    assert pen.shape[0] == cnt.shape[0], "pen: join error"
    pen = pen.assign(penetration = pen['NLoans']/pen['NEstabs']
                 , AvgLoanAmount = pen['TotLoanAmount']/pen['NLoans']
                 , AvgJobsReported = pen['TotJobsReported']/pen['NLoans']
                 , LoanAmtperEmp = pen['TotLoanAmount']/pen['TotJobsReported'])

    # Add NAICS descriptions
    # naics codes downloaded from https://data.bls.gov/cew/doc/titles/industry/industry_titles.csv
    fpath = '/Users/aligo/git-repos/FEMA/BLS_data/'
    dfnaics = pd.read_csv(fpath + 'industry_titles.csv')

    if (naics == 'NAICS2'):
        idx = (dfnaics['industry_code'].str.len().eq(2)
            | dfnaics['industry_code'].str.contains('^[0-9][0-9]-[0-9][0-9]'))
    else:
        idx = dfnaics['industry_code'].str.len().eq(3)
    dfnaics = dfnaics[idx]
    dfnaics['industry_title'] = dfnaics['industry_title'].str.replace('^NAICS \d+ ',''
                    , regex=True).str.replace('^NAICS \d\d-\d\d ','', regex=True)
    dfnaics.columns = [naics,'NAICSdescr']
    assert dfnaics.index.duplicated().sum() == 0, "dfnaics index not unique"
    tmp = pen.shape[0]
    pen = pen.reset_index().set_index(naics).join(dfnaics.set_index(naics)).reset_index()
    assert pen.shape[0] == tmp, "pen: join error with NAICS description"

    # SAVE 
    idx = pen['NLoans'].isna()
    pen.loc[idx,'NLoans'] = 0
    pen.loc[idx,'penetration'] = 0
    pen = pen.replace([np.inf, -np.inf], np.nan)  # entries with loans but no establishments
    #pen[['State','COUNTYfips','COUNTYName','NAICS3','NAICSdescr'
    #     ,'NEstabs','NLoans','penetration']].to_csv(fpath + 'PPPpenetration.csv')

    # debug
#    fname = '/Users/aligo/Downloads/tmp/ppp_loans_counts.xlsx'
#    writer = pd.ExcelWriter(fname, engine = 'openpyxl')
#    cnt.reset_index().to_excel(writer, sheet_name='counts')
#    writer.save()
#    writer.close()

    # Summaries
#    print('Total Number of PPP loans to New England with valid NAICS: ' + str(loansNE.shape[0]))
#    print('Total Number of PPP loans to New England, excluding ' + ''.join(soleprop) 
#                                                  + ': ' + str(loans.shape[0]))
    print('Total Number of PPP loans to New England excluding loans with missing info: ' 
                                                  + str(pen['NLoans'].sum()))
    print('Total Count of businesses in NE: ' + str(pen['NEstabs'].sum()))
    print('Total Number of County-NAICS pairs in NE with existing businesses: ' 
                                                  + str(pen.shape[0]))
    print('Previous Number with penetration > 1: ' + str(sum(pen['penetration'].gt(1))))
    print('Previous Number with penetration = 0: ' + str(sum(pen['penetration'].isna())))

    return pen

def CalcPenforScopes(loansc, naics, cnt):
    # Subset scope of loans draws and calculate penetration
    d1all = 'First draw (2020 and 2021)'
    d1_21 = 'First draw (2020 only)'
    d2 = 'Second draw (2021)'
    d21all = 'Both draws (2021)'
             # Name of set of loans : filter condition 
    set_dict = { d1all:(loansc['ProcessingMethod']=='PPP')
            , d1_21:((pd.to_datetime(loansc['DateApproved'])<'2021-01-01') & (loansc['ProcessingMethod']=='PPP'))
            , d2:(loansc['ProcessingMethod']=='PPS')
            , d21all:(pd.to_datetime(loansc['DateApproved'])>'2020-12-31') }
    list_df = []
    for key in set_dict:
        print( f'*** {key} ***' )
        # subset loans according to conditions above
        loans_f = loansc[set_dict[key]]
        # aggregate loans
        loansum = AggregateLoans(loans_f, naics)
        # Calculate penetration
        tmp = CalcPenetration(loansum, cnt, naics).assign( scope = key )
        list_df.append( tmp )

    pen = pd.concat(list_df)

    narows = pen['zipcity'].isna()
    if narows.sum() > 0:
        print( f'Penetration table: {narows.sum()} County-NAICS pairs with empty zipcode')
        # Fill Zip of counties/Zip with no loans 
        for index, row in pen[narows][['State','COUNTYfips']].drop_duplicates().iterrows(): 
            st, cty = row[['State','COUNTYfips']]
            # print( f'st {st}, cty {cty}')
            idx = (pen['State']==st) & (pen['COUNTYfips']==cty)
            zipvalid = pen[(~narows) & idx]['zipcity'].mode()[0]
            pen.loc[narows & idx,'zipcity'] = zipvalid

    narows = pen['zipcity'].isna()
    print( f'Penetration table: {narows.sum()} County-NAICS pairs with empty zipcode')
    
    # change from 1st draw (2020+2021) to 2nd draw
    pen_draw1 = pen[pen['scope']==d1all].set_index(['COUNTYfips',naics])
    pen_draw2 = pen[pen['scope']==d2].set_index(['COUNTYfips',naics])[['penetration']]

    pen_chg = pen_draw1.join( pen_draw2, how='outer', lsuffix='_1', rsuffix='_2' )
    # change in penetration
    pen_chg = pen_chg.assign( penetration = pen_chg['penetration_1'] - pen_chg['penetration_2']
                        , scope = 'Reduction from First draw (2020 and 2021) to Second draw' ) \
                    .drop( columns=['penetration_1','penetration_2'] ).reset_index()
    
    pen4 = pd.concat( [pen, pen_chg] )

    # change from 2020 rounds to 2021
    #set_dict['2020 to 2021 change'] = []

    # FOR ARCGIS
    pen4['COUNTYName'] = pen4['COUNTYName'] + ' County'
    pen4['Statefips'] = pen4['COUNTYfips'].str[:2]
    pen4 = pen4.sort_values(by=['scope','Statefips', 'COUNTYName',naics])
    pen4[['Zip','City']] = pen4['zipcity'].str.split(',',expand=True)
    pen4['Postal'] = pen4['zipcity'] + ', ' + pen4['State']    # .str.split(',',expand=True)
    pen4['color'] = pen4['penetration']
    pen4.loc[pen4['color'] > 1,'color'] = 1
    pen4.loc[pen4['color'] < 0,'color'] = 0
    pen4.loc[pen4['color'].isna(),'color'] = 1
    pen4['size'] = pen4['NEstabs']
    pen4.loc[pen4['size'] > 1000,'size'] = 1000
#    pen4['penlabel'] = pd.Series([f'{val:.0%}' for val in pen4['penetration']], index = pen4.index)

    colnames_dict = { 'scope':'scope of loans','State':'state','COUNTYfips':'county fips','COUNTYName':'county name','City':'city','Postal':'Postal'
                 ,naics:'NAICS code','NAICSdescr':'subsector name','NEstabs':'number of establishments','NLoans':'number of loans'
              ,'penetration':'PPP penetration','AvgLoanAmount':'average loan amount','AvgJobsReported':'average jobs reported','LoanAmtperEmp':'loan amount per employee'
                 ,'color':'color (penetration or reduction in penetration)','size':'size (number of establishments)' }
    pen4 = pen4[list(colnames_dict.keys())]
    pen4.columns = list(colnames_dict.values())

    return pen4   