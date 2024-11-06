import json
import os

from pathlib import Path

# Get the absolute path to the directory of the current script
localization_dir = Path(__file__).resolve().parent

with open(os.path.join(localization_dir, "type1_localization.json"), "r") as locale:
    type1_locale_data = json.load(locale)

with open(os.path.join(localization_dir, "type2_localization.json"), 'r') as locale:
    type2_locale_data = json.load(locale)