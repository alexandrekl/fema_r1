#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 17 06:46:44 2020
    
Import data from BLS API

@author: aligo
"""

fpath = '/Users/aligo/git-repos/FEMA/BLS_data/'
countyfile = 'County codes for BLS data.xlsx'
blsurl = 'https://data.bls.gov/cew/data/api/2020/1/area/'

import pandas as pd

# naics codes downloaded from https://data.bls.gov/cew/doc/titles/industry/industry_titles.csv
dfnaics = pd.read_csv(fpath + 'industry_titles.csv')
dfnaics['industry_title'] = dfnaics['industry_title'].str.replace(
                                      'NAICS \d+ ','').str.replace('\d+ ','')

dflocations = pd.read_excel(fpath + countyfile)

states = list(dflocations['State'].unique())
# this for loop froze after 30 or so counties... had to use the loop below 
# with counties downloaded manually
for st in states:
    counties = list(dflocations.loc[dflocations.State.eq(st),'County'])
    df = pd.DataFrame()
    for c in counties:
        u = blsurl + f'{c:05}' + '.csv'
        df = df.append(pd.read_csv(u))
        print( 'URL downloaded: ' + u)
    df.to_csv(fpath + st + '.csv')
print('Done!')

# this was done because the above failed in VT and after
for st in states[3:6]:
    counties = list(dflocations.loc[dflocations.State.eq(st),'County'])
    df = pd.DataFrame()
    for c in counties:
        f = fpath + st + '/' + f'{c:05}' + '.csv'
        df = df.append(pd.read_csv(f))
    df.to_csv(fpath + st + '.csv')
    
    
# Filter data by given number of NAICS digits
with pd.ExcelWriter(fpath + 'bls_R1.xlsx') as writer:
    for st in states:
        df = pd.read_csv(fpath + st + '.csv')
        # select relevant columns
        dff = df.assign(naics_length = df.industry_code.str.len(), emplvl = round(
             (df['month1_emplvl']+df['month2_emplvl']+df['month3_emplvl'])/3))
        dff = dff.set_index('industry_code').join(dfnaics.set_index('industry_code')
                                           , on='industry_code').reset_index()
        dff = dff[['area_fips','own_code','industry_code','naics_length'
                   ,'industry_title','year','qtr','qtrly_estabs','emplvl']]
        dff.to_excel(writer, sheet_name=st, index=False)
    # add legend
    dt = {'area_fips': ['5-character County code (FIPS code)']
          ,'own_code': ['1-character ownership code: 0 Total Covered, 5 Private, 4 International Government, 3 Local Government, 2 State Government, 1 Federal Government, 8 Total Government, 9	Total U.I. Covered (Excludes Federal Government)']
          ,'industry_code':['2 to 6-character industry code (NAICS, SuperSector)']
          ,'naics_length':['number of digits in NAICS code']
          ,'industry_title':['description of NAICS code']
          ,'year':['year data is reported']
          ,'qtr':['quarter data is reported']
          ,'qtrly_estabs':['Count of establishments for a given quarter']
          ,'emplvl':['Employment level (quarter)']
          ,' ':[' ']
          ,'Source':['https://data.bls.gov/cew/doc/access/csv_data_slices.htm#AREA_SLICES and https://www.bls.gov/cps/definitions.htm#employed']
          }
    dfleg = pd.DataFrame.from_dict(dt, orient='index', columns=['Description'])
    dfleg.to_excel(writer, sheet_name='legend', index=True)
    
    
    
# The code below is for use of the BLS API https://www.bls.gov/developers/
# But I am not using it
import requests
import json
import numpy as np

headers = {'Content-type': 'application/json'}
data = json.dumps({"seriesid": ['ENU09001205111150','ENU09001205000044'],"startyear":"2020", "endyear":"2020"})
p = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/', data=data, headers=headers)
json_data = json.loads(p.text)
for series in json_data['Results']['series']:
#    x=prettytable.PrettyTable(["series id","year","period","value","footnotes"])
    df = pd.DataFrame(columns=["seriesid","year","period","value","footnotes"])
    seriesId = series['seriesID']
    for item in series['data']:
        year = item['year']
        period = item['period']
        value = item['value']
        footnotes=""
        for footnote in item['footnotes']:
            if footnote:
                footnotes = footnotes + footnote['text'] + ','
        #if 'M01' <= period <= 'M12':'
            #x.add_row([seriesId,year,period,value,footnotes[0:-1]])
        dfrow = pd.DataFrame(np.array([[seriesId,year,period,value,footnotes[0:-1]]])
                , columns=["seriesid","year","period","value","footnotes"])
        df.append(dfrow)   
#    output = open(seriesId + '.txt','w')
#    output.write (x.get_string())
#    output.close()
    df.to_excel('/Users/aligo/git-repos/FEMA/BLS_data/' + seriesId + '.xlsx')
    
