# Get CDC emsemble data for State Excel tool
library(dplyr)
library(openxlsx)

quants <- c(0.5, 0.9, 0.975) # quantiles to consider from ensemble forecast

NEstfips <-  c('09','25','23','33','44','50') # FIPS of states in New England
NEstNames <- c('CT','MA','ME','NH','RI','VT') # FIPS of states in New England

# truth URL from the CDC ensemble 
turl <- 'https://github.com/CSSEGISandData/COVID-19/raw/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv'
tmp <- read.csv( turl ) 
df <- tmp %>% tidyr::pivot_longer( cols = starts_with("X")
                                  , names_to="date", names_prefix="X"
                                  , values_to = "value",  values_drop_na = TRUE ) %>%
              mutate( date=as.Date(gsub("\\.","\\/",date), format="%m/%d/%y")
                      , location=substr(sprintf("%05d", FIPS), start=1, stop=2) ) %>%
              filter( location %in% NEstfips )
ens_hist <- df %>% # filter( nchar(location)==5 ) %>%
                group_by( location, date ) %>%
                summarise( value = sum(value), .groups='drop_last' )
latest_history_date <- max(ens_hist$date)
tmp <- latest_history_date - min(ens_hist$date)
npastdays <- tmp[[1]] + 1
  
# read URL of CDC ensemble forecasts per state
d <- Sys.Date() # today's date
repeat {
  s <- as.character(d, '%Y-%m-%d')
  eurl <- paste0('https://github.com/reichlab/covid19-forecast-hub/raw/master/data-processed/COVIDhub-ensemble/' 
                 , s, '-COVIDhub-ensemble.csv')
  if ( RCurl::url.exists(eurl, .header = FALSE) ){
    latest_forecast_date <- s
    print( paste0('FOUND latest_forecast_date: ', latest_forecast_date) )
    break
  }
  print( paste0('Checked forecast for ', s) )
  d <- d - 1
}

df <- read.table( eurl, sep = ',', header = T ) # fields are explained in https://github.com/reichlab/covid19-forecast-hub/blob/master/data-processed/README.md#quantile

# N wk ahead inc case
# This target is the incident (weekly) number of cases predicted by the model during the week that is N weeks after forecast_date.
# A week-ahead forecast should represent the total number of new cases reported during a given epiweek (from Sunday through Saturday, inclusive).
# Predictions for this target will be evaluated compared to the number of new reported cases, as recorded by JHU CSSE.
# location: FIPS (we get 5-digit that represent counties)
# type/quantile: we get median
ens_fcst <- df %>%
  filter( forecast_date==latest_forecast_date & grepl( '[1-4] wk ahead inc case', target )
          & nchar(location)==2  # state data only
          & trimws(location, which='both') %in% NEstfips    # New England states only
          & type=='quantile' & (quantile %in% quants) )  # filter desired quantiles
nforecasts <- length(unique(ens_fcst$target)) # number of forecasts per location/quantile
  
CasesofState <- function(statefipsi, quantilei, ensemble){
  # COVID counts of state i
  
  if("forecast_date" %in% colnames(ensemble))
  { # forecast data: nforecasts rows
    casesst <- ensemble %>% filter( location==statefipsi & quantile==quantilei) # county forecast
    stopifnot( nrow(casesst)==nforecasts )
  }
  else
  { # historical data: npastdays rows
    casesst <- ensemble %>% filter( location==statefipsi ) # county forecast
    if (nrow(casesst)!=npastdays)
      stop( paste0(casesst, ", nrow(casescty): ", nrow(casesst)) )
  }
  casesst$quantile <- quantilei
  
  if("forecast_date" %in% colnames(ensemble))
  { # forecast data (weekly)
    # change weekly to daily frequency (linearly)
    daily <- casesst[rep(seq_len(nrow(casesst)), each=7),]
    daily$date <- seq( from=as.Date(casesst$forecast_date[1]), by="days", length.out=nrow(daily) )
    daily$casesst <- daily$value / 7
  }
  else
  { # historical data is already daily
    daily <- casesst %>% rename( casesst = value )
  }
  print( paste0(statefipsi, ", quantile ", quantilei, ", nrow(daily): ", nrow(daily)) )
  return( daily )
}

