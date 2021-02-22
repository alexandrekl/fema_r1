import csv
import requests

##COVID Dashboard for Massachusetts
url = 'https://www.google.com/maps/d/u/0/viewer?mid=1z197EsKQBJ1jkUL9YjnLSRN30qFRnfqd&ll=42.25455184487974%2C-71.54994546486294&z=9'
   
##Get Website as pure HTML and split into data instances
respon = requests.get(url)
results = respon.text.split('iDbOGlSP2_Q')

##Process 178 data points
scrape = []
for item in range(3,180):
    location = {}
    location['latlon'] = results[item].split(",[")[1].split("]")[0]
    location['designation'] = results[item].split(",[")[2].split("\\\"")[1]
    location['name'] = results[item].split(",[")[3].split("\\\"")[1]
    scrape.append(location)

##Write out to CSV
keys = scrape[0].keys()
with open('MASS_sites_scraped.csv', 'w', newline='')  as output_file:
    dict_writer = csv.DictWriter(output_file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(scrape)