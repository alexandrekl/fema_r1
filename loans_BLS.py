#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 20 13:23:36 2020

@author: aligo
"""

import glob
import pandas as pd
import zipfile
from plotnine import *    # python lib to use ggplot
import numpy as np

NEstates = ['CT','MA','ME','NH','RI','VT']
NEstfips = ['09','25','23','33','44','50']

naics = 'NAICS3'  # or 'NAICS2'

def OverrideNAICS2(df):
    # adjusts 2-digit NAICS that are joint, e.g. NAICS 31-33 Manufacturing
    df.loc[df['NAICS2'].eq('31'),'NAICS2'] = '31-33'
    df.loc[df['NAICS2'].eq('33'),'NAICS2'] = '31-33'
    df.loc[df['NAICS2'].eq('44'),'NAICS2'] = '44-45' # NAICS 44-45 Retail trade
    df.loc[df['NAICS2'].eq('45'),'NAICS2'] = '44-45' # NAICS 44-45 Retail trade
    df.loc[df['NAICS2'].eq('48'),'NAICS2'] = '48-49' # 	NAICS 48-49 Transportation and warehousing
    df.loc[df['NAICS2'].eq('49'),'NAICS2'] = '48-49' # 	NAICS 48-49 Transportation and warehousing
    return df

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
loansNE = df[df.Zip.notna() & df.State.isin(NEstates)
             & ~df.NAICSCode.isna()]   # only non-empty NAICS codes
loansNE = loansNE.set_index('Zip')

# list business types
biztypes = loansNE.groupby('BusinessType').agg('count')
print(biztypes.City)
print(biztypes.City.sum())

# Exclude loans to sole proprietors, contractors etc
soleprop = ['Independent Contractors' #,'Self-Employed Individuals'
            ,'Sole Proprietorship', 'Tenant in Common']
loans = loansNE[~loansNE.BusinessType.isin(soleprop)]

# Join County info into each loan 
# ZIPcode to County Code crosswalk from https://www.huduser.gov/portal/datasets/usps_crosswalk.html#data
zipcounty = pd.read_excel('/Users/aligo/Downloads/FEMA recovery data/ZIP_COUNTY_092020.xlsx'
                          , engine='openpyxl', usecols=['ZIP','COUNTY']
                          , dtype={'ZIP':'object','COUNTY':'object'})
zipcounty = zipcounty.drop_duplicates(subset='ZIP', keep="first")

# County code to county name crosswalk
fpath = 'https://www2.census.gov/programs-surveys/popest/geographies/2018/all-geocodes-v2018.xlsx'
countyfips = pd.read_excel(fpath, engine='openpyxl', skiprows=range(4), header=0
            , dtype={'State Code (FIPS)':'object', 'County Code (FIPS)':'object'})
countyfips = countyfips[countyfips['Summary Level'].eq(50) &   # keep county entries
                        countyfips['State Code (FIPS)'].isin(NEstfips)]   # keep NE 
countyfips = countyfips.assign( COUNTY=countyfips['State Code (FIPS)']+
                                       countyfips['County Code (FIPS)'])
countyfips = countyfips.replace({'State Code (FIPS)': 
                    {NEstfips[i]: NEstates[i] for i in range(len(NEstfips))}})
countyfips = countyfips[['COUNTY','State Code (FIPS)','Area Name (including legal/statistical area description)']]
countyfips.columns=['COUNTY','State','COUNTYName']
zipcounty = zipcounty[['ZIP','COUNTY']].reset_index().set_index('COUNTY').join(
                                countyfips.set_index('COUNTY'),how='inner').reset_index()
zipcounty.columns=['COUNTYfips','index','Zip','State','COUNTYName']
zipcounty = zipcounty[['Zip','State','COUNTYfips','COUNTYName']].set_index('Zip')

loansc = loans.join(zipcounty['COUNTYfips']).reset_index() # loans with County fips and name
if (naics == 'NAICS2'):
    # adjusts 2-digit NAICS that are joint, e.g. NAICS 31-33 Manufacturing
    loansc = OverrideNAICS2(loansc)

# Number of loans per county and NAICS sector
loansum = loansc.groupby(['COUNTYfips',naics]).agg({'Zip':'count'
                                ,'LoanAmount':'sum', 'JobsReported':'sum'})
loansum.columns=['NLoans','TotLoanAmount','TotJobsReported']

# TOTAL NUMBER OF BUSINESSES 
# read total number of businesses from BLS
fpath = '/Users/aligo/Downloads/FEMA recovery data/'
zf = zipfile.ZipFile( fpath + '2020_qtrly_singlefile.zip') 
qcew = pd.read_csv(zf.open('2020.q1-q2.singlefile.csv'), dtype={'area_fips':'object'})
# filter
idx = (qcew.own_code.eq(5) & qcew.qtr.eq(1) & # private, FIRST quarter only
         qcew['area_fips'].isin(countyfips['COUNTY'].tolist()))   # NE only
if (naics == 'NAICS2'):
    idx = idx & ((qcew['industry_code'].str.len().eq(2)   # 2-digit NAICS
            | qcew['industry_code'].str.match('\d\d-\d\d'))    # 2-digit NAICS that are joint, e.g. NAICS 31-33 Manufacturing
          & ~qcew['industry_code'].eq('10') )      # exclude code = 10 that are "ALL Naics" totals
else:
    idx = idx & (qcew['industry_code'].str.len().eq(3)   # 3-digit NAICS
          & ~qcew['industry_code'].str.startswith('10') )      # exclude code = 10 that are "ALL Naics" totals
    
cnt = qcew[idx]  # New England counties
cnt = cnt[['area_fips','industry_code','qtrly_estabs']].set_index('area_fips')
# Add state and county name
cnt = cnt.join(countyfips.set_index('COUNTY'))
# Join Total Num businesses + Num of loans
cnt = cnt.reset_index()
cnt.columns = ['COUNTYfips',naics,'NEstabs','State','COUNTYName']
cnt = cnt.set_index(['COUNTYfips',naics])
pen = cnt.join(loansum, rsuffix='loan')
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
                                        ).str.replace('^NAICS \d\d-\d\d ','')
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

with pd.ExcelWriter(fpath + 'PPPpenetrationBLS_' + naics + '.xlsx') as writer:
    pen[['State','COUNTYfips','COUNTYName',naics,'NAICSdescr','NEstabs','NLoans'
              ,'penetration','AvgLoanAmount','AvgJobsReported','LoanAmtperEmp']
                            ].to_excel(writer, sheet_name='PPP', index=False)

# Summaries
print('Total Number of PPP loans to New England with valid NAICS: ' + str(loansNE.shape[0]))
print('Total Number of PPP loans to New England, excluding ' + ''.join(soleprop) 
                                                  + ': ' + str(loans.shape[0]))
print('Previous Number excluding loans with missing info: ' 
                                                  + str(pen['NLoans'].sum()))
print('BLS Total Count of businesses in NE: ' + str(pen['NEstabs'].sum()))
print('Total Number of County-NAICS pairs in NE with existing businesses: ' 
                                                  + str(pen.shape[0]))
print('Previous Number with penetration > 1: ' + str(sum(pen['penetration'].gt(1))))
print('Previous Number with penetration = 0: ' + str(sum(pen['penetration'].isna())))

# total per county 
dfc = pen.groupby(['COUNTYName']).agg('sum').reset_index()
dfc['penetration'] = dfc['NLoans'] / dfc['NEstabs']
ggplot(dfc, aes(x='reorder(COUNTYName,penetration)', y='penetration')
          ) + geom_bar(stat="identity"
          ) + xlab('County'
          ) + ylab('PPP Loan Penetration'
          ) + ggtitle('New England PPP Penetrations per County'
          ) + theme(axis_text_y = element_text(size=6)
          ) + coord_flip()

# total per NAICS
dfp = pen.groupby([naics,'NAICSdescr']).agg('sum').reset_index()
dfp['penetration'] = dfp['NLoans'] / dfp['NEstabs']

ggplot(dfp, aes(x='reorder(NAICSdescr,penetration)', y='penetration')
          ) + geom_bar(stat="identity"
          ) + xlab('NAICS 2 Digit Sector'
          ) + ylab('PPP Loan Penetration'
          ) + ggtitle('New England PPP Penetrations per NAICS Sector'
#          ) + scale_y_continuous(trans = 'log2'
          ) + coord_flip()

ggplot(dfp[dfp['penetration'].gt(1)], aes(x='reorder(NAICSdescr,penetration)', y='penetration')
          ) + geom_bar(stat="identity"
          ) + xlab(naics + ' Sector'
          ) + ylab('PPP Loan Penetration'
          ) + ggtitle('New England PPP Penetrations > 1 per NAICS Sector'
#          ) + scale_y_continuous(trans = 'log2'
          ) + coord_flip()
                                   
# Histogram of County-NAICS penetrations
ggplot(pen[pen.penetration.le(1)], aes(x='penetration')
       ) + geom_histogram(binwidth=.05
       ) + xlab('PPP Loan Penetration'
       ) + ylab('Number of Counties-Sectors'
       ) + ggtitle('Distribution of PPP Penetration <= 1 in New England')

# outlier penetrations
ggplot(pen, aes(x='State', y='penetration')
       ) + geom_boxplot(
       ) + xlab('State'
       ) + ylab('Penetration'
       ) + ggtitle('Outliers of PPP Penetration in New England')

#with pd.ExcelWriter(fpath + 'PPP.xlsx') as writer:
#    dfsum[['State','City','Zip','NAICS3','NAICSdescr','TotalAmount','NumLoans'
#           ,'JobsReported']].to_excel(writer, sheet_name='PPP', index=False)