colseq <- c("date", "quantile", NEstfips)
# history - raw data is cumulative
tmp <- lapply( NEstfips, CasesofState, 0, ens_hist )
cumulsts_history <- bind_rows(tmp) %>% tidyr::pivot_wider( names_from=location, values_from=casesst )
cumulsts_history <- cumulsts_history[colseq]

# history of new cases with smoothing through 7-day moving average
incsts_history_raw <- cumulsts_history
incsts_history <- cumulsts_history
for ( col in 3:length(colseq) ){
  incsts_history_raw[col] <- diff( c(0,cumulsts_history[[col]]) )
  # smoothed
  incsts_history[col] <- zoo::rollmean( incsts_history_raw[col], k=7, fill=0, align="right" )
}
# Non-smoothed incidence history to Excel
fname <- paste0('/Users/aligo/Downloads/FEMA recovery data/STATE_History_inc_',latest_history_date,'.xlsx')
wb <- createWorkbook( 'inc' )
addWorksheet(wb, "NOT SMOOTHED")
addWorksheet(wb, "SMOOTHED")
tmp <- list(incsts_history_raw, incsts_history)
sapply( 1:2, function( i ){
  dt <- tmp[[i]] %>% select(-quantile) %>% filter( date >= "2020-06-01" )
  names( dt ) <- c('date', NEstNames)
  writeData(wb, sheet = i, dt )
} )
saveWorkbook(wb, fname, overwrite = TRUE)
#  write.xlsx( , fname ) 

# transform history of new cases to cumulative
cumulsts_history <- incsts_history
for ( col in 3:length(colseq) )
  cumulsts_history[,col] <- cumsum( incsts_history[,col] )

# forecast - raw data is NEW CASES
CasesofQuartile <- function(quantilei){
  tmp <- lapply( NEstfips, CasesofState, quantilei, ens_fcst )
  incsts_forecast <- bind_rows(tmp) %>% select( date, location, quantile, casesst ) %>%
    tidyr::pivot_wider( names_from=location, values_from=casesst ) %>%
    filter( date > latest_history_date )
  incsts_forecast <- incsts_forecast[colseq]
  # extent forecast until thursday (for compatibility with Excel formulas)
  end_date <- max(incsts_forecast$date)
  while ( weekdays(as.Date(end_date)) != "Thursday" ){
    newrow <- incsts_forecast[nrow(incsts_forecast),]
    end_date <- end_date + 1
    newrow$date <- end_date
    incsts_forecast <- bind_rows( incsts_forecast, newrow )
  }
  # transform new cases to cumulative
  cumulsts_forecast <- bind_rows( cumulsts_history %>% filter( date==latest_history_date )
                                    , incsts_forecast )
  for ( col in 3:length(colseq) )
    cumulsts_forecast[,col] <- cumsum( cumulsts_forecast[,col] )
  
  cumulsts_forecast <- cumulsts_forecast %>% filter( date > latest_history_date )
  return( cumulsts_forecast )
}  
tmp <- lapply( quants, CasesofQuartile )
cumulsts_forecast <- bind_rows(tmp)

# bind history and forecast
cumulsts <- bind_rows( cumulsts_history, cumulsts_forecast )

# Data to be copied to Excel STATE tool 
fname <- paste0('/Users/aligo/Downloads/FEMA recovery data/STATE_Forecast_cumul_',latest_history_date,'.xlsx')
write.xlsx( filter( cumulsts, date >= "2020-09-01" ), fname ) 

# DEBUG
tmp <- ens_fcst %>% # filter( location %in% s ) %>%
        mutate( date=as.Date(target_end_date, format="%Y-%m-%d") )
ggplot( tmp, aes(x=date, y=value) ) +
  facet_wrap(~location, nrow=4, scales='free_y') +
 geom_line()
