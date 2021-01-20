# Get CDC emsemble data for HRR Excel tool
library(dplyr)
library(openxlsx)

NEstfips <- c('09','25','23','33','44','50', '36') # FIPS of states in New England + NY
#hrrnums <- c(109,110,111,221,222,227,230,231,281,282,295,364,424)

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
  filter(substr(location, start=1, stop=2) %in% NEstfips    # New England states only
         & forecast_date==latest_forecast_date & grepl( '[1-4] wk ahead inc case', target )
         & nchar(location)==5
         & type=='quantile' & quantile==0.5)
nforecasts <- length(unique(ens_fcst$target))
  
# build county to HRR crosswalk data, to assign forecasts from counties to HRRs based on population
# crosswalk obtained from https://mcdc.missouri.edu/applications/geocorr2014.html
fname <- '/Users/aligo/Downloads/FEMA recovery data/geocorr2014.csv'
colnames <- read.csv( fname, nrows=1 ) 
countyhrr <- read.csv( fname, skip=1 ) 
names(countyhrr) <- names(colnames) 
countyhrr <- countyhrr %>% mutate( COUNTYfips = sprintf("%05d", county) )
  
countyfipslst <- unique(countyhrr$COUNTYfips)
hrrnamelst <- unique(countyhrr$hrrname)

CasesofCountythatareinHRR <- function(countyfipsi, hrrnamei, ensemble){
  # COVID counts of county countyi that are within HRR hrri
  
  casescty <- ensemble %>% filter( location==countyfipsi ) # county forecast
  if("forecast_date" %in% colnames(ensemble))
  { # forecast data: nforecasts rows
    stopifnot( nrow(casescty)==nforecasts )
  }
  else
  { # historical data: npastdays rows
    if (nrow(casescty)!=npastdays)
      stop( paste0(countyfipsi, ", nrow(casescty): ", nrow(casescty)) )
  }
  tmp <- countyhrr %>% filter( hrrname==hrrnamei & COUNTYfips==countyfipsi ) # pop of county that are in HRR
  if (nrow(tmp)==1){ propctyhrr <- tmp$afact }
  else if (nrow(tmp)==0){ propctyhrr <- 0 }
  else{ stop(paste0('length propctyhrr',nrow(tmp))) }
  casescty$casesctyhrr <- casescty$value * propctyhrr
  
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
CasesofHRR <- function(hrrnamei, ensemble){
  # forecast of HRR hrrcityi
  tmp <- lapply( countyfipslst, CasesofCountythatareinHRR, hrrnamei, ensemble )
  casesofctiesinhrr <- bind_rows(tmp)
  caseshrr <- casesofctiesinhrr %>% ungroup() %>% group_by( date ) %>% 
                summarise( caseshrr = sum(casesctyhrr, na.rm=T), .groups='drop_last' )
  if("forecast_date" %in% colnames(ensemble))
    stopifnot( nrow(caseshrr)==nforecasts*7 ) # forecast data: nforecasts rows
  else
  { # historical data: npastdays rows
    if (nrow(caseshrr)!=npastdays)
      stop( paste0(hrrnamei, ", nrow(caseshrr): ", nrow(caseshrr)) )
  }
  caseshrr$hrrcity <- hrrnamei
  print( paste0(hrrnamei, ", nrow(caseshrr): ", nrow(caseshrr)) )
  return( caseshrr )
}

colseq <- c("date","Bridgeport","CT- HARTFORD","CT- NEW HAVEN"
            ,"Boston","Springfield","Worcester","Bangor","Portland"
            ,"Lebanon","Manchester","Providence","Burlington","Albany")
colseq <- c("date","CT- BRIDGEPORT","CT- HARTFORD","CT- NEW HAVEN"
            ,"MA- BOSTON","MA- SPRINGFIELD","MA- WORCESTER","ME- BANGOR","ME- PORTLAND"
            ,"NH- LEBANON","NH- MANCHESTER","RI- PROVIDENCE","VT- BURLINGTON","NY- ALBANY")
# history - raw data is cumulative
tmp <- lapply( hrrnamelst, CasesofHRR, ens_hist )
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
tmp <- lapply( hrrnamelst, CasesofHRR, ens_fcst )
inchrrs_forecast <- bind_rows(tmp) %>% tidyr::pivot_wider( names_from=hrrcity, values_from=caseshrr ) %>%
  filter( date > latest_history_date )
inchrrs_forecast <- inchrrs_forecast[colseq]

# bind history and forecast
inchrrs <- bind_rows( inchrrs_history, inchrrs_forecast )

# transform new cases to cumulative
cumulhrrs <- inchrrs
for ( col in 2:length(colseq) )
  cumulhrrs[,col] <- cumsum( inchrrs[,col] )

fname <- paste0('/Users/aligo/Downloads/FEMA recovery data/HRR_Forecast_cumul_',latest_history_date,'.xlsx')
write.xlsx( cumulhrrs, fname ) 

# DEBUG - 14-day rolling average of new cases per 100K people,
# to benchmark with https://www.dartmouthatlas.org/covid-19/hrr-mapping/
sumpophrr <- countyhrr %>% ungroup() %>% group_by( hrrname ) %>%
                summarise( pop = sum(pop14 * afact), .groups='drop_last' )
inchrrs100k <- inchrrs
for ( col in 2:length(colseq) ){
  pop <- sumpophrr$pop[sumpophrr$hrrname == colseq[col]]
  inchrrs100k[,col] <- zoo::rollsum( inchrrs100k[[col]] / pop * 100e3
                                      , k=14, fill=NA, align="right" )
}
fname <- paste0('/Users/aligo/Downloads/FEMA recovery data/HRR_Forecast100K14d_',latest_history_date,'.xlsx')
write.xlsx( inchrrs100k, fname ) 

c <- unique(ens_fcst$location)
s <- sample( c, 16, replace = FALSE )
tmp <- ens_fcst %>% filter( location %in% s ) %>%
        mutate( date=as.Date(target_end_date, format="%Y-%m-%d") )
ggplot( tmp, aes(x=date, y=value) ) +
  facet_wrap(~location, nrow=4, scales='free_y') +
 geom_line()
