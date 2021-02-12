library(dplyr)
library(zoo)
library(ggplot2)
library(openxlsx)

theme_set( theme_bw() + theme( legend.position="bottom" ) +
             theme( legend.title=element_blank() ) +
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
#  sm <- HoltWinters( as.ts(zz[-(1:(nper-1))]), gamma=FALSE )  # , alpha=0.3, gamma=FALSE )
  sm <- HoltWinters( as.ts(zz[-(1:(nper-1))]), gamma=FALSE ) # 
  print( paste('location', l, 'alpha', sm$alpha, 'beta', sm$beta, 'level', sm$coefficients['a'], 'trend', sm$coefficients['b']) )
  pr <- predict(sm, 14, prediction.interval=TRUE, level = 0.95)
#  plot(sm, pr)
  dates <- seq(max(dt$date)+1, by = "day", length.out = 14)
  prdf <- data.frame( dates, pr ) 
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

# tmp <- HoltWinters( as.ts(zz), alpha=0.5, beta=FALSE, gamma=FALSE )

# calculate maximum capacity to administer doses per day (assumed constant)
fname <- '/Users/aligo/Downloads/tmp/vaccine data MOCK.xlsx'
sites <- read.xlsx( fname, sheet = 1, detectDates=TRUE )
sitecap <- read.xlsx( fname, sheet = 2, detectDates=TRUE )

sc <- left_join(sites, sitecap, by=c('date','location','type')) %>%
  group_by(date, location) %>% summarise( cap = sum( Ni * Ci ), .groups='drop_last' )

dfw <- dfw %>% mutate( cap = NA )
for ( state in NEstates )
  dfw$cap[dfw$location==state & dfw$date>latest_history_date-5] <- sc$cap[sc$location==state]

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
cnames <- c('Min supply level in the week','Doses administered','Max vaccination capacity (FAKE)')
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
# current stockpile: daily_available = total_distributed*(1-waste_rate) - total_vaccinations, all at latest_history_date
# Number of people who current need a 2nd dose: demand2nd = people_vaccinated - people_fully_vaccinated, all at latest_history_date
# assuming everyone in demand2nd will get the 2nd dose within 24 days (average between Moderna and Pfizer)
# then 7/24 of them will get the shot within one week
stock <- dcap %>% filter( date == latest_history_date ) %>%
  mutate( demand2nd1wk = ( people_vaccinated - people_fully_vaccinated ) * 7/t1st2nd
        , demand2nd2wk = ( people_vaccinated - people_fully_vaccinated ) * 14/t1st2nd ) %>%
  select( location, daily_available, demand2nd1wk, demand2nd2wk ) 

# Number of people who will get 1st dose next week: demand1st1wk = sum[daily_vaccinations(next 7 days)] - demand2nd1wk
dvac1wk <- dfw %>% filter( between( date, latest_history_date+1, latest_history_date+7 ) ) %>%
  group_by( location ) %>%
  summarise( dvac1wk = sum(daily_vaccinations), .groups='drop_last' )
dvac2wk <- dfw %>% filter( between( date, latest_history_date+1, latest_history_date+14 ) ) %>%
  group_by( location ) %>%
  summarise( dvac2wk = sum(daily_vaccinations), .groups='drop_last' )

stock <- left_join(stock, dvac1wk, by='location') %>%
          mutate( demand1st1wk = dvac1wk - demand2nd1wk )
stock <- left_join(stock, dvac2wk, by='location') %>%
          mutate( demand1st2wk = dvac2wk - demand2nd2wk )

dp <- stock %>% select( -dvac1wk,-dvac2wk ) %>%
  tidyr::pivot_longer( cols = -location, names_to="variable" ) %>%
  mutate( cat = 'currently\navailable')

dp[dp$variable=='demand1st1wk' | dp$variable=='demand2nd1wk',]$cat <- "needed\nin 1 week"
dp[dp$variable=='demand1st2wk' | dp$variable=='demand2nd2wk','cat']$cat <- "needed\nin 2 weeks"

leg <- c('All doses','1st dose','2nd dose')
dp[dp$variable=='daily_available','variable'] <- leg[1]
dp[grepl('demand1st[1-2]wk',dp$variable),'variable'] <- leg[2]
dp[grepl('demand2nd[1-2]wk',dp$variable),'variable'] <- leg[3]

ggplot(dp, aes(x = cat, y = value, fill = variable)) + 
  geom_bar(stat = 'identity', position = 'stack') + 
  facet_wrap('~ location', nrow=2, scale='free_y' ) +
  scale_fill_discrete(breaks=leg) +
  theme(axis.title.x = element_blank()) +
  ylab('Number of doses') +
  scale_y_continuous(label = scales::unit_format(unit = "K", scale = 1e-3, sep = ""))
  
  
save(wcap,latest_history_date,sites,sitecap, file='/Users/aligo/git-repos/FEMA/vaccinations/app.RData')
