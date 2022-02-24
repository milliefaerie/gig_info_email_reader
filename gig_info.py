import os
import re
import pandas as pd
from pprint import pprint
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil.parser import parse
from collections import defaultdict
import urllib
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from time import sleep

# import requests
# from bs4 import BeautifulSoup as bs
# from random import randint
# import re
# from datetime import date
# from datetime import datetime
# from email.mime.text import MIMEText
# import base64
# import pickle
# import os.path
# from googleapiclient.discovery import build
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.auth.transport.requests import Request

def read_gig_info_email(gig_info_filename):
  gig_info_dir = "/home/erindb/Downloads/"
  gig_info_path = os.path.join(gig_info_dir, gig_info_filename)
  with open(gig_info_path) as f:
    gig_info_email_string = f.read()
    email_regex = r"Note\:((?:.*\n*)*)"
    gig_info_email_content = re.findall(email_regex, gig_info_email_string)[0]
    return gig_info_email_content

def make_tag_regex(tag_list):
  return re.compile("</? *(" + "|".join(tag_list) + ")[^>]*/?>")

def clean_gig_email(email_content):
  tags_to_remove = ["a", "b", "font"]
  tags_to_replace = ["br", "tr", "td", "ul", "li", "table", "pre"]
  tags_to_remove_regex = make_tag_regex(tags_to_remove)
  tags_to_replace_regex = make_tag_regex(tags_to_replace)
  clean_email_content = email_content
  clean_email_content = re.sub(tags_to_remove_regex, "", clean_email_content)
  clean_email_content = re.sub(tags_to_replace_regex, "\n", clean_email_content)
  clean_email_content = re.sub("\n+", "\n", clean_email_content)
  return clean_email_content

def separate_gigs(gig_info_email_content):
  gig_email_intro = "-+\nHi Millie.*\n"
  gig_separator = "-----{--@ -----{--@ -----{--@ -----{--@ -----{--@"
  gigs_string = re.sub(gig_email_intro, "", gig_info_email_content)
  gigs = re.split(gig_separator, gigs_string)[:-1]
  return gigs

def find_info(label, gig_string, end_string = None):
  if end_string:
    regex = label + ": *((?:(?:.*)\n)*)" + end_string
  else:
    regex = label + ": *(.*)"
  m = re.search(regex, gig_string)
  if m:
    return m.groups()[0].strip()
  else:
    return None

def parse_gigs(gig_info_email_content):
  gig_strings = separate_gigs(gig_info_email_content)
  gigs = []
  for gig_string in gig_strings:
    gig = {
      "child_name": find_info("Birth Day Child Name", gig_string),
      "child_age": find_info("Birth Day Child Age", gig_string),
      "character": find_info("Character", gig_string),
      "number_of_kids": find_info("Number of Children", gig_string),
      "dow": find_info("Day of Week", gig_string),
      "age_range": find_info("Ages of Children", gig_string),
      "parent_name": re.sub("%.*", "", find_info("Contact Parent", gig_string)).strip(),
      "home_phone": find_info("Home", gig_string),
      "cell_phone": find_info("Cell", gig_string),
      "work_phone": find_info("Work", gig_string)
    }
    activites_string = find_info(
      "Activity Plan",
      gig_string,
      "Performer told to collect"
    )
    location = find_info("Address of party and X Streets", gig_string)
    location = location.replace(" in ", ", ")
    location = re.sub("^[^0-9]*([0-9])", "\\1", location)
    gig["location"] = location
    gig["activites"] = activites_string.strip().split("\n")
    gig_date_string = find_info("Date of Event", gig_string)
    gig["gig_date"] = date.fromisoformat(gig_date_string)
    gig_time_string = find_info("Exact Time", gig_string)
    gig_times = gig_time_string.split("-")
    gig["start_time"] = parse(gig_date_string + " " + gig_times[0])
    gig["end_time"] = parse(gig_date_string + " " + gig_times[1])
    gig["text"] = gig_string.strip()
    gigs.append(gig)
  return gigs

