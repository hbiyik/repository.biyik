'''
Created on Jun 20, 2025

@author: boogie
'''
import json
import os

ISOPATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "resources", "iso")

countries_2letter = {}
countries_3letter = {}

languages_2letter = {}
languages_3letter = {}

for dbs, isos in (((countries_2letter, countries_3letter), ("iso3166-1", "iso3166-3")),
            ((languages_2letter, languages_3letter), ("iso639-3", "iso639-5"))):
    for iso in isos: 
        with open(os.path.join(ISOPATH, iso) + ".json") as f:
            js = json.load(f)
        for entry in js[list(js.keys())[0]]:
            key = entry.get("alpha_2")
            if key:
                dbs[0][key.lower()] = entry["name"].title()
            key = entry.get("alpha_3")
            if key:
                dbs[1][key.lower()] = entry["name"].title()
