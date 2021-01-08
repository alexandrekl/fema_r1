#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  8 14:52:34 2021
Common code for loans_BLS.py and loans_CBP.py
@author: aligo
"""

import glob
import pandas as pd

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