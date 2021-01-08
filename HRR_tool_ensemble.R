# Get CDC emsemble data for HRR Excel tool
library(dplyr)
library(openxlsx)

# read URL of CDC ensemble forecasts per county
latest_data <- '2020-12-28'
eurl <- paste0('https://github.com/reichlab/covid19-forecast-hub/raw/master/data-processed/COVIDhub-ensemble/' 
                                          , latest_data, '-COVIDhub-ensemble.csv')
# truth URL
turl <- 'https://github.com/reichlab/covid19-forecast-hub/raw/master/data-truth/truth-Incident%20Cases.csv'
  
df <- read.table( eurl, sep = ',', header = T )  # fields are explained in https://github.com/reichlab/covid19-forecast-hub/blob/master/data-processed/README.md#quantile

# N wk ahead inc case
# This target is the incident (weekly) number of cases predicted by the model during the week that is N weeks after forecast_date.
# A week-ahead forecast should represent the total number of new cases reported during a given epiweek (from Sunday through Saturday, inclusive).
# Predictions for this target will be evaluated compared to the number of new reported cases, as recorded by JHU CSSE.
# location: FIPS (we get 5-digit that represent counties)
# type/quantile: we get median
ensemble <- df %>%
  filter(forecast_date==latest_data & grepl( '[1-4] wk ahead inc case', target )
         & nchar(location)==5
         & type=='quantile' & quantile==0.5)
nforecasts <- length(unique(ensemble$target))
  
# build county to HRR crosswalk data, to assign forecasts from counties to HRRs based on population
tmp <- tempfile()
download.file('https://atlasdata.dartmouth.edu/downloads/geography/ZipHsaHrr18.csv.zip',tmp)
ziphrr <- read.table( unz(tmp, 'ZipHsaHrr18.csv'), sep=',', quote="", header=T, colClasses='character' )
unlink(tmp)
# New england HRRs
ziphrrne <- ziphrr %>% filter( hrrnum %in% c(109,110,111,221,222,227,230,231,281,282,295,364,424))
# ZIPcode to County Code crosswalk from https://www.huduser.gov/portal/datasets/usps_crosswalk.html#data
tmp <- readxl::read_xlsx('/Users/aligo/Downloads/FEMA recovery data/ZIP_COUNTY_092020.xlsx'
                               , col_types=c('text','text','numeric','numeric','numeric','numeric')) #%>%
#  group_by(ZIP) %>% mutate( ratio=max(TOT_RATIO) ) %>% ungroup()
zipcounty <- tmp #%>% filter( ratio == TOT_RATIO ) # keep county with biggest ratio of all addresses in the ZIP–County to the total number of all addresses in the entire ZIP.
#zip/county/hrr
zipctyhrr <- inner_join(ziphrrne, select(zipcounty,ZIP,COUNTY,TOT_RATIO), by=c('zipcode18'='ZIP'))
countylst <- unique(zipctyhrr$COUNTY)
#add zipcode population
zipop <- read.table( unz('/Users/aligo/Downloads/FEMA recovery data/ACSST5Y2019.S0101_2020-12-30T143736.zip'
                         , 'ACSST5Y2019.S0101_data_with_overlays_2020-12-30T143117.csv'), sep=',', skip=2 ) %>%
  mutate( ZIP=substr(V2, 7, 12), ZIPOP=V3 )
zip_cty_hrr_pop <- left_join(zipctyhrr, select(zipop, ZIP, ZIPOP), by=c('zipcode18'='ZIP'))
zip_cty_hrr_pop$ZIPOP[is.na(zip_cty_hrr_pop$ZIPOP)] <- 0

# population by county,HRR
sumpopctyhrr <- zip_cty_hrr_pop %>% ungroup() %>%
              group_by(hrrcity,COUNTY) %>% summarise( pop = sum(ZIPOP*TOT_RATIO) )
hrrcities <- unique( sumpopctyhrr$hrrcity )
# population by county
sumpopcty <- zip_cty_hrr_pop %>% ungroup() %>%
              group_by(COUNTY) %>% summarise( pop = sum(ZIPOP*TOT_RATIO) )

CasesofCountythatareinHRR <- function(countyi, hrrcityi){
  # forecast of county countyi that are within HRR hrrcityi
  
  casescty <- ensemble %>% filter( location==countyi ) # county forecast
  stopifnot( nrow(casescty)==nforecasts )
  tmp <- sumpopctyhrr %>% filter( hrrcity==hrrcityi & COUNTY==countyi ) # pop of county that are in HRR
  if (nrow(tmp)==1){ popctyhrr <- tmp$pop }
  else if (nrow(tmp)==0){ popctyhrr <- 0 }
  else{ stop(paste0('length popctyhrr',nrow(tmp))) }
  popcty <- sumpopcty %>% filter( COUNTY==countyi ) # pop of county
  stopifnot( nrow(popcty)==1 )
  casescty$casesctyhrr <- casescty$value * popctyhrr / popcty$pop
  
  # change weekly to daily frequency (linearly)
  daily <- casescty[rep(seq_len(nrow(casescty)), each=7),]
  daily$target_end_date <- seq( from=as.Date(casescty$forecast_date[1]), by="days", length.out=nrow(daily) )
  daily$casesctyhrr <- daily$casesctyhrr / 7
  return( daily )
}
CasesofHRR <- function(hrrcityi){
  # forecast of HRR hrrcityi
  tmp <- lapply( countylst, CasesofCountythatareinHRR, hrrcityi )
  casesofctiesinhrr <- bind_rows(tmp)
  caseshrr <- casesofctiesinhrr %>% ungroup() %>% group_by(target, target_end_date) %>% 
                summarise( caseshrr = sum(casesctyhrr, na.rm=T) )
  stopifnot( nrow(caseshrr)==nforecasts*7 )
  caseshrr$hrrcity <- hrrcityi
  return( caseshrr )
}

tmp <- lapply( hrrcities, CasesofHRR )
caseshrrs_forecast <- bind_rows(tmp) %>% tidyr::pivot_wider( names_from=hrrcity, values_from=caseshrr )
caseshrrs_forecast <- caseshrrs_forecast[c("target","target_end_date","Bridgeport","Hartford","New Haven"
                   ,"Boston","Springfield","Worcester","Bangor","Portland"
                   ,"Lebanon","Manchester","Providence","Burlington","Albany")]

caseshrrs <- bind_rows( caseshrrs_history, caseshrrs_forecast )

fname <- paste0('/Users/aligo/Downloads/FEMA recovery data/HRR_Forecast_',latest_data,'.xlsx')
write.xlsx( caseshrrs, fname ) 
