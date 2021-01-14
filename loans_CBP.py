#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 20 13:23:36 2020
v2 version of this script was to work with BLS QCEW data
v3 version is to work 
@author: aligo
"""

import loans_common as co

import pandas as pd
import zipfile
from plotnine import *    # python lib to use ggplot
from io import BytesIO
from urllib.request import urlopen

naics = 'NAICS2'
excsole = False

loans = co.ReadPPPdata(naics)

# Number of loans per county and NAICS2
[loans_y, countyfips] = co.MatchCounties(loans, excsole, naics)

# EXECUTE THIS COMMAND ONLY AFTER CHECKING THE EXCEL FILE OF UNMATCHED LOANS in Downloads/
loansum = co.AddManualCounties(loans_y, excsole, naics)

# TOTAL NUMBER OF BUSINESSES - from US Census CBP
url = urlopen("https://www2.census.gov/programs-surveys/cbp/datasets/2018/cbp18co.zip")
#Download Zipfile and create pandas DataFrame
zipfile = zipfile.ZipFile(BytesIO(url.read()))
cbp = pd.read_csv(zipfile.open('cbp18co.txt'), na_values='N')

cbp['FIPST'] = cbp['fipstate'].astype(str).str.pad(2,fillchar='0')
cbp['area_fips'] = cbp['FIPST'] + cbp['fipscty'].astype(str).str.pad(3,fillchar='0')
cnt = cbp[cbp['FIPST'].isin(co.NEstfips)    # New England counties
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
cnt = co.OverrideNAICS2(cnt)

pen = co.CalcPenetration(loansum, cnt, naics)

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





