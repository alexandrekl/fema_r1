# Get CDC emsemble data for HRR Excel tool
library(dplyr)
library(openxlsx)

latest_forecast_date <- '2021-01-11'

NEstfips <- c('09','25','23','33','44','50', '36') # FIPS of states in New England + NY

# truth URL from the CDC ensemble 
turl <- 'https://github.com/CSSEGISandData/COVID-19/raw/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'
df <- read.csv( turl ) %>% tidyr::pivot_longer( cols = starts_with("X")
                                  , names_to="date", names_prefix="X"
                                  , values_to = "value",  values_drop_na = TRUE ) %>%
              mutate( date=as.Date(gsub("\\.","\\/",date), format="%m/%d/%y")
                      , location=sprintf("%05d", FIPS) ) %>%
              filter( substr(location, start=1, stop=2) %in% NEstfips )
ens_hist <- df %>% filter( nchar(location)==5 ) # date <= "2021-01-11" location == '25' & 
latest_history_date <- max(ens_hist$date)
tmp <- latest_history_date - min(ens_hist$date)
npastdays <- tmp[[1]] + 1
  
# read URL of CDC ensemble forecasts per county
eurl <- paste0('https://github.com/reichlab/covid19-forecast-hub/raw/master/data-processed/COVIDhub-ensemble/' 
                                          , latest_forecast_date, '-COVIDhub-ensemble.csv')
df <- read.table( eurl, sep = ',', header = T ) # fields are explained in https://github.com/reichlab/covid19-forecast-hub/blob/master/data-processed/README.md#quantile

# N wk ahead inc case
# This target is the incident (weekly) number of cases predicted by the model during the week that is N weeks after forecast_date.
# A week-ahead forecast should represent the total number of new cases reported during a given epiweek (from Sunday through Saturday, inclusive).
# Predictions for this target will be evaluated compared to the number of new reported cases, as recorded by JHU CSSE.
# location: FIPS (we get 5-digit that represent counties)
# type/quantile: we get median
ens_fcst <- df %>%
  filter(substr(location, start=1, stop=2) %in% NEstfips    # New England states only
         & forecast_date==latest_forecast_date & grepl( '[1-4] wk ahead inc case', target )
         & nchar(location)==5
         & type=='quantile' & quantile==0.5)
nforecasts <- length(unique(ens_fcst$target))
  
# build county to HRR crosswalk data, to assign forecasts from counties to HRRs based on population
tmp <- tempfile()
download.file('https://atlasdata.dartmouth.edu/downloads/geography/ZipHsaHrr18.csv.zip',tmp)
ziphrr <- read.table( unz(tmp, 'ZipHsaHrr18.csv'), sep=',', quote="", header=T, colClasses='character' )
unlink(tmp)
# New england HRRs
ziphrrne <- ziphrr %>% filter( hrrnum %in% c(109,110,111,221,222,227,230,231,281,282,295,364,424))
# ZIPcode to County Code crosswalk from https://www.huduser.gov/portal/datasets/usps_crosswalk.html#data
tmp <- readxl::read_xlsx('/Users/aligo/Downloads/FEMA recovery data/ZIP_COUNTY_092020.xlsx', col_types=c('text')) %>%
              mutate( RES_RATIO=as.numeric(RES_RATIO), BUS_RATIO=as.numeric(BUS_RATIO)
                      , OTH_RATIO=as.numeric(OTH_RATIO), TOT_RATIO=as.numeric(TOT_RATIO) ) # %>%
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

CasesofCountythatareinHRR <- function(countyi, hrrcityi, ensemble){
  # forecast of county countyi that are within HRR hrrcityi
  
  casescty <- ensemble %>% filter( location==countyi ) # county forecast
  if("forecast_date" %in% colnames(ensemble))
  { # forecast data: nforecasts rows
    stopifnot( nrow(casescty)==nforecasts )
  }
  else
  { # historical data: npastdays rows
    if (nrow(casescty)!=npastdays)
      stop( paste0(countyi, ", nrow(casescty): ", nrow(casescty)) )
  }
  tmp <- sumpopctyhrr %>% filter( hrrcity==hrrcityi & COUNTY==countyi ) # pop of county that are in HRR
  if (nrow(tmp)==1){ popctyhrr <- tmp$pop }
  else if (nrow(tmp)==0){ popctyhrr <- 0 }
  else{ stop(paste0('length popctyhrr',nrow(tmp))) }
  popcty <- sumpopcty %>% filter( COUNTY==countyi ) # pop of county
  stopifnot( nrow(popcty)==1 )
  casescty$casesctyhrr <- casescty$value * popctyhrr / popcty$pop
  
  if("forecast_date" %in% colnames(ensemble))
  { # forecast data (weekly)
    # change weekly to daily frequency (linearly)
    daily <- casescty[rep(seq_len(nrow(casescty)), each=7),]
    daily$date <- seq( from=as.Date(casescty$forecast_date[1]), by="days", length.out=nrow(daily) )
    daily$casesctyhrr <- daily$casesctyhrr / 7
    return( daily )
  }
  else
  { # historical data is already daily
    return( casescty )
  }
}
CasesofHRR <- function(hrrcityi, ensemble){
  # forecast of HRR hrrcityi
  tmp <- lapply( countylst, CasesofCountythatareinHRR, hrrcityi, ensemble )
  casesofctiesinhrr <- bind_rows(tmp)
  caseshrr <- casesofctiesinhrr %>% ungroup() %>% group_by( date ) %>% 
                summarise( caseshrr = sum(casesctyhrr, na.rm=T) )
  if("forecast_date" %in% colnames(ensemble))
    stopifnot( nrow(caseshrr)==nforecasts*7 ) # forecast data: nforecasts rows
  else
  { # historical data: npastdays rows
    if (nrow(caseshrr)!=npastdays)
      stop( paste0(hrrcityi, ", nrow(caseshrr): ", nrow(caseshrr)) )
  }
  caseshrr$hrrcity <- hrrcityi
  return( caseshrr )
}

