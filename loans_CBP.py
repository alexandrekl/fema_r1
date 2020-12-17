#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 20 13:23:36 2020
v2 version of this script was to work with BLS QCEW data
v3 version is to work 
@author: aligo
"""

import glob
import pandas as pd
import zipfile
from plotnine import *    # python lib to use ggplot
from io import BytesIO
from urllib.request import urlopen
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
df = df.assign( NAICS2 = df.NAICSCode.str.slice(start=0, stop=2))

# keep loan data for New England only
loansNE = df[df.Zip.notna() & df.State.isin(NEstates)
             & ~df.NAICSCode.isna()]   # only non-empty NAICS codes
loansNE = loansNE.set_index('Zip')

# list business types
biztypes = loansNE.groupby('BusinessType').agg('count')
print(biztypes.City)
print(biztypes.City.sum())

# Exclude loans to sole proprietors, contractors etc
#soleprop = ['Independent Contractors' #,'Self-Employed Individuals'
#            ,'Sole Proprietorship', 'Tenant in Common']
loans = loansNE #[~loansNE.BusinessType.isin(soleprop)]

# Join County info into each loan 
# ZIPcode to County Code crosswalk from https://www.huduser.gov/portal/datasets/usps_crosswalk.html#data
zipcounty = pd.read_excel('/Users/aligo/Downloads/FEMA recovery data/ZIP_COUNTY_092020.xlsx'
           , usecols=['ZIP','COUNTY']
           , dtype={'ZIP':'object','COUNTY':'object'})
zipcounty = zipcounty.drop_duplicates(subset='ZIP', keep="first")

# County FIPS to county name crosswalk
fpath = 'https://www2.census.gov/programs-surveys/popest/geographies/2018/all-geocodes-v2018.xlsx'
countyfips = pd.read_excel(fpath, skiprows=range(4), header=0, dtype={
                'State Code (FIPS)':'object', 'County Code (FIPS)':'object'})
countyfips = countyfips[countyfips['Summary Level'].eq(50) &   # keep county entries
                        countyfips['State Code (FIPS)'].isin(NEstfips)]   # keep NE 
countyfips = countyfips.assign( COUNTY=countyfips['State Code (FIPS)']+
                                       countyfips['County Code (FIPS)'])
countyfips = countyfips.replace({'State Code (FIPS)': 
                    {NEstfips[i]: NEstates[i] for i in range(len(NEstfips))}})
countyfips = countyfips[['COUNTY','State Code (FIPS)','Area Name (including legal/statistical area description)']]
countyfips.columns=['COUNTY','State','COUNTYName']
# Note the INNER join below - will keep only the zipcodes in New England
zipcounty = zipcounty[['ZIP','COUNTY']].reset_index().set_index('COUNTY').join(
                                countyfips.set_index('COUNTY'),how='inner').reset_index()
zipcounty.columns=['COUNTYfips','index','Zip','State','COUNTYName']
zipcounty = zipcounty[['Zip','State','COUNTYfips','COUNTYName']].set_index('Zip')

loansc = loans.join(zipcounty['COUNTYfips']).reset_index() # loans with County fips and name
# adjusts 2-digit NAICS that are joint, e.g. NAICS 31-33 Manufacturing
loansc = OverrideNAICS2(loansc)

# Number of loans per county and NAICS2
loansum = loansc.groupby(['COUNTYfips','NAICS2']).agg({'Zip':'count'
                                ,'LoanAmount':'sum', 'JobsReported':'sum'})
loansum.columns=['NLoans','TotLoanAmount','TotJobsReported']

# TOTAL NUMBER OF BUSINESSES - from US Census CBP
url = urlopen("https://www2.census.gov/programs-surveys/cbp/datasets/2018/cbp18co.zip")
#Download Zipfile and create pandas DataFrame
zipfile = zipfile.ZipFile(BytesIO(url.read()))
cbp = pd.read_csv(zipfile.open('cbp18co.txt'), na_values='N')

cbp['FIPST'] = cbp['fipstate'].astype(str).str.pad(2,fillchar='0')
cbp['area_fips'] = cbp['FIPST'] + cbp['fipscty'].astype(str).str.pad(3,fillchar='0')
cnt = cbp[cbp['FIPST'].isin(NEstfips)    # New England counties
          & ~cbp['fipscty'].eq(999)      # exclude fipscty = 999 that are "statewide" totals
          & cbp['naics'].str.contains('^[0-9][0-9]----',regex=True)]    # 2-digit NAICS codes
cnt = cnt.assign( industry_code = cnt['naics'].str.slice(start=0,stop=2) )    # 2-digit NAICS codes, cleaned
cnt['NEstabs'] = cnt[['n<5','n5_9','n10_19','n20_49','n50_99','n100_249','n250_499']
                     ].sum(axis=1, skipna=True)         # num Establishments with < 500 employees
cnt = cnt[['area_fips','industry_code','NEstabs']].set_index('area_fips')
# Add state and county name
cnt = cnt.join(countyfips.set_index('COUNTY'))

# Join Total Num businesses + Num of loans
cnt = cnt.reset_index()
cnt.columns = ['COUNTYfips','NAICS2','NEstabs','State','COUNTYName']
# adjusts 2-digit NAICS that are joint, e.g. NAICS 31-33 Manufacturing
cnt = OverrideNAICS2(cnt)
cnt = cnt.set_index(['COUNTYfips','NAICS2'])
pen = cnt.join(loansum, rsuffix='loan')
pen = pen.assign(penetration = pen['NLoans']/pen['NEstabs']
                 , AvgLoanAmount = pen['TotLoanAmount']/pen['NLoans']
                 , AvgJobsReported = pen['TotJobsReported']/pen['NLoans']
                 , LoanAmtperEmp = pen['TotLoanAmount']/pen['TotJobsReported'])

# Add NAICS descriptions
# naics codes downloaded from https://data.bls.gov/cew/doc/titles/industry/industry_titles.csv
fpath = '/Users/aligo/git-repos/FEMA/BLS_data/'
dfnaics = pd.read_csv(fpath + 'industry_titles.csv')
dfnaics = dfnaics[dfnaics['industry_code'].str.len().eq(2)
            | dfnaics['industry_code'].str.contains('^[0-9][0-9]-[0-9][0-9]')]
dfnaics['industry_title'] = dfnaics['industry_title'].str.replace('^NAICS \d\d ',''
                                        ).str.replace('^NAICS \d\d-\d\d ','')
dfnaics.columns = ['NAICS2','NAICSdescr']
pen = pen.reset_index().set_index('NAICS2').join(dfnaics.set_index('NAICS2')).reset_index()

# SAVE 
fpath = '/Users/aligo/Downloads/FEMA recovery data/PPP_loans_from_SBA/'
idx = pen['NLoans'].isna()
pen.loc[idx,'NLoans'] = 0   # entries with no loans
pen.loc[idx,'penetration'] = 0
pen = pen.replace([np.inf, -np.inf], np.nan)  # entries with loans but no establishments
#pen[['State','COUNTYfips','COUNTYName','NAICS2','NAICSdescr'
#     ,'NEstabs','NLoans','penetration']].to_csv(fpath + 'PPPpenetration.csv')

with pd.ExcelWriter(fpath + 'PPPpenetrationCBP.xlsx') as writer:
    pen[['State','COUNTYfips','COUNTYName','NAICS2','NAICSdescr','NEstabs','NLoans'
              ,'penetration','AvgLoanAmount','AvgJobsReported','LoanAmtperEmp']
                            ].to_excel(writer, sheet_name='PPP', index=False)

# Summaries
print('Total Number of PPP loans to New England with valid NAICS: ' + str(loansNE.shape[0]))
print('Previous Number excluding loans with missing info: ' 
                                                  + str(pen['NLoans'].sum()))
print('Census CBP Total Count of businesses in NE: ' + str(pen['NEstabs'].sum()))
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
dfp = pen.groupby(['NAICS2','NAICSdescr']).agg('sum').reset_index()
dfp['penetration'] = dfp['NLoans'] / dfp['NEstabs']

ggplot(dfp, aes(x='reorder(NAICSdescr,penetration)', y='penetration')
          ) + geom_bar(stat="identity"
          ) + xlab('NAICS 2 Digit Sector'
          ) + ylab('PPP Loan Penetration'
          ) + ggtitle('New England PPP Penetrations per NAICS Sector'
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