def read_gig_info(gig_info_filename):
  raw_gig_info_email_content = read_gig_info_email(gig_info_filename)
  gig_info_email_content = clean_gig_email(raw_gig_info_email_content)
  gigs = parse_gigs(gig_info_email_content)
  return gigs

def create_gig_event(gig):
  """
  Enter your preferred headers. Only Subject and Start Date are required.
  [x] Subject (event name)
  [x] Start Date (format: 12/01/2017)
  [x] Start Time (format: 9:30 AM)
  [x] End Date (format: 9:30 AM)
  [x] End Time (format: 9:30 AM)
  [x] All Day Event (enter True or False)
  [x] Description
  [x] Location
  Private (enter True or False)
  """
  character = gig["character"]
  child_name = gig["child_name"]
  child_age = gig["child_age"]
  gig_date = gig["gig_date"]
  start_time = gig["start_time"]
  end_time = gig["end_time"]
  confirmation_call_script = "Confirmation Call:\n\n\n\n\n"
  full_description = confirmation_call_script + gig["text"]
  subject = f"Happily {character} Party {child_name} {child_age}"
  subject = re.sub(" +", " ", subject)
  gig_event = {
    "Subject": subject,
    "Start Date": f"{gig_date:%m/%d/%Y}",
    "End Date": f"{gig_date:%m/%d/%Y}",
    "Start Time": f"{start_time:%I:%M %p}",
    "End Time": f"{end_time:%I:%M %p}",
    "All Day Event": False,
    "Description": full_description,
    "Location": gig["location"]
  }
  return gig_event

def create_load_car_events_dataframe(gig_event_data):
  load_car = gig_event_data.copy()[["Start Date", "Start Time", "End Date", "End Time", "All Day Event"]]
  load_car["Start Time"] = load_car["End Time"]
  start_time = [parse(x) for x in load_car["End Date"] + " " + load_car["End Time"]]
  end_time = [x + timedelta(minutes = 15) for x in start_time]
  load_car["End Time"] = [f"{t:%I:%M %p}" for t in end_time]
  load_car["Subject"] = "Load Car"
  return load_car

def create_arrive_events_dataframe(gig_event_data):
  arrive = gig_event_data.copy()[["Start Date", "Start Time", "End Date", "End Time", "All Day Event"]]
  arrive["End Time"] = arrive["Start Time"]
  end_time = [parse(x) for x in arrive["Start Date"] + " " + arrive["Start Time"]]
  start_time = [x - timedelta(minutes = 30) for x in end_time]
  arrive["Start Time"] = [f"{t:%I:%M %p}" for t in start_time]
  arrive["Subject"] = "Arrive, Unload Car, Get Into Costume"
  return arrive

def create_gig_events_dataframe(gigs):
  gig_events = [create_gig_event(gig) for gig in gigs]
  gig_event_data = pd.DataFrame(gig_events)
  return gig_event_data

def create_google_calendar_dataframe(gigs):
  gig_event_data = create_gig_events_dataframe(gigs)
  load_car_data = create_load_car_events_dataframe(gig_event_data)
  arrive_data = create_arrive_events_dataframe(gig_event_data)
  return pd.concat([gig_event_data, load_car_data, arrive_data])

def create_google_contacts_dataframe(gigs):
  contacts = []
  for gig in gigs:
    parent_name = gig["parent_name"]
    character = gig["character"]
    child_name = gig["child_name"]
    child_age = gig["child_age"]
    dow = gig["dow"]
    start_time = gig["start_time"]
    contact_details = f"Faerie {character} {child_name} {child_age}"
    contact_details = re.sub(" +", " ", contact_details)
    contact_data = {
      "Given Name": parent_name,
      "Additional Name": contact_details,
      "Family Name": f"{dow} {start_time:%y/%m/%d %H:%M}"
    }
    if gig["cell_phone"]:
      contact_data["Phone 1 - Type"] = "Mobile"
      contact_data["Phone 1 - Value"] = gig["cell_phone"]
    if gig["work_phone"]:
      contact_data["Phone 1 - Type"] = "Work"
      contact_data["Phone 1 - Value"] = gig["work_phone"]
    if gig["home_phone"]:
      contact_data["Phone 1 - Type"] = "Home"
      contact_data["Phone 1 - Value"] = gig["home_phone"]
    contacts.append(contact_data)
  return pd.DataFrame(contacts)

