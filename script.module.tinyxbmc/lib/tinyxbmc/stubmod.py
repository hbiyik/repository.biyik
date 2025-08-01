'''
Created on Feb 13, 2021

@author: boogie
'''
import xbmc


def isstub():
    return hasattr(xbmc, "__kodistubs__") and xbmc.__kodistubs__


if isstub():
    import xbmcvfs
    import os
    import sys
    from lxml import etree
    from six.moves.urllib import parse
    import tempfile
    import inspect
    import xbmcaddon
    from tinyxbmc import tools

    rootpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")

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
            rootpath = os.path.expanduser(f"~/.kodi/addons/{self.id}")
            if os.path.exists(rootpath) and os.path.isdir(rootpath):
                self.rootpath = rootpath
                settingfile = os.path.join(self.rootpath, "resources", "settings.xml")
                if os.path.exists(settingfile):
                    self.settingfile = settingfile

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
        return os.path.join(path_return, "")

    def executeJSONRPC(*args, **kwargs):
        return '{"result": {"addon": {}}}'

    tools.kodiversion = lambda: 19
    xbmc.executeJSONRPC = executeJSONRPC
    xbmcaddon.Addon = Addon
    xbmc.log = xbmclog
    xbmcvfs.translatePath = translatePath

    from tinyxbmc import mediaurl
    mediaurl.url.HASFFDR = False
    mediaurl.url.HASISA = False
    import aceengine
    aceengine.acestream.apiurl = lambda: "http://127.0.0.1:6878"
