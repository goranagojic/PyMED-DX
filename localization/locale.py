import json

with open("localization/type1_localization.json", 'r') as locale:
    type1_locale_data = json.load(locale)

with open("localization/type2_localization.json", 'r') as locale:
    type2_locale_data = json.load(locale)