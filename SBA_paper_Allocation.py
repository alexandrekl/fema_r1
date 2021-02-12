#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb  5 16:52:59 2021

@author: aligo
"""

import pandas as pd
import numpy as np

# 2-digit NAICS sectors to include in the analysis
NAIC2lst = ['23' # Construction
            , '44-45' # (retail)
            , '54' # Professional and technical services
            , '62' # (health & social, includes childcare)
            , '72'] #(accommodation & food)]

fpath = '/Users/aligo/Box/1 RisknDecScience/FEMA recovery/SBA paper/data/'

# read nloans, amount, nestablishments per county and NAIC2 sector
pen = pd.read_excel(fpath + 'PPPpenetrationBLS_County_NAICS2US.xlsx', engine='openpyxl' # , dtype={'STATEFP10':'object','COUNTYFP10':'object'}
                           )
# keep selected NAICS only
pens = pen[pen['NAICS2'].isin(NAIC2lst)]

tmp = pens['']
# optmize allocation to maximize penetration
#max Sum[all county-naics pairs](Nloansi / NEstabsi)
#	s.t. Sum[all county-naics pairs](Nloansi) = Ntotal
#		Nloansi <= NEstabsi
#		Nloansi >= 0

# Constraints
n = pens.shape[0] # number of decision variables: county-NAICS pairs
NEstabsTot = pens['NEstabs'].sumn()
# Sum[all county-naics pairs](Nloansi) = NEstabsTot
A_eq = np.ones( (1,n) ) 
b_eq = [NEstabsTot]
# Nloansi <= NEstabsi
A_ub = np.identity( n )
b_ub = pens['NEstabs'].to_numpy()

# vector of coefficients of objective function: 1/NEstabsi
c = 1 / b_ub
c = ( 1 / pens['NEstabs'] ).array

