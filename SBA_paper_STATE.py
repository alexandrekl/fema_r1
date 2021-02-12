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

naics = 'NAICS2'  # or 'NAICS3'

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
loans = df.assign( NAICS2 = df.NAICSCode.str.slice(start=0, stop=2)
               , NAICS3 = df.NAICSCode.str.slice(start=0, stop=3) )

nloans = loans.shape[0]
totAmnt = loans['LoanAmount'].sum()
print('PPP loans:', nloans)
print('Total PPP loan Amount:', totAmnt)
print('PPP loans with valid NAICS:', loans[~loans.NAICSCode.isna()].shape[0] / nloans )
print('PPP loans with non-empty Zipcode:', loans[~loans.Zip.str.strip().eq('')].shape[0] / nloans )
print('PPP loans with non-empty BusinessType:', loans[~loans.BusinessType.str.strip().eq('')].shape[0] / nloans )
print('PPP loans with answered RaceEthnicity:', loans[~loans.RaceEthnicity.str.strip().eq('Unanswered')].shape[0] / nloans )
print('PPP loans with answered Gender:', loans[~loans.Gender.str.strip().eq('Unanswered')].shape[0] / nloans )
print('PPP loans with answered Veteran:', loans[~loans.Veteran.str.strip().eq('Unanswered')].shape[0] / nloans )
print('PPP loans with answered NonProfit:', loans[~loans.NonProfit.isna()].shape[0] / nloans )

#loans.to_csv('/Users/aligo/Box/1 RisknDecScience/FEMA recovery/SBA paper/data/PPPloans.csv')
#loans.sample(n=500000, random_state=1).to_csv('/Users/aligo/Box/1 RisknDecScience/FEMA recovery/SBA paper/data/PPPloansSAMPLE.csv')

tmp = loans['State'].unique()
tmp = np.sort(loans[~loans['State'].isna()]['State'].unique())
tmp = np.sort(loans[loans['LoanAmount'].le(150e3) & ~loans['State'].isna()]['State'].unique())
tmp = np.sort(loans[loans['LoanAmount'].gt(150e3) & ~loans['State'].isna()]['State'].unique())

# list and save Loans' business types 
biztypes = loans.groupby('BusinessType').agg({'State':'count','LoanAmount':'sum'})
idx = loans['BusinessType'].isna()
biztypes.loc['UNKNOWN'] = [idx.sum(), loans.loc[idx,'LoanAmount'].sum()]
biztypes['NLoansPercent'] = biztypes['State'] / nloans
biztypes['LoanAmtPercent'] = biztypes['LoanAmount'] / totAmnt
biztypes = biztypes[['NLoansPercent','LoanAmtPercent']].reset_index().melt(id_vars=['BusinessType'])

ggplot(biztypes, aes(x='reorder(BusinessType,value)', y='value',color='variable',fill='variable')
          ) + geom_bar(stat="identity", position ="identity",alpha=0.5
#          ) + scale_alpha_manual(values=[.1, .3]
          ) + theme_bw(
          ) + xlab('Business Type'
          ) + ylab('Percentage of Number of Loans and Loan Amount'
          ) + ggtitle('Business Types in PPP Loans'
          ) + scale_y_continuous(labels=lambda l: ["%d%%" % (v * 100) for v in l]
          ) + coord_flip()

# plot race
race = loans[~loans.RaceEthnicity.str.strip().eq('Unanswered')].groupby('RaceEthnicity'
                                    ).agg({'State':'count','LoanAmount':'sum'})
race['NLoansPercent'] = race['State'] / race['State'].sum()
race['LoanAmtPercent'] = race['LoanAmount'] / race['LoanAmount'].sum()
race = race[['NLoansPercent','LoanAmtPercent']].reset_index().melt(id_vars=['RaceEthnicity'])

ggplot(race, aes(x='reorder(RaceEthnicity,value)', y='value',color='variable',fill='variable')
          ) + geom_bar(stat="identity", position ="identity",alpha=0.5
          ) + theme_bw(
          ) + xlab('Race / Ethnicity'
          ) + ylab('Percentage of Number of Loans and Loan Amount'
          ) + ggtitle('Race / Ethnicity (reported in 10.4% of PPP Loans)'
          ) + scale_y_continuous(labels=lambda l: ["%d%%" % (v * 100) for v in l]
          ) + coord_flip()

# plot gender
gender = loans[~loans.Gender.str.strip().eq('Unanswered')].groupby('Gender'
                                    ).agg({'State':'count','LoanAmount':'sum'})
gender['NLoansPercent'] = gender['State'] / gender['State'].sum()
gender['LoanAmtPercent'] = gender['LoanAmount'] / gender['LoanAmount'].sum()
gender = gender[['NLoansPercent','LoanAmtPercent']].reset_index().melt(id_vars=['Gender'])

