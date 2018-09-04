import json
from os import listdir
from os.path import isdir, join

conf = open("config.json", "r", encoding="utf-8")

conf_data = json.load(conf)
arms = conf_data.get("arms")
