import json

_conf_data = json.load(open("config.json", "r", encoding="utf-8"))

def get_arms_list():
	return _conf_data.get("arms")

def get_main_dir():
	return _conf_data.get("mainDir")