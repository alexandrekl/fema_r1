library(dplyr)
library(zoo)
library(ggplot2)
library(openxlsx)

theme_set( theme_bw() + theme( legend.position="bottom" ) +
             theme( legend.title=element_blank() ) +
             theme(plot.title = element_text(hjust = 0.5) ) +
             theme( text = element_text(size=16) ) )

# Assumptions
waste_rate <- 0.0013  # rate of doses lost
t1st2nd <- (21+28)/2  # average time between 1st and 2nd dose

# Constants
dfmts <- c('%Y-%m-%d', '%m/%d/%Y')
NEstates <- c('Connecticut','Maine','Massachusetts','New Hampshire','Rhode Island','Vermont')
nper <- 14 # days to smooth supply

# truth URL from the CDC ensemble 
vurl <- 'https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/vaccinations/us_state_vaccinations.csv'
df <- read.csv( vurl ) 

# Calculate daily history
# (current capacity to administer doses per day is in daily_vaccinations - 7-day moving avg)
dcap <- df %>% filter( location %in% NEstates ) %>% 
  select( date,location,total_vaccinations,total_distributed,daily_vaccinations,people_vaccinated,people_fully_vaccinated ) %>%
  group_by( location ) %>%
  mutate( date = as.Date(date, tryFormats = dfmts)
          , total_vaccinations = na.approx( total_vaccinations, na.rm=FALSE )
          , total_distributed = na.approx( total_distributed, na.rm=FALSE )
          , daily_available = total_distributed*(1-waste_rate) - total_vaccinations # total availability level IGNORING WASTE
          , daily_available_avg = rollmean(daily_available, k=nper, fill=NA, align="right") # total availability level IGNORING WASTE
          #, daily_distributed = c(NA, diff(total_distributed))  # supply of doses per day
  ) %>% ungroup()
latest_history_date <- max(dcap$date)

# plot cummulative supply and capacity
colors <- c('total_distributed','total_vaccinations','daily_available')
dp <- dcap %>% select(c('date','location',colors)) %>%
#     mutate( daily_distributed_avg = rollmean(daily_distributed, k=7, fill=0, align="right") ) %>% 
     tidyr::pivot_longer( cols = all_of(colors), names_to="s" 
                            , values_to = "value",  values_drop_na = TRUE )
cnames <- c('(I) Total distributed','(II) Total vaccinations','Supply level (I-II)')
dp <- dp %>% mutate( n = NA )
dp$n[dp$s %in% colors] <- cnames[match(dp$s,colors)]
ggplot( dp, aes(x = date, y=value, color=n) ) +
   facet_wrap('~ location', nrow=2, scale='free_y' ) +
   geom_line() + 
  theme(axis.title.x = element_blank()) +
  ylab('Total Number of Doses') +
  scale_y_continuous(label = scales::unit_format(unit = "K", scale = 1e-3, sep = "")
                      , expand = c(0, 0), limits = c(0, NA))

# plot smoothed supply
dp <- dcap %>% select(date,location,daily_available,daily_available_avg) %>%
  tidyr::pivot_longer( cols = c('daily_available','daily_available_avg'), names_to="s" 
                       , values_to = "value",  values_drop_na = TRUE )
ggplot( dp, aes(x = date, y=value, color=s) ) +
  facet_wrap('~ location', nrow=2, scale='free_y' ) +
  geom_line() + 
  theme(axis.title.x = element_blank()) +
  ylab('Total Number of Doses') +
  scale_y_continuous(label = scales::unit_format(unit = "K", scale = 1e-3, sep = "")
                     , expand = c(0, 0), limits = c(0, NA))