ggplot(gender, aes(x='reorder(Gender,value)', y='value',color='variable',fill='variable')
          ) + geom_bar(stat="identity", position ="identity",alpha=0.5
          ) + theme_bw(
          ) + xlab('Gender'
          ) + ylab('Percentage of Number of Loans and Loan Amount'
          ) + ggtitle('Gender (reported in 21.4% of PPP Loans)'
          ) + scale_y_continuous(labels=lambda l: ["%d%%" % (v * 100) for v in l]
          ) 

# plot veteran status
veteran = loans[~loans.Veteran.str.strip().eq('Unanswered')].groupby('Veteran'
                                    ).agg({'State':'count','LoanAmount':'sum'})
veteran['NLoansPercent'] = veteran['State'] / veteran['State'].sum()
veteran['LoanAmtPercent'] = veteran['LoanAmount'] / veteran['LoanAmount'].sum()
veteran = veteran[['NLoansPercent','LoanAmtPercent']].reset_index().melt(id_vars=['Veteran'])

ggplot(veteran, aes(x='reorder(Veteran,value)', y='value',color='variable',fill='variable')
          ) + geom_bar(stat="identity", position ="identity",alpha=0.5
          ) + theme_bw(
          ) + xlab('Veteran Status'
          ) + ylab('Percentage of Number of Loans and Loan Amount'
          ) + ggtitle('Veteran Status (reported in 14.6% of PPP Loans)'
          ) + scale_y_continuous(labels=lambda l: ["%d%%" % (v * 100) for v in l]
          ) 
                                 
# Exclude loans to sole proprietors, contractors etc
soleprop = ['Independent Contractors' #,'Self-Employed Individuals'
            ,'Sole Proprietorship', 'Tenant in Common']
loansCorp = loans[~loans.BusinessType.isin(soleprop)]
print(loansCorp.shape[0], 'loans in PPP dataset excluding', soleprop)

# adjusts 2-digit NAICS that are joint, e.g. NAICS 31-33 Manufacturing
loansc = OverrideNAICS2(loansCorp)

# check
tmp = loansc[loansc['State'].eq('VT')   
             & loansc['NAICS3'].eq('311')]
tmp['LoanAmount'].sum()

# Number of loans per county and NAICS sector
loansum = loansc.groupby(['State',naics]).agg({'Zip':'count'
                                ,'LoanAmount':'sum', 'JobsReported':'sum'})
loansum.columns=['NLoans','TotLoanAmount','TotJobsReported']

# distribution of NLoans per NAICS
ggplot(loansum.reset_index(), aes(x=naics, y='NLoans')
    ) + geom_boxplot(
    ) + scale_y_log10(breaks=lambda b: [10**v for v in range(0,7)], labels=lambda l: ["%d" % v for v in l]
    ) + theme(axis_text_x=element_text(rotation=90, hjust=0.5)
    ) + ggtitle('Number of loans per State'
    ) + xlab('Industry (2-digit NAICS code)'
    ) + ylab('Number of Loans')

dfq = loansum['NLoans'].reset_index().groupby(naics).quantile([0.5,0.75,0.95,0.99,0.999,1]
        ).reset_index().pivot_table(index='level_1',columns=naics,values='NLoans')
dfq.index = dfq.index.map(str)
print('            Quantiles (Number of Loans per state)')
with pd.option_context('display.max_rows', None, 'display.max_columns', None,'display.precision',0):  # more options can be specified also
    print(dfq.transpose())

# TOTAL NUMBER OF BUSINESSES 
# read total number of businesses from BLS
fpath = '/Users/aligo/Downloads/FEMA recovery data/'
zf = zipfile.ZipFile( fpath + '2020_qtrly_singlefile.zip') 
qcew = pd.read_csv(zf.open('2020.q1-q2.singlefile.csv'), dtype={'area_fips':'object'})
# filter
idx = (qcew.own_code.eq(5) & qcew.qtr.eq(1)  # private, FIRST quarter only
         & ~qcew['area_fips'].eq('US000') # exclude US total
         & qcew['area_fips'].str[-3:].eq('000') # include only states totals
         )
if (naics == 'NAICS2'):
    idx = idx & ((qcew['industry_code'].str.len().eq(2)   # 2-digit NAICS
            | qcew['industry_code'].str.match('\d\d-\d\d'))    # 2-digit NAICS that are joint, e.g. NAICS 31-33 Manufacturing
          & ~qcew['industry_code'].eq('10') )      # exclude code = 10 that are "ALL Naics" totals
else:
    idx = idx & (qcew['industry_code'].str.len().eq(3)   # 3-digit NAICS
          & ~qcew['industry_code'].str.startswith('10') )      # exclude code = 10 that are "ALL Naics" totals
    
cnt = qcew[idx]  
cnt = cnt[['area_fips','industry_code','qtrly_estabs']]
cnt['Statefips'] = cnt['area_fips'].str[:2]
# Add state and county name
stabbr = pd.read_csv(fpath + 'state_fips_names.csv', dtype='str')
stabbr[' st'] = stabbr[' st'].str.strip()
stabbr[' stusps'] = stabbr[' stusps'].str.strip()
stabbr = stabbr.set_index(' st').rename(columns={' stusps':'State'})

