library(dplyr)

#tmp <- read.table("/Users/aligo/Downloads/zipcode_NAICS/CB1800ZBP.dat", header=TRUE, sep = "|", dec = "."
#                  , quote="\"", nrows=1e7 )

tmp2 <- read.table("/Users/aligo/Downloads/zipcode_NAICS/ZBP2018.dat", header=TRUE, sep = "|", dec = "."
                   , quote="\"", nrows=1e7 )

ct <- tmp2 %>% filter( ST == 09 ) # CT

# NAICS codes CT/SBA are interested at:
naics <- data.frame(  c('Retail trade', 44)
                    , c('Retail trade', 45)
                    , c('Transportation and warehousing', 48)
                    , c('Transportation and warehousing', 49)
                    , c('Administration and support services', 56)
                    , c('Educational services', 61)
                    , c('Healthcare and social assistance', 62)
                    , c('Arts, entertainment, and recreation', 71)
                    , c('Accommodation and food services', 72)
                    , c('Other services', 81)
                    )
naics <- data.frame(t(naics))
colnames(naics) <- c('name','code')
filternaics <- function(code){
  return( stringr::str_detect(ct$NAICS2017, paste0('^',code)) )
}
m <- logical(nrow(ct))
for (c in naics$code){
  m <- m | filternaics(c)
}
ct_f <- ct[m,] %>% filter( nchar(trimws(NAICS2017)) >= 6)
  
write.csv(ct_f
          , "/Users/aligo/Downloads/zipcode_NAICS/ct_zipcode_6naics.csv", row.names=FALSE)
