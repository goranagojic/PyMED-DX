import json
import os

from pathlib import Path

# Get the absolute path to the directory of the current script
localization_dir = Path(__file__).resolve().parent

with open(os.path.join(localization_dir, "type1_localization.json"), "r") as locale_file:
    type1_locale_data = json.load(locale_file)

with open(os.path.join(localization_dir, "type2_localization.json"), 'r') as locale_file:
    type2_locale_data = json.load(locale_file)

locale_data = None

def update_locale_data(qtype):
    global locale_data
    if qtype == 1:
        locale_data = type1_locale_data
    elif qtype == 2:
        locale_data = type2_locale_data
    else:
        locale_data = None
        
def get_locale_data():
    return locale_data