colseq <- c("date","Bridgeport","Hartford","New Haven"
            ,"Boston","Springfield","Worcester","Bangor","Portland"
            ,"Lebanon","Manchester","Providence","Burlington","Albany")
# history - raw data is cumulative
tmp <- lapply( hrrcities, CasesofHRR, ens_hist )
cumulhrrs_history <- bind_rows(tmp) %>% tidyr::pivot_wider( names_from=hrrcity, values_from=caseshrr )
cumulhrrs_history <- cumulhrrs_history[colseq]
# new cases with smoothing through 7-day moving average
inchrrs_history <- cumulhrrs_history
for ( col in 2:length(colseq) )
{
  inchrrs_history[col] <- zoo::rollmean( diff( c(0,cumulhrrs_history[[col]]) ) 
                                    , k=7, fill=0, align="right" )
}

# forecast - raw data is NEW CASES
tmp <- lapply( hrrcities, CasesofHRR, ens_fcst )
inchrrs_forecast <- bind_rows(tmp) %>% tidyr::pivot_wider( names_from=hrrcity, values_from=caseshrr ) %>%
  filter( date > latest_history_date )
inchrrs_forecast <- inchrrs_forecast[colseq]

# bind history and forecast
inchrrs <- bind_rows( inchrrs_history, inchrrs_forecast )

# transform new cases to cumulative
cumulhrrs <- inchrrs
for ( col in 2:length(colseq) )
  cumulhrrs[,col] <- cumsum( inchrrs[,col] )

# for ( col in 2:length(colseq) )
#  caseshrrs_forecast[,col] <- cumsum( caseshrrs_forecast[,col] )

# forecast - raw data is NEW CASES
# tmp <- lapply( hrrcities, CasesofHRR, ens_fcst )
# caseshrrs_forecast <- bind_rows(tmp) %>% tidyr::pivot_wider( names_from=hrrcity, values_from=caseshrr ) %>%
#                      filter( date >= latest_history_date )
#caseshrrs_forecast <- caseshrrs_forecast[colseq]
# transform new cases to cumulative
#caseshrrs_forecast[caseshrrs_forecast$date==latest_history_date,] = caseshrrs_history[caseshrrs_history$date==latest_history_date,]
# for ( col in 2:length(colseq) )
#  caseshrrs_forecast[,col] <- cumsum( caseshrrs_forecast[,col] )

# caseshrrs_forecast <- caseshrrs_forecast %>% filter( date > latest_history_date) # delete first row

# bind history and forecast
# caseshrrs <- bind_rows( caseshrrs_history, caseshrrs_forecast )

fname <- paste0('/Users/aligo/Downloads/FEMA recovery data/HRR_Forecast_cumul_',latest_history_date,'.xlsx')
write.xlsx( cumulhrrs, fname ) 

# DEBUG - 14-day rolling average of new cases per 100K people,
# to benchmark with https://www.dartmouthatlas.org/covid-19/hrr-mapping/
sumpophrr <- sumpopctyhrr %>% ungroup() %>% group_by( hrrcity ) %>%
                summarise( pop = sum(pop), .groups='drop_last' )
inchrrs100k <- inchrrs
for ( col in 2:length(colseq) ){
  pop <- sumpophrr$pop[sumpophrr$hrrcity == colseq[col]]
  inchrrs100k[,col] <- zoo::rollsum( inchrrs100k[[col]] / pop * 100e3
                                      , k=14, fill=NA, align="right" )
}
fname <- paste0('/Users/aligo/Downloads/FEMA recovery data/HRR_Forecast100K14d_',latest_history_date,'.xlsx')
write.xlsx( inchrrs100k, fname ) 

  