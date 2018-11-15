import os
import json
import datetime
import calendar
from connector import Connector
from models import BaseDPM, Application
from sync.functions import sync_separate_app
from delphitools import DelphiProject

path_to_config = "config.json"

def main():
	if os.path.exists("db.sqlite"):
		os.remove("db.sqlite")
	config = read_config()
	path_to_app = config["testApp"]
	app_name = config["testAppName"]
	d = datetime.datetime.now()
	la = datetime.datetime.fromtimestamp(
		calendar.timegm((datetime.date.today() - datetime.timedelta(days=30)).timetuple())
	)
	db = Connector()
	session = db.connect_to_dpm()
	data = {
		"path": path_to_app,
		"name": app_name,
		"last_sync": d,
		"last_update": la}
	print(data)
	test_app = Application(**data)
	session.add(test_app)
	session.flush()
	sync_separate_app(test_app, session)
	print(session.dirty)


def read_config():
	return json.load(open(path_to_config, "r", encoding="utf-8"))



if __name__ == "__main__":
	main()
