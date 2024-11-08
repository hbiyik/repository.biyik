'''
Created on Nov 8, 2024

@author: boogie
'''
from tinyxbmc import addon
import os

DEBUG = False
ADDON_NAME = "script.module.chromium"
ADDON_PATH = addon.get_addondir(ADDON_NAME)
DATA_PATH = os.path.join(ADDON_PATH, "data")
DOWNLOAD_PATH = os.path.join(ADDON_PATH, "downloads")
CHROMIUM_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
CMD_TIMEOUT = 3