# plot daily_vaccinations (it is already 7-day smoothed in the original data)
dp <- dcap %>% select(date,location,daily_vaccinations) 
ggplot( dp, aes(x = date, y=daily_vaccinations) ) +
  facet_wrap('~ location', nrow=2, scale='free_y' ) +
  geom_line() + 
  theme(axis.title.x = element_blank()) +
  ylab('Daily Vaccinations') +
  scale_y_continuous(label = scales::unit_format(unit = "K", scale = 1e-3, sep = "")
                     , expand = c(0, 0), limits = c(0, NA))

# Forecast function
fcastfn <- function( l, c ){
  # bt = NULL: function tries to find
  # bt = FALSE: exponential smoothing only
  dt <- dcap %>% filter( location == l ) %>% 
    select( all_of(c('date',c)) ) 
  z <- read.zoo( dt )
  zz <- z
  time(zz) <- seq_along(time(zz))
  # forecast model
  sm <- HoltWinters( as.ts(zz[-(1:(nper-1))]), gamma=FALSE )  # , alpha=0.3, gamma=FALSE )
#  sm <- HoltWinters( as.ts(zz[-(1:(nper-1))]), gamma=FALSE ) 
  # tmp <- HoltWinters( as.ts(zz), alpha=0.5, beta=FALSE, gamma=FALSE )
  print( paste('location', l, 'alpha', sm$alpha, 'beta', sm$beta, 'level', sm$coefficients['a'], 'trend', sm$coefficients['b']) )
  pr <- predict(sm, 14, prediction.interval=TRUE, level = 0.95)
#  plot(sm, pr)
  dates <- seq(max(dt$date)+1, by = "day", length.out = 14)
  prdf <- data.frame( dates, pr ) 
  prdf[prdf < 0] <- 0    # override negative predictions
  cols <- paste0(c, '_', colnames(prdf[1,-1]))
  colnames(prdf) <- c('date',cols)
  
#  prdf <- prdf %>% tidyr::pivot_longer( cols = -date, names_to="s", values_to = "value",  values_drop_na = TRUE )
  
  # bind history and prediction
  # res <- dt %>% rename( 'value' = c ) %>%
  #   mutate( 's' = c ) %>%
  #   bind_rows( prdf ) %>%
  #   mutate( 'location' = l )
  res <- prdf %>% mutate( 'location' = l )
}
# Forecast daily supply level of doses
tmp <- lapply( NEstates, fcastfn, 'daily_available_avg' )
f1 <- bind_rows( tmp )

# Forecast daily vaccinations
tmp <- lapply( NEstates, fcastfn, 'daily_vaccinations' )
f2 <- bind_rows( tmp )

fcast <- bind_cols( f1, f2 %>% select(-date,-location) )
latest_fcast_date <- max(fcast$date)

# bind history and prediction
dcap_s <- dcap %>% select( date, location, daily_vaccinations,   daily_available )
fcast_s <- fcast %>% select(date,location,daily_vaccinations_fit,daily_available_avg_fit)
colnames(fcast_s) <- colnames(dcap_s)
dfw <- bind_rows( dcap_s, fcast_s )

dp <- dfw %>% tidyr::pivot_longer( cols = c('daily_vaccinations','daily_available')
                       , names_to="s" 
                       , values_to = "value",  values_drop_na = TRUE )
ggplot( dp, aes(x = date, y=value, color=s) ) +
   facet_wrap('~ location', nrow=2, scale='free_y' ) +
   geom_line() + 
  geom_vline(xintercept=latest_history_date, linetype="dashed", 
             color = "gray") +  
  theme(axis.title.x = element_blank()) +
   ylab('Total Number of Doses') +
   scale_y_continuous(label = scales::unit_format(unit = "K", scale = 1e-3, sep = "")
                      , expand = c(0, 0), limits = c(0, NA))
ggplot( dfw, aes(x = date, y=daily_vaccinations) ) +
  facet_wrap('~ location', nrow=2, scale='free_y' ) +
  geom_line() + 
  geom_vline(xintercept=latest_history_date, linetype="dashed", 
             color = "gray") +  
  theme(axis.title.x = element_blank()) +
  ylab('Daily Vaccinations') +
  scale_y_continuous(label = scales::unit_format(unit = "K", scale = 1e-3, sep = "")
                     , expand = c(0, 0), limits = c(0, NA))