def compose_text(gig, today_dow):
  if gig["child_name"] != "":
    the_party = f"{gig['child_name']}'s party"
  else:
    the_party = f"the party"
  if gig["parent_name"] != "":
    greeting = f"Hi, {gig['parent_name']}!"
  else:
    greeting = "Hi!"
  # Thursday
  a_good_time = "a good time"
  when = f"on {gig['dow']}"
  if today_dow == 3:
    if gig["dow"] == "Saturday" or gig["dow"] == "Sunday":
      a_good_time = "a good time today or tomorrow"
  # Friday
  elif today_dow == 4:
    if gig["dow"] == "Saturday":
      a_good_time = "a good time today"
      when = "tomorrow"
    elif gig["dow"] == "Sunday":
      a_good_time = "a good time today or tomorrow"
  return f"{greeting} This is Millie from Happily Ever Laughter! When is {a_good_time} for me to give you a call so we can check in about details of {the_party} {when}? 💖✨"

def print_instructions(gigs):
  n = len(gigs)
  print()
  print("################# Step 1: Load Contacts and Send Text Messages #################")
  print()
  print("* Go to https://contacts.google.com/u/1/ and click 'Import'")
  print(f"* Go to https://voice.google.com/u/1/messages in {n} separate tab(s)")
  print()
  for gig in gigs:
    print(f"  * text {gig['parent_name']}")
    today_dow = datetime.today().weekday()
    text = compose_text(gig, today_dow)
    print(text)
    print()

  print()
  print("################# Step 2: Load Calendar Events #################")
  print()
  print("* Go to https://calendar.google.com/calendar/u/0/r/settings/export")
  print()

  print("################# Step 3: Look Up Travel Time #################")
  add_travel_time = input("Do you want to manually add travel time calendar events? (Y/n) ")
  print()
  return add_travel_time.lower() == "y"

def arrange_by_day(all_gigs):
  days = defaultdict(lambda: [])
  for gig in all_gigs:
    days[gig["dow"]].append(gig)
  return days

def get_distances(all_gigs):
  """
  given a particular arrival and/or departure day and time, find the number
  of minutes (mean and max) and the number of miles between locations
  """
  days = arrange_by_day(all_gigs)
  maps_url = "https://www.google.com/maps/dir/"
  home = "3644+Rutledge+Common,+Fremont,+CA"
  driver = webdriver.Chrome()
  for day, gigs in days.items():
    # get from home to the first event
    first_location = gigs[0]["location"]
    first_location_url = maps_url + home + "/" + urllib.parse.quote(first_location)
    driver.get(first_location_url)
    sleep(2)
    sleep(60)

    # get in between events
    for i in range(len(gigs)-1):
      gig_from = gigs[i]["location"]
      gig_to = gigs[i+1]["location"]
      driver.get(maps_url + urllib.parse.quote(gig_from) + "/" + urllib.parse.quote(gig_to))
      sleep(2)
      sleep(60)

    # get from the last event to home
    last_location = gigs[-1]["location"]
    last_location_url = maps_url + urllib.parse.quote(last_location) + "/" + home
    driver.get(last_location_url)
    sleep(2)
    sleep(60)
    # # click on the div that says "Leave now"
    # # click on the div that says "Arrive by"
    # # use the input with name="transit-time" to choose the arrival time
    # # use the date picker to choose the date
    # # read the travel time and miles for the top route

  # html = driver.page_source
  driver.close()
  # soup = bs(html, 'html.parser')

