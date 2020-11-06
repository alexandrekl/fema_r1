library(dplyr)

tmp <- read.table("/Users/aligo/Downloads/CB1800ZBP.dat", header=TRUE, sep = "|", dec = "."
                  , quote="\"", nrows=1e7 )

tmp2 <- read.table("/Users/aligo/Downloads/ZBP2018.dat", header=TRUE, sep = "|", dec = "."
                   , quote="\"", nrows=1e7 )

ct <- tmp2 %>% filter( ST == 09 ) # CT

write.csv(ct, "/Users/aligo/Downloads/ct_zipcode_6naics.csv", row.names=FALSE)
