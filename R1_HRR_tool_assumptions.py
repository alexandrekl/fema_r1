#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec  7 12:12:36 2020

@author: aligo
"""

# assumptions for bed capacity and utilization

import pandas as pd

fpath = '/Users/aligo/Box/2020 RisknDecScience/FEMA recovery/R1 tool/'

hrr = pd.read_csv(fpath + 'HRR_hospital_12-4-2020.csv')

hrr['valid'] = pd.to_datetime(hrr['valid'])

hrr = hrr[hrr.valid.gt(pd.to_datetime('11/04/2020', format='%m/%d/%Y'))]

calcs = ['median','min','max']
hrrm = hrr.groupby(['hrrstate','hrrcity','fema_regio']).agg({'inpat_beds':calcs
                    ,'inpat_be_1':calcs, 'inpat_be_2':calcs, 'total_icu_':calcs
                    , 'icu_used':calcs, 'icu_used_c':calcs})

# convert to wide format with fema_regio in columns
hrrw = hrrm.reset_index().pivot(index=['hrrstate','hrrcity'], columns='fema_regio')

hrrt = hrrw.T
