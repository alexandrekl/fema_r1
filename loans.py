#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 20 13:23:36 2020

@author: aligo
"""

import zipfile
import pandas as pd

# naics codes downloaded from https://data.bls.gov/cew/doc/titles/industry/industry_titles.csv
fpath = '/Users/aligo/git-repos/FEMA/BLS_data/'
dfnaics = pd.read_csv(fpath + 'industry_titles.csv')
dfnaics['industry_title'] = dfnaics['industry_title'].str.replace(
                                      'NAICS \d+ ','').str.replace('\d+ ','')

fpath = '/Users/aligo/Downloads/FEMA recovery data/PPP_loans_from_SBA/'

# read data on PPP loans - from https://home.treasury.gov/policy-issues/cares-act/assistance-for-small-businesses/sba-paycheck-protection-program-loan-level-data
zf = zipfile.ZipFile( fpath + "All Data 0808.zip") 
text_files = zf.infolist()
list_df = []

print ("Uncompressing and reading data... ")

for text_file in text_files:
    print(text_file.filename)
    if text_file.filename.startswith('__MACOSX'):
        continue
    if text_file.filename.endswith('.csv'):
        df = pd.read_csv(zf.open(text_file.filename)
                               , dtype={'Zip':'object', 'NAICSCode':'object'})
        print("read")
        # do df manipulations
        list_df.append(df)

df = pd.concat(list_df).assign( NAICS3 = df.NAICSCode.str.slice(start=0, stop=3))

print('Total amount of loans < $150K')
print(df['LoanAmount'].sum())

# Loans above 150K have LoanRange instead of LoanAmount: we fill LoanAmount 
# with the mean of each range
print(df.LoanRange.drop_duplicates())
stw = ['a ', 'b ', 'c ', 'd ', 'e ']
vln = [7e6, 3e6, 1.5e6, .6e6, .2e6]
for i in range(5):
    m = df.LoanRange.notna() & df.LoanRange.str.startswith(stw[i])
    df.loc[m,'LoanAmount'] = vln[i]
    print( stw[i] + ': ' + str(sum(m)) )

print('Total amount of loans')
print(df['LoanAmount'].sum())

tmp = df[df['LoanAmount'].isna()]
tmp = df[['LoanAmount','LoanRange']]
tmp = tmp.drop_duplicates()
tmp = df[['LoanAmount','LoanRange']]
tmp2 = tmp[tmp['LoanRange'].notna()]

dfsum = df.groupby(['NAICS3','Zip']).agg({'City':'first', 'State':'first'
                                        , 'LoanAmount':['sum','count']
                                        , 'JobsReported':'sum' }).reset_index()
print('Total amount of loans')
print(df['LoanAmount'].sum())

# join NAICS description
#dfsum = dfsum.set_index('NAICS3').join(dfnaics.set_index('industry_code')
#                                           , on='industry_code').reset_index()
dfsum = dfsum.reset_index().set_index('NAICS3').join(dfnaics.set_index('industry_code')
                                                               ).reset_index()
dfsum.columns=['NAICS3','ind','Zip','City','State','TotalAmount','NumLoans'
                                               ,'JobsReported','NAICSdescr']
print('Total amount of loans')
print(dfsum['TotalAmount'].sum())

with pd.ExcelWriter(fpath + 'PPP.xlsx') as writer:
    dfsum[['State','City','Zip','NAICS3','NAICSdescr','TotalAmount','NumLoans'
           ,'JobsReported']].to_excel(writer, sheet_name='PPP', index=False)



fpath = '/Users/aligo/Downloads/FEMA recovery data/EIDL Data/'

# EIDL loans
eidl1 = pd.read_csv(fpath + 'EIDLLoans1.csv')

tmp = eidl1.head(1000)

eidl2 = pd.read_csv(fpath + 'EIDLLoans2.csv')

tmp = eidl2.head(1000)

eidl3 = pd.read_csv(fpath + 'EIDLLoans3.csv')

