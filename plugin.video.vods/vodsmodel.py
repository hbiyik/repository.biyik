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
from tinyxbmc import gui
from tinyxbmc import addon
from tinyxbmc import tools


class extension(object):
    title = "Unnamed Extension"
    info = {}
    art = {"icon": "DefaultFolder.png", "thumb": "DefaultFolder.png", "poster": "DefaultFolder.png"}

    def __init__(self, container):
        self.__container = container
        self._address = []
        self.init()

    def download(self, *args, **kwargs):
        return self.__container.download(*args, **kwargs)

    def localtime(self, dtob, utc=True):
        if utc:
            dtob = dtob.replace(tzinfo=tools.tz_utc())
            return dtob.astimezone(tools.tz_local())
        else:
            return dtob.replace(tzinfo=tools.tz_local())

    def init(self, *args, **kwargs):
        pass

    def hay(self, *args, **kwargs):
        return self.__container.hay(*args, **kwargs)

    def getcache(self, arg, typ="movie"):
        mname = self.__class__.__module__
        cname = self.__class__.__name__
        path = ".".join([self.addonid, mname, cname, "metacache"])
        mname = "cache%ss" % typ
        stack = self.hay(path)
        info = stack.find("%s%sinfo" % (repr(arg), typ)).data
        art = stack.find("%s%sart" % (repr(arg), typ)).data
        isimp = hasattr(self, mname)
        if info == {} and art == {} and isimp:
            cache = getattr(self, mname)
            info, art = cache(arg)
            name = info.get("title")
            if not name:
                name = info.get("tvshowtitle", "media")
            stack.throw("%s%sinfo" % (repr(arg), typ), info)
            stack.throw("%s%sart" % (repr(arg), typ), art)
            gui.notify(self.__class__.__name__, "Cached %s" % name, False)
        return info, art


class scraperextension(extension):
    usedirect = True
    uselinkplayers = True
    useaddonplayers = True

    def __init__(self, container, page=None, addonid=None):
        self.__items = []
        self.__nextpage = (None, None, {}, {})
        self.__page = page
        self.__addonid = addonid
        self.setting = addon.kodisetting(addonid)
        super(scraperextension, self).__init__(container)

    def additem(self, name, arg=None, info=None, art=None):
        if not info:
            info = {}
        if not art:
            art = {}
        tup = (name, arg, info, art)
        self.__items.append(tup)

    def setnextpage(self, arg, name=None, info=None, art=None):
        if not info:
            info = {}
        if not art:
            art = {}
        if not name:
            name = "Next"
        self.__nextpage = (name, arg, info, art)

    @property
    def addonid(self):
        return self.__addonid

    @addonid.setter
    def addonid(self, val):
        raise ValueError("addonid can not be overriden")

    @property
    def items(self):
        return self.__items

    @items.setter
    def items(self, val):
        raise ValueError("items can not be overriden")

    @property
    def page(self):
        return self.__page

    @page.setter
    def page(self, val):
        raise ValueError("page can not be overriden")

    @property
    def nextpage(self):
        return self.__nextpage

    @nextpage.setter
    def nextpage(self, val):
        raise ValueError("nextpage can not be overriden")
