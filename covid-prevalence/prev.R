library(tidyr)
library(ggplot2)

# county cumulative cases in wide format, USA facts
cumw <- read.csv("https://usafactsstatic.blob.core.windows.net/public/data/covid-19/covid_confirmed_usafacts.csv")

# county population data from USA facts
pop <- read.csv("https://usafactsstatic.blob.core.windows.net/public/data/covid-19/covid_county_population_usafacts.csv")

# join
tmp1 <- pop %>% filter( countyFIPS > 0 ) %>% select(countyFIPS, population)
tmp2 <- cumw %>% filter( countyFIPS > 0 )
casesw <- left_join(tmp1, tmp2, by="countyFIPS")

# wide to long
cases <- casesw %>% 
  pivot_longer( -c(countyFIPS, population, County.Name, State, stateFIPS)
                , names_to="Date", names_prefix="X"
                , values_to="Cumul")
cases <- cases %>% mutate( Date = as.Date(Date, "%m.%d.%y")
                           , CountySt = paste0(County.Name, ", ", State)
                          ) %>%
              group_by(countyFIPS) %>% 
              mutate( New100k = (Cumul-lag(Cumul))/population*1e5
                      , Active14d100k = (Cumul-lag(Cumul,n=14))/population*1e5
                      ) %>% 
              mutate( ActiveRate = (Active14d100k-lag(Active14d100k))/
                                    as.numeric( as.Date(Date)-as.Date(lag(Date)) )
                       ) %>% 
              mutate( ActiveRateavg = rollmean(x=ActiveRate, 7, align="right", fill=NA) ) %>%
              ungroup()

mostdense <- c("New York County, NY", "Kings County, NY", "Bronx County, NY"
               , "San Francisco County, CA", "Cook County, IL", "Suffolk County, MA"
               , "Philadelphia County, PA", "Washington, DC", "St. Louis County, MO")
df <- cases %>% filter( CountySt %in% mostdense )

# "prevalence" - actually, number of cases that appeared in the last 14 days
ggplot( df, aes( x=Date, y=Active14d100k, colour=CountySt )) +
  scale_y_continuous(sec.axis = sec_axis(~. / 14, name = "New cases per 100k people, 14-day average")) +
  facet_wrap(~ CountySt, nrow=3) +
  geom_line() +
  ylab("14-day active cases per 100k people") +
  theme(legend.position="none") # removes legends

# derivative of "prevalence"
ggplot( df, aes( x=Date, y=ActiveRateavg, colour=CountySt )) +
  facet_wrap(~ CountySt, nrow=3) +
  geom_line() +
  ylab("Rate of change in 14-day active cases per 100k people") +
  theme(legend.position="none") # removes legends

ggplot( df, aes( x=Date, y=Active14d100k, colour=CountySt )) +
  geom_line()
