#!/usr/bin/env python

# California Fire Study: Fire Data Scraper
# date: 11/25/2018
# author: apsam
# description: This script scrapes data from Cal Fire's current incidents pages.
#	Data is read from all incident pages, some cleaning is performed, latitude
#	and longitude data is obtained from the entry's county field. All parsed
#	data is then saved to a csv file. 

import requests as req
from bs4 import BeautifulSoup
from datetime import datetime
from geopy.geocoders import Nominatim
import re
import csv

base_url = "https://www.fire.ca.gov"
url_path = "current_incidents/?page="
site_template = "{}/{}".format(base_url, url_path)

# Parse the site to get final page number
page0 = req.get(site_template + "1")
soup0 = BeautifulSoup(page0.content, 'html.parser')
total_pages = soup0.find('li', class_="PagedList-skipToLast")
ending_url = str(total_pages.find('a', href=True).attrs['href'])
last_page = int(re.findall(r'\d+', ending_url)[0])

all_fires = []
print("Source: {}\n".format(base_url))
for page_num in range(1, last_page + 1):
	# Each page contains 5 incident tables, extract values from each
	incidents = []
	single_fire = []

	dest_site = site_template + str(page_num)
	print("Scraping pages...\t\t[{}/{}]".format(page_num, last_page), end='\r')
	page = req.get(dest_site)
	soup = BeautifulSoup(page.content, 'html.parser')
	incidents = soup.find_all('table', class_='incident_table')
	incidents = incidents[1:]

	"""
	Dirty data: (all in one line)
	-----------
	Market Fire:  more info...,
	"Updated: October 30, 2018 10:18  am",
	Tulare County  ,
	"Road 208 and Avenue 380, 5 miles north of Woodlake  ",
	120 acres -  100% contained  
	"""
	for entry in incidents:
		values = entry.find_all("td")

		name = values[0].get_text()		# Fire Name
		single_fire.append(name)

		time = values[1].get_text()		# Value Updated Time
		single_fire.append(time)

		county = values[3].get_text()	# County
		single_fire.append(county)

		location = values[5].get_text()	# Location
		single_fire.append(location)

		acres_containment = values[7].get_text()	# Acres/Containment
		single_fire.append(acres_containment)

		all_fires.append(single_fire)
		single_fire = []

# Done fetching entries from web page, do some cleaning
"""
Before:
['Name', 'Time', 'County', 'Location', 'Acres/Containment'])
After:
['Name', 'Time', 'County', 'Location', 'Acres', 'Containment', 'Lat', 'Long'])
"""
print("\n")
geolocator = Nominatim(user_agent="fire_scraper")
total_fire_entries = len(all_fires)
for index, fire_entry in enumerate(all_fires):
	fire_entry[0] = str(re.findall(r'^\s*(.*):', fire_entry[0])[0])
	time_str = str(re.findall(r'\D+:\s(.*[^"][^\s])', fire_entry[1])[0])
	# Adjust time format
	time_obj = datetime.strptime(time_str, '%B %d, %Y %I:%M %p')
	fire_entry[1] = time_obj.strftime('%m/%d/%Y %H:%M')
	try:
		county = str(re.findall(r'.*[^\s]{2}', fire_entry[2])[0])
		fire_entry[2] = county.replace(u'\xa0', '').split(',')[0]
	except IndexError:
		fire_entry[2] = " "
	try:
		fire_entry[3] = str(re.findall(r'.*[^\s]{2}', fire_entry[3])[0])
	except IndexError:
		fire_entry[3] = " "
	try:
		acres = str(re.findall(r'^(.*?)\sacre', fire_entry[4])[0])
	except IndexError:
		acres = " "
	try:
		containment = str(re.findall(r'-\s+(.*)%', fire_entry[4])[0])
	except IndexError:
		containment = " "
	fire_entry[4] = acres
	# Add the new column for containment percentage
	fire_entry.append(containment)
	# Add new columns for latitude and longitude
	location = geolocator.geocode(fire_entry[2])
	try:
		fire_entry.append(location.latitude)
	except AttributeError:
		fire_entry.append(0)
	try:
		fire_entry.append(location.longitude)
	except AttributeError:
		fire_entry.append(0)
	print("Cleaning entries...\t\t[{}/{}]".format(
		index + 1, total_fire_entries), end='\r')

print("\n")
total_fire_entries = len(all_fires)
# Append the cleaned data to the file
# Write all the fires for this page to the csv file
outputFireFile = 'fire-list-{}.csv'.format(
					datetime.now().strftime("%m-%d-%Y-%H:%M"))
print("Writing {} entries to: {}...".format(len(all_fires), outputFireFile))
f = csv.writer(open(outputFireFile, 'w'))
f.writerow(['Name', 'Time', 'County', 'Location', 'Acres', 'Containment'])
f.writerows(all_fires)
print("...Done")
