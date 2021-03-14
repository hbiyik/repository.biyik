'''
Created on Feb 13, 2021

@author: boogie
'''
import xbmcaddon
import os
import sys
from xml.dom import minidom
from six.moves.urllib import parse

rootpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")


class Addon(xbmcaddon.Addon):
    def __init__(self, nid=None):
        if nid is None:
            url = parse.urlparse(sys.argv[0])
            if url.scheme.lower() in ["plugin", "script"]:
                nid = url.netloc
        self.id = nid
        if self.id:
            self.settingfile = os.path.join(rootpath, self.id, "resources", "settings.xml")

    def getSetting(self, aid):
        xfile = minidom.parse(self.settingfile)
        for setting in xfile.getElementsByTagName("setting"):
            setid = setting.attributes.get("aid")
            if setid and setid.value == aid:
                return setting.attributes.get("default").value
                break

    def setSetting(self, aid, value):
        xfile = minidom.parse(self.settingfile)
        for setting in xfile.getElementsByTagName("setting"):
            setid = setting.attributes.get("aid")
            if setid and setid.value == aid:
                setting.attributes.get("default").value = value
                break
        with open(self.settingfile, "w") as f:
            f.write(xfile.toxml())
