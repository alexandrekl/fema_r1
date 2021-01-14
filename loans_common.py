#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  8 14:52:34 2021
Common code for loans_BLS.py and loans_CBP.py
@author: aligo
"""

import glob
import pandas as pd
import zipfile
import numpy as np

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

def ReadPPPdata(naics):
    # read PPP loan data
    fpath = '/Users/aligo/Downloads/FEMA recovery data/PPP_loans_from_SBA/120120 Paycheck Protection Program Data/'

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
    loansNE = df[#df.Zip.notna() & 
                 df.State.isin(NEstates)]
    print('loans in NE: ' + str(loansNE.shape[0]))
    loansNE = loansNE[~loansNE.NAICSCode.isna()]   # only non-empty NAICS codes
    print('loans in NE with valid NAICS: ' + str(loansNE.shape[0]))
    #fpath = '/Users/aligo/Downloads/FEMA recovery data/PPP_loans_from_SBA/'
    #loansNE.to_csv(fpath + 'PPP_loans_NEWENGLAND.csv')
    #loansNE = loansNE.set_index('Zip')

    loansNE.to_csv('/Users/aligo/Downloads/FEMA recovery data/PPPloansNE.csv')

    # list and save Loans' business types 
    totLoans = loansNE.shape[0]
    totAmnt = loansNE['LoanAmount'].sum()
    print('Total Number of PPP loans to New England with valid NAICS and Zipcode: ' + str(totLoans))
    print('Total PPP loan Amount to New England with valid NAICS and Zipcode: ' + str(totAmnt))
    biztypes = loansNE.groupby('BusinessType').agg({'State':'count','LoanAmount':'sum'})
    idx = loansNE['BusinessType'].isna()
    biztypes.loc['UNKNOWN'] = [idx.sum(), loansNE.loc[idx,'LoanAmount'].sum()]
    biztypes['NLoansPercent'] = biztypes['State'] / totLoans
    biztypes['LoanAmtPercent'] = biztypes['LoanAmount'] / totAmnt
    fpath = '/Users/aligo/Downloads/FEMA recovery data/PPP_loans_from_SBA/'
    with pd.ExcelWriter(fpath + 'PPP_business_types.xlsx') as writer:
        biztypes[['NLoansPercent','LoanAmtPercent']].to_excel(writer, sheet_name='PPP'
                                                                 , index=True)
    return loansNE

def MatchCounties(loans, excsole, naics):
    # Add county info to each loan, first based on city 
    # and then on zipcode for the unmatched with city
    
    # Join County info into each loan 
    loansc = loans.reset_index().drop(columns='index')
    loansc['cityc'] = loansc['City'].str.upper()
    loansc['cityc'] = loansc['cityc'].str.replace(r'[^A-Z ]+','', regex=True).str.strip()
    loancities = loansc[['State','cityc']].drop_duplicates().reset_index().drop(
                        columns='index').rename(columns={'State':'StateAbb'})
    tmp = loansc.rename(columns={'State':'StateAbb'}).set_index(['StateAbb','cityc'])
    tmp = tmp[~tmp.index.duplicated(keep='first')]
    loancities = loancities.set_index(['StateAbb','cityc']).join(tmp[['City','Address','Zip']])

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
    loancities = loancities.join(tmp)[['City','STATEFP10','COUNTYFP10','NAMELSAD10'
                                ,'FULLNAMELSAD10','COUNTYName']].reset_index()
    print('unique cities in loan dataset: ' + str(loancities.shape[0]))
    print('Unique matches: ' + str(loancities['COUNTYName'].notna().sum()))
    print('Unique non-matches: ' + str(loancities['COUNTYName'].isna().sum()))
    loancities.to_excel('/Users/aligo/Downloads/tmp/ppp addresses.xlsx')

    loancities['COUNTYfips'] = loancities['STATEFP10'] + loancities['COUNTYFP10']
    tmp = loansc.rename(columns={'State':'StateAbb'}).set_index(['StateAbb','cityc'])
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

    # County code to county name crosswalk
    #fpath = 'https://www2.census.gov/programs-surveys/popest/geographies/2018/all-geocodes-v2018.xlsx'
    #countyfips = pd.read_excel(fpath, engine='openpyxl', skiprows=range(4), header=0
    #            , dtype={'State Code (FIPS)':'object', 'County Code (FIPS)':'object'})
    #countyfips = countyfips[countyfips['Summary Level'].eq(50) &   # keep county entries
    #                        countyfips['State Code (FIPS)'].isin(NEstfips)]   # keep NE 
    #countyfips = countyfips.assign( COUNTY=countyfips['State Code (FIPS)']+
    #                                       countyfips['County Code (FIPS)'])
    #countyfips = countyfips.replace({'State Code (FIPS)': 
    #                    {NEstfips[i]: NEstates[i] for i in range(len(NEstfips))}})
    #countyfips = countyfips[['COUNTY','State Code (FIPS)','Area Name (including legal/statistical area description)']]
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
    loans_y = tmp[tmp['COUNTYName'].notna()]  # already matched
    loans_n = tmp[tmp['COUNTYName'].isna()]  # not yet matched
    cols = loans_y.columns

    #loansc = loans.join(zipcounty['COUNTYfips']).reset_index() # loans with County fips and name
    tmp = loans_n.set_index('Zip').drop(columns=['COUNTYfips','COUNTYName'])
    tmp2 = tmp.join(zipcounty[['COUNTYfips','COUNTYName']]).reset_index()
    loansc = pd.concat([loans_y[cols], tmp2[cols]])

    print('loans in loan dataset: ' + str(loansc.shape[0]))
    print('loans with matches: ' + str(loansc['COUNTYName'].notna().sum()))
    print('loans non-matches: ' + str(loansc['COUNTYName'].isna().sum()))

    # Manual fix of remaining non-matches
    loans_y = loansc[loansc['COUNTYName'].notna()]  # already matched
    loans_n = loansc[loansc['COUNTYName'].isna()]
    fpath = '/Users/aligo/Downloads/FEMA recovery data/'
    if excsole:
        s = 'nosole'
    else:
        s = 'withall'
    fname = fpath + 'ppp addresses MISS' + s + '.xlsx'
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
    fname = fpath + 'ppp addresses MANUAL' + s + '.xlsx'

    loans_n = pd.read_excel(fname, engine='openpyxl', dtype=tmp.to_dict() )
    loansc = pd.concat([loans_y, loans_n])
    print('loans in loan dataset: ' + str(loansc.shape[0]))
    print('loans with matches: ' + str(loansc['COUNTYName'].notna().sum()))
    print('loans non-matches: ' + str(loansc['COUNTYName'].isna().sum()))

    loansc = loansc[loansc['COUNTYName'].notna()]   # only non-empty NAICS codes

    if (naics == 'NAICS2'):
        # adjusts 2-digit NAICS that are joint, e.g. NAICS 31-33 Manufacturing
        loansc = OverrideNAICS2(loansc)

    # check
    if (naics == 'NAICS3'):
        tmp = loansc[loansc['COUNTYfips'].eq('50017')    # orange county
             & loansc['NAICS3'].eq('311')]
        tmp = loansc[loansc['State'].eq('VT')    # orange county
             & loansc['NAICS3'].eq('311')]
        tmp['LoanAmount'].sum()

    # Number of loans per county and NAICS sector
    loansum = loansc.groupby(['COUNTYfips',naics]).agg({'Zip':'count'
                                ,'LoanAmount':'sum', 'JobsReported':'sum'})
    loansum.columns=['NLoans','TotLoanAmount','TotJobsReported']

    # debug
    with pd.ExcelWriter('/Users/aligo/Downloads/tmp/ppp_loans_counts.xlsx') as writer:
        loansc.reset_index().to_excel(writer, sheet_name='loans')

    return loansum

    
def CalcPenetration(loansum, cnt, naics):
    # Calculate PPP penetration from counts of loans and counties/sectors
    
    cnt = cnt.set_index(['COUNTYfips',naics])
    tmp = loansum.reset_index().set_index(['COUNTYfips',naics])
    pen = cnt.join(loansum) #, rsuffix='loan')
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
    pen = pen.reset_index().set_index(naics).join(dfnaics.set_index(naics)).reset_index()

    # SAVE 
    fpath = '/Users/aligo/Downloads/FEMA recovery data/PPP_loans_from_SBA/'
    idx = pen['NLoans'].isna()
    pen.loc[idx,'NLoans'] = 0
    pen.loc[idx,'penetration'] = 0
    pen = pen.replace([np.inf, -np.inf], np.nan)  # entries with loans but no establishments
    #pen[['State','COUNTYfips','COUNTYName','NAICS3','NAICSdescr'
    #     ,'NEstabs','NLoans','penetration']].to_csv(fpath + 'PPPpenetration.csv')

    # FOR ARCGIS
    pen['COUNTYName'] = pen['COUNTYName'] + ' County'
    pen['Statefips'] = pen['COUNTYfips'].str[:2]
    pen = pen.sort_values(by=['Statefips', 'COUNTYName',naics])
    pen['OBJECTID'] = pen.reset_index().index + 1
    with pd.ExcelWriter(fpath + 'PPPpenetration_' + naics + '.xlsx') as writer:
        pen[['OBJECTID','State','COUNTYfips','COUNTYName',naics,'NAICSdescr','NEstabs','NLoans'
              ,'penetration','AvgLoanAmount','AvgJobsReported','LoanAmtperEmp']
                            ].to_excel(writer, sheet_name='PPP', index=False)

    # debug
    fname = '/Users/aligo/Downloads/tmp/ppp_loans_counts.xlsx'
    writer = pd.ExcelWriter(fname, engine = 'openpyxl')
    cnt.reset_index().to_excel(writer, sheet_name='counts')
    writer.save()
    writer.close()

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