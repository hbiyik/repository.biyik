'''
Created on Feb 13, 2021

@author: boogie
'''
import xbmcaddon
import xbmc
import xbmcvfs
import os
import sys
import re
from lxml import etree
from six.moves.urllib import parse
import tempfile
import inspect

rootpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")


def isstub():
    return hasattr(xbmc, "__kodistubs__") and xbmc.__kodistubs__


def xbmclog(msg, *args, **kwargs):
    print(msg)


class Addon(xbmcaddon.Addon):
    def __init__(self, nid=None):
        self.rootpath = None
        self.settingfile = None
        if nid is None:
            url = parse.urlparse(sys.argv[0])
            if url.scheme.lower() in ["plugin", "script"]:
                nid = url.netloc
        self.id = nid
        if self.id:
            self.root = self.findroot()

    def findroot(self):
        found = False
        for stack in inspect.stack():
            if found:
                break
            parent = os.path.dirname(stack.filename)
            lookups = [self.id]
            for _ in range(10):
                rootpath = os.path.abspath(os.path.join(parent, *lookups))
                if os.path.exists(rootpath) and os.path.isdir(rootpath):
                    self.rootpath = rootpath
                    settingfile = os.path.join(self.rootpath, "resources", "settings.xml")
                    if os.path.exists(settingfile):
                        self.settingfile = settingfile
                    found = True
                    break
                lookups.insert(0, "..")

    def getAddonInfo(self, info):
        if info == "path" and self.rootpath:
            return self.rootpath

    def getSetting(self, variable):
        with open(self.settingfile) as f:
            parser = etree.XMLParser(recover=True, ns_clean=True)
            xfile = etree.parse(f, parser)
            for elem in xfile.findall(".//setting"):
                if elem.get("id") == variable and "default" in elem.attrib:
                    return elem.get("default")

    def setSetting(self, variable, value):
        newxml = None
        with open(self.settingfile) as f:
            parser = etree.XMLParser(recover=True, ns_clean=True)
            xfile = etree.parse(f, parser)
            for elem in xfile.findall(".//setting"):
                if elem.get("id") == variable and "default" in elem.attrib:
                    elem.attrib["default"] = value
                    newxml = xfile.tostring(self.settingfile, pretty_print=True)
        if newxml:
            with open(self.settingfile, "wb") as f:
                f.write(newxml)


def translatePath(path):
    isspecial = False
    path_return = path
    try:
        parsed = parse.urlparse(path)
        isspecial = parsed.scheme == "special"
    except Exception:
        pass
    if isspecial:
        if parsed.netloc == "userdata":
            path_return = os.path.join(tempfile.gettempdir(), "kodi_userdata")
            if len(parsed.path):
                path_return = os.path.join(path_return, *os.path.split(parsed.path[1:]))
    return path_return


if isstub():
    xbmcaddon.Addon = Addon
    xbmc.log = xbmclog
    xbmcvfs.translatePath = translatePath