## MAXIMUM CAPACITY
# calculate maximum capacity to administer doses per day (assumed constant)
fname <- '/Users/aligo/Downloads/tmp/vaccine data MOCK.xlsx'
sites <- read.xlsx( fname, sheet = 1, detectDates=TRUE )
sitecap <- read.xlsx( fname, sheet = 2, detectDates=TRUE )

sc <- left_join(sites, sitecap, by=c('date','location','type')) %>%
  group_by(date, location) %>% summarise( cap = sum( Ni * Ci ), .groups='drop_last' )

#dfw <- dfw %>% mutate( cap = NA )
for ( state in NEstates )
  dfw$cap[dfw$location==state #& dfw$date>latest_history_date-5
          ] <- sc$cap[sc$location==state]

colors <- c('daily_available','daily_vaccinations','cap')
dp <- dfw %>%
#  mutate( supply_daily = zoo::rollmean(supply_daily, k=7, fill=0, align="right") ) %>% 
  tidyr::pivot_longer( cols = all_of(colors)
                       , names_to="s" 
                       , values_to = "value",  values_drop_na = TRUE )
cnames <- c('Supply level','Doses administered','Max vaccination capacity (FAKE)')
dp <- dp %>% mutate( n = NA )
dp$n[dp$s %in% colors] <- cnames[match(dp$s,colors)]
ggplot( dp, aes(x = date, y=value, color=n) ) +
  facet_wrap('~ location', nrow=2, scale='free_y' ) +
  geom_line() +
  geom_vline(xintercept=latest_history_date, linetype="dashed", 
             color = "gray") +  
  theme(axis.title.x = element_blank()) +
  ylab('Doses per day') +
  scale_y_continuous(label = scales::unit_format(unit = "K", scale = 1e-3, sep = ""))

# WEEKLY
tmp <- dfw %>% mutate( week = format(date, '%Y.%W') )
wcap <- tmp %>% group_by(location, week) %>%
        summarise( date = max(date), weekly_available=min(daily_available, na.rm=TRUE)
                   , weekly_vaccinations=mean(daily_vaccinations, na.rm=TRUE)*7
                   , weekly_cap=mean(cap, na.rm=TRUE)*7, .groups='drop_last' )
wcolors <- c('weekly_available','weekly_vaccinations','weekly_cap')
cnames <- c('Min supply level in the week','Doses administered','Max vaccination capacity')
dp <- wcap %>% select(c('date', 'location', wcolors)) %>%
  #  mutate( supply_daily = zoo::rollmean(supply_daily, k=7, fill=0, align="right") ) %>% 
  tidyr::pivot_longer( cols = all_of(wcolors)
                       , names_to="s" 
                       , values_to = "value",  values_drop_na = TRUE )
dp <- dp %>% mutate( n = NA )
dp$n[dp$s %in% wcolors] <- cnames[match(dp$s,wcolors)]
ggplot( dp, aes(x=date, y=value, color=n) ) +
  facet_wrap('~ location', nrow=2, scale='free_y' ) +
  geom_line() +
  geom_vline(xintercept=latest_history_date, linetype="dashed", 
               color = "gray") +  # , size=1.5
  theme(axis.title.x = element_blank()) +
  scale_x_date(date_labels = '%b%e' ) +
  ylab('Doses per week') +
  scale_y_continuous(label = scales::unit_format(unit = "K", scale = 1e-3, sep = "")
                     , expand = c(0, 0), limits = c(0, NA))

