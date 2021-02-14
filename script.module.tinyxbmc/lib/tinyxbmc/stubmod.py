'''
Created on Feb 13, 2021

@author: boogie
'''
import xbmcaddon
import os
import urlparse
import sys
from xml.dom import minidom

rootpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")


class Addon(xbmcaddon.Addon):
    def __init__(self, id=None):
        if id is None:
            url = urlparse.urlparse(sys.argv[0])
            if url.scheme.lower() in ["plugin", "script"]:
                id = url.netloc
        self.id = id
        if self.id:
            self.settingfile = os.path.join(rootpath, self.id, "resources", "settings.xml")

    def getSetting(self, id):
        xfile = minidom.parse(self.settingfile)
        for setting in xfile.getElementsByTagName("setting"):
            setid = setting.attributes.get("id")
            if setid and setid.value == id:
                return setting.attributes.get("default").value
                break

    def setSetting(self, id, value):
        xfile = minidom.parse(self.settingfile)
        for setting in xfile.getElementsByTagName("setting"):
            setid = setting.attributes.get("id")
            if setid and setid.value == id:
                setting.attributes.get("default").value = value
                break
        with open(self.settingfile, "w") as f:
            f.write(xfile.toxml())