def get_costume_packing_list(character):
  purple_kit = set(
    "purple fleece shirt",
    "purple tights",
    "purple bows (x2)",
    "purple belt",
    "purple fan"
  )
  black_kit = set(
    "black belt",
    "black bows (x2)",
    "black fan"
  )
  blue_kit = set(
    "blue tights",
    "blue fleece shirt"
  )
  faerie = set(
    "black flats",
    "white boots",
    "blue petticoat",
    "faerie topskirt",
    "teal tank top",
    "purple corset",
    "faerie shrug",
    "blue wings",
    "blue mask",
    "faerie headdress"
  ).union(purple_kit)
  packings_lists = {
    "faerie": faerie,
    "pixie witch": faerie.union(set(
      "witch hat",
      "pirate tights"
    )),
    "adventure faerie": set(
      "pirate boots",
      "pirate tights",
      "blue petticoat",
      "faerie topskirt",
      "white chemise",
      "purple corset",
      "pirate belt",
      "blue wings",
      "blue mask",
      "pirate scarf",
      "pirate hat",
      "faerie flower clipped to hat"
    ),
    "pirate": set(
      "pirate boots",
      "pirate tights",
      "pirate skirt",
      "white chemise",
      "black corset",
      "pirate belt",
      "gold mask",
      "pirate scarf",
      "pirate hat",
      "red feather clipped to hat",
      "juggling knives"
    ).union(black_kit),
    "circus girl": set(
      "black flats",
      "white boots",
      "white petticoat",
      "circus skirt",
      "yellow tank top",
      "red corset",
      "circus shrug",
      "gold mask",
      "circus headdress"
    ).union(blue_kit).union(black_kit).union(white_kit)
  }

def get_one_day_packing_list(gigs):
  character = gigs["character"]
  activites = gigs["activites"]
  packing_list = set(
    "kn95",
    "fashion tape",
    "glasses",
    "glasses case",
    "contacts",
    "contacts case",
    "contacts solution",
    "lens cleaner cloth",
    "hand sanitizer",
    "water bottle",
    "granola bar",
    "purple fleece pants",
    "cape",
    "pink 3d printed mask ear protector",
    "speaker",
    "microphone",
    "clock (check time)",
    "millie necklace",
    "rain boots",
    "umbrella",
    "wing belt (wig headband)"
  )
  packing_list = packing_list.union(get_costume_packing_list(character))
  for activity in activites:
    packing_list = packing_list.union(get_activity_packing_list(activity))
  return packing_list

def get_daily_packing_lists(all_gigs):
  days = arrange_by_day(all_gigs)
  packing_lists = {}
  for day, gigs in all_gigs:
    packing_lists[day] = get_one_day_packing_list(gigs)
  return packing_lists

def main():
  gig_info_filename = "Gig Info for Feb 24-March 4th!.eml"
  gigs = read_gig_info(gig_info_filename)
  gig_event_data = create_google_calendar_dataframe(gigs)
  gig_event_data.to_csv("events.csv")
  contacts_data = create_google_contacts_dataframe(gigs)
  contacts_data.to_csv("contacts.csv", index = False)
  add_travel_time = print_instructions(gigs)
  if add_travel_time:
    get_distances(gigs)
  #packing_lists = get_daily_packing_lists(gigs)

main()

"""
make google calendar events csv
include:
 - [x] location
 - [x] notes
 - [ ] confirmation script
 - [ ] followup text template
confirmation script:
- confirm day, time, character, address (nearby what?)
- guests arrive early? (cofirm activity order)
- magic show is on wheels
- birthday kid's name & age
- siblings?
- ages of other kids and how many
add transition times to calendar
"""

# [ ] make daily packing checklist in google keep

# [ ] make weekly activity list & transition list

# [ ] make google contacts for parents and draft text to send them, with emojis

# [ ] update faerie login hours with distances