cnt = cnt.set_index('Statefips').join(stabbr).reset_index()
cnt = cnt[['index','industry_code','qtrly_estabs','State']]
# Join Total Num businesses + Num of loans
cnt.columns = ['Statefips',naics,'NEstabs','State']
cnt = cnt.set_index(['State',naics])
tmp = loansum.reset_index().set_index(['State',naics])
pen = cnt.join(tmp) #, rsuffix='loan')
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
dfnaics['industry_title'] = dfnaics['industry_title'].str.replace('^NAICS \d+ '
                    ,'',regex=True).str.replace('^NAICS \d\d-\d\d ','',regex=True)
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
pen.sort_values(by=['Statefips', naics])
pen['OBJECTID'] = pen.reset_index().index + 1
with pd.ExcelWriter(fpath + 'PPPpenetrationBLS_STATE_' + naics + '.xlsx') as writer:
    pen[['OBJECTID','State',naics,'NAICSdescr','NEstabs','NLoans'
              ,'penetration','AvgLoanAmount','AvgJobsReported','LoanAmtperEmp']
                            ].to_excel(writer, sheet_name='PPP', index=False)

# debug
with pd.ExcelWriter('/Users/aligo/Downloads/tmp/ppp_loans_bls_counts.xlsx') as writer:
#    loansc.reset_index().to_excel(writer, sheet_name='loans')
    cnt.reset_index().to_excel(writer, sheet_name='bls')

# Summaries
print('Total Number of PPP loans:', loans.shape[0])
print('Total Number of PPP loans, excluding ' + ''.join(soleprop) 
                                                  + ': ' + str(loansc.shape[0]))
print('Previous Number excluding loans with missing info: ' 
                                                  + str(pen['NLoans'].sum()))
print('BLS Total Count of businesses: ' + str(pen['NEstabs'].sum()))
print('Total Number of STATE-NAICS pairs with existing businesses: ' 
                                                  + str(pen.shape[0]))
print('Previous Number with penetration > 1: ' + str(sum(pen['penetration'].gt(1))))
print('Previous Number with penetration = 0: ' + str(sum(pen['penetration'].eq(0))))

# distribution of NEstabs per NAICS
ggplot(pen, aes(x=naics, y='NEstabs')
    ) + geom_boxplot(
    ) + coord_cartesian(ylim=[0, 35000]
    ) + theme(axis_text_x=element_text(rotation=90, hjust=0.5)
    ) + ggtitle('Number of businesses per State'
    ) + xlab('Industry (2-digit NAICS code)'
    ) + ylab('Number of Businesses')
dfq = pen[[naics,'NEstabs']].groupby(naics).quantile([0.5,0.75,0.95,0.99,0.999,1]
        ).reset_index().pivot_table(index='level_1',columns=naics,values='NEstabs')
dfq.index = dfq.index.map(str)
print('         Quantiles (Number of businesses per State)')
print('     ')
with pd.option_context('display.max_rows', None, 'display.max_columns', None,'display.precision',0):  # more options can be specified also
    print(dfq.transpose())
    
# distribution of penetration per NAICS
ggplot(pen, aes(x=naics, y='penetration')
    ) + geom_boxplot(
    ) + coord_cartesian(ylim=[0, 1.5]
    ) + theme(axis_text_x=element_text(rotation=90, hjust=0.5)
    ) + ggtitle('Penetration per State'
    ) + xlab('Industry (2-digit NAICS code)'
    ) + ylab('Penetration (Num loans/Num BLS businesses)')
dfq = pen[[naics,'penetration']].groupby(naics).quantile([0.5,0.75,0.95,0.99,0.999,1]
        ).reset_index().pivot_table(index='level_1',columns=naics,values='penetration')
dfq.index = dfq.index.map(str)
print('           Quantiles (Penetration per State)')
print('     ')
with pd.option_context('display.max_rows', None, 'display.max_columns', None,'display.precision',2):  # more options can be specified also
    print(dfq.transpose())

nloansMEchild = loansCorp[loansCorp['State'].eq('ME')&(loansCorp['NAICSCode'].eq(
    '624410')|loansCorp['BusinessType'].eq('Non-Profit Childcare Center'))].shape[0]
nbizMEchild = qcew.loc[qcew['area_fips'].eq('23000') & qcew['industry_code'].eq('624410'
                ) & qcew.own_code.eq(5) & qcew.qtr.eq(1)]['qtrly_estabs'].values[0]
print('Number of loans to Maine NAICS 624410 or BusinessType Non-Profit Childcare Center:'
                                                              , nloansMEchild)
print('Number of BLS businesses to Maine NAICS 624410, Q1 2020:', nbizMEchild)
print('Penetration:', nloansMEchild / nbizMEchild )

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




