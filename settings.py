import os
import json
import logging

PROJECT_DIR = os.getcwd()
GUI_DIR = os.path.join(PROJECT_DIR, "gui")
PROJECT_NAME = "DPM"

config = json.load(open(os.path.join(PROJECT_DIR, "config.json"), "r", encoding="utf-8"))

logging.basicConfig(filename=config["logfile"], level=logging.DEBUG)

# ToDo add icons mapping for gui