### Calculate totals per state for the next week or two ###
comp <- function( d ){
  # This function calculates availability and required doses for the next d days
  
  # current stockpile: daily_available = total_distributed*(1-waste_rate) - total_vaccinations, all at latest_history_date
  # Number of people who current need a 2nd dose: demand2nd = people_vaccinated - people_fully_vaccinated, all at latest_history_date
  # assuming everyone in demand2nd will get the 2nd dose within 24 days (average between Moderna and Pfizer)
  # then 7/24 of them will get the shot within one week
  stock <- dcap %>% filter( date == latest_history_date ) %>%
    mutate( demand2nd = ( people_vaccinated - people_fully_vaccinated ) * d/t1st2nd ) %>%
    select( location, daily_available, demand2nd ) 

  # Number of people who will get 1st dose next week: demand1st1wk = sum[daily_vaccinations(next d days)] - demand2nd1wk
  dvac <- dfw %>% filter( between( date, latest_history_date+1, latest_history_date+d ) ) %>%
    group_by( location ) %>%
    summarise( dvac = sum(daily_vaccinations), .groups='drop_last' )
  stock <- left_join(stock, dvac, by='location') %>%
    mutate( demand1st = dvac - demand2nd )
  stock[stock < 0] <- 0
  
  # Number of doses that will be distributed next week = total_distributed(1wk ahead) - total_distributed(current)
  # = daily_available(1wk ahead) + total_vaccinations(1wk ahead) - daily_available(current) - total_vaccinations(current)
  # = daily_available(1wk ahead) - daily_available(current) + sum[daily_vaccinations(next 7 days)]
  # daily_available(1wk ahead)
  dav <- dfw %>% filter( date==latest_history_date+d ) %>% select(location,daily_available) %>% rename( dav=daily_available ) 
  stock <- left_join(stock, dav, by='location') %>%
    mutate( distrib = dav - daily_available + dvac )

  dp <- stock %>% select( -dvac,-dav ) %>%
    tidyr::pivot_longer( cols = -location, names_to="variable" ) %>%
    mutate( cat = 'Available')
  
  # which stack each total shows in
  dp[grepl('^demand',dp$variable),'cat'] <- 'Needed'
  
  # code to choose colors to use
  # hex_codes <- scales::dichromat_pal("BluetoOrange.10")(10)   # Identify hex codes
  # dichromat_pal("BluetoOrange.10")(5)
  # dichromat_pal("DarkRedtoBlue.12")(12)
  # scales::show_col(hex_codes) 
  
  # legend (colors)
  # legend must be sorted in the order they should appear in the stack
  bars <- c('addl forecasted\nstockpile','current\nstockpile','2nd dose\nforecast','1st dose\nforecast')
  leg <- c(bars[2],bars[1],bars[4],bars[3])
  colors<- c('#3399FF','#66CCFF', '#FF9933', '#FF5500')
  dp[dp$variable=='daily_available','variable'] <- leg[1]
  dp[dp$variable=='distrib','variable'] <- leg[2]
  dp[dp$variable=='demand1st','variable'] <- leg[3]
  dp[dp$variable=='demand2nd','variable'] <- leg[4]
  
  print( dp )
  ggplot(dp, aes(x=cat, y=value, fill=factor(variable, levels=bars))) + 
    geom_bar(stat = 'identity', position = 'stack') + 
    facet_wrap('~ location', nrow=2, scale='free_y' ) +
    #  scale_fill_discrete(breaks=leg) +
    scale_fill_manual(values=colors, breaks=leg) +
    theme(axis.title.x = element_blank()) +
    ylab('Number of doses') +
    scale_y_continuous(label = scales::unit_format(unit = "K", scale = 1e-3, sep = "")) + 
    ggtitle( paste0(d, '-Day Projection of Doses Available and Needed')) + theme(plot.title = element_text(hjust = 0.5) )
}
comp( 7 )
comp( 14 )

# SAVE for Shiny App
save(dfw,latest_history_date,sites,sitecap,NEstates, file='/Users/aligo/git-repos/FEMA/vaccinations/app.RData')
