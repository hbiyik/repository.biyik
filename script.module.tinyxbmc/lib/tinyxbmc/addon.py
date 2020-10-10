# -*- coding: utf-8 -*-
'''
    Author    : Huseyin BIYIK <husenbiyik at hotmail>
    Year      : 2016
    License   : GPL

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import xbmcaddon
import xbmc

import os
import traceback
import sys
import urlparse
import json

from distutils.version import LooseVersion

from tinyxbmc import tools

addon = None

if len(sys.argv):
    url = urlparse.urlparse(sys.argv[0])
    if url.scheme.lower() in ["plugin", "script"]:
        addon = url.netloc


def has_addon(aid):
    """
    Checks if the given __addon id is installed
    """
    return xbmc.getCondVisibility('System.HasAddon(%s)' % aid)


def get_addon(aid=None):
    """
    Returns the __addon instance gicen by __addon id, if id is not given and called by a script,
    tinyxbmc __addon is returned
    """
    if not aid:
        aid = addon
    a = xbmcaddon.Addon(aid)
    return a


def addon_details(aid):
    data = {
        "jsonrpc": "2.0",
        "method": "Addons.GetAddonDetails",
        "id": 1,
        "params": {"addonid": aid,
                   "properties": ["name",
                                  "version",
                                  "path",
                                  "dependencies",
                                  "enabled",
                                  "broken",
                                  ],
                   }
    }
    addons = json.loads(xbmc.executeJSONRPC(json.dumps(data)))
    if "error" in addons:
        return None
    return addons["result"]["addon"]


def toggle_addon(aid, enable=None):
    if enable is None:
        enable = "toggle"

    data = {"jsonrpc": "2.0",
            "method": "Addons.SetAddonEnabled",
            "params": {"addonid": aid,
                       "enabled": enable},
            "id": 1}
    toggle = json.loads(xbmc.executeJSONRPC(json.dumps(data)))
    if "error" in toggle:
        return False
    return True


def depend_addon(aid, *paths):
    """
    Adds directories of the addons dependencies to the system path for the given addonid
    """
    a = get_addon(aid)
    if a:
        bpath = a.getAddonInfo('path')
        path = xbmc.translatePath(bpath).decode("utf-8")
        if path not in sys.path:
            sys.path.append(path)
        axml = os.path.join(bpath, "addon.xml")
        if os.path.exists(axml):
            dxml = tools.readdom(axml)
        exts = dxml.getElementsByTagName("extension")
        if len(paths):
            ex_path = os.path.join(bpath, *paths)
            if ex_path not in sys.path:
                sys.path.append(ex_path)
        for ext in exts:
            if ext.getAttribute("point") == "xbmc.python.module":
                lib = ext.getAttribute("library")
                if lib:
                    ldir = os.path.join(bpath, lib)
                    if ldir not in sys.path:
                        sys.path.append(ldir)


def get_addondir(aid=None):
    """
    Returns the data directory for the __addon given
    """
    if not aid:
        aid = addon
    path = get_commondir()
    for p in ["addons", aid]:
        path = os.path.join(path, p)
        if not os.path.exists(path):
            os.makedirs(path)
    return os.path.abspath(path)


def get_commondir():
    """
    Returns the common data dir for tinyxbmc
    """
    a = get_addon("script.module.tinyxbmc")
    profile = a.getAddonInfo('profile')
    path = xbmc.translatePath(profile).decode("utf-8")
    if tools.isstub():
        path = os.path.join(addon, "profile_dir")
    if not os.path.exists(path):
        os.makedirs(path)
    return path


class kodisetting():
    def __init__(self, aid=None):
        self.e = "utf-8"
        self.a = get_addon(aid)

    @staticmethod
    def _get_file(aid, name):
        a = get_addon(aid)
        profile = a.getAddonInfo('profile')
        path = xbmc.translatePath(profile).decode("utf-8")
        return os.path.join(path, name)

    @staticmethod
    def ischanged(aid):
        f = kodisetting._get_file(aid, "settings.xml")
        if os.path.exists(f):
            cur_s = str(os.path.getsize(f))
        else:
            cur_s = "-1"
        f = kodisetting._get_file(aid, "settings.size")
        if os.path.exists(f):
            with open(f, "r") as sfile:
                pre_s = sfile.read()
        else:
            pre_s = "-1"
        if cur_s == pre_s:
            return False
        else:
            with open(f, "w") as sfile:
                sfile.write(cur_s)
            return True

    def getbool(self, variable):
        return bool(self.a.getSetting(variable) == 'true')

    def getstr(self, variable):
        return str(self.a.getSetting(variable).decode(self.e))

    def getint(self, variable):
        val = self.a.getSetting(variable)
        if isinstance(val, (int, float)):
            return int(val)
        elif isinstance(val, (str, unicode)) and val.isdigit():
            return int(val)
        else:
            return -1

    def getfloat(self, variable):
        return float(self.a.getSetting(variable))

    def set(self, key, value):
        if isinstance(value, bool):
            value = str(value).lower()
        elif not isinstance(value, (str, unicode)):
            value = str(value)
        return self.a.setSetting(key, value)


def local(sid, aid=None):
    a = get_addon(aid)
    if a:
        return a.getLocalizedString(sid).encode('utf-8')
    else:
        return xbmc.getLocalizedString(sid)


class blockingloop(object):
    def __init__(self, *args, **kwargs):
        self.wait = 0.1
        self.__new = LooseVersion(xbmc.__version__) >= LooseVersion("2.20.0")  # @UndefinedVariable
        self.__terminate = False
        self.init(*args, **kwargs)
        self.oninit()
        e = None
        if self.__new:
            self.__mon = xbmc.Monitor()
            while not self.isclosed():
                try:
                    self.onloop()
                except Exception, e:
                    traceback.print_exc()
                    break
                if self.__mon.waitForAbort(self.wait) or self.isclosed():
                    if not self.__terminate:
                        self.onclose()
                    break
            del self.__mon
        else:
            while True:
                try:
                    self.onloop()
                except Exception, e:
                    traceback.print_exc()
                    break
                if self.isclosed():
                    self.onclose()
                    break
                xbmc.sleep(int(self.wait * 1000))
        if e:
            print traceback.print_exc()
            raise(e)

    def init(self, *args, **kwargs):
        pass

    def oninit(self):
        pass

    def onloop(self):
        pass

    def onclose(self):
        pass

    def isclosed(self):
        if self.__new:
            return self.__mon.abortRequested() or self.__terminate
        else:
            return xbmc.abortRequested or self.__terminate  # @UndefinedVariable

    def close(self):
        self.onclose()
        self.__terminate = True

    @property
    def terminate(self):
        return self.__terminate


def builtin(*args, **kwargs):
    return xbmc.executebuiltin(*args, **kwargs)
