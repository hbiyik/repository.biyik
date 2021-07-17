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

from vods import movieextension
from vods import showextension
from vods import linkplayerextension
from vods import scraperextension
from vodsmodel import extension as vextension

from tinyxbmc import container
from tinyxbmc import extension
from tinyxbmc import gui
from tinyxbmc import const as tinyconst
from tinyxbmc import addon as tinyaddon
from tinyxbmc import tools
from tinyxbmc import net
from tinyxbmc import const

from six import string_types
import six

import traceback
import json
import os

_prefix = "plugin.program.vods-"
_resolvehay = "vods_resolve"
_useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36"
_timeout = 5
_extmovie = "vodsmovie"
_extshow = "vodsshow"
_extlinkplayer = "vodslinkplayer"
_extaddonplayer = "vodsaddonplayer"


def channelmethod(chanmethod):
    def wrapped(self, page, *args, **kwargs):
        try:
            six.next(self.getscrapers(page=page,
                                      mtd=chanmethod.__name__,
                                      args=args,
                                      **kwargs))
        except Exception:
            print(traceback.format_exc())
            return
        ret = chanmethod(self, *args)
        if self.chan.nextpage[0] and self._next:
            name, arg, info, art = self.chan.nextpage
            info["sorttitle"] = chr(255)  # :) hope this always works
            li = self.item(name, info, art, method=chanmethod.__name__)
            li.dir(arg, *args, **kwargs)
            self._next = False
        return ret
    return wrapped


def makenameart(cls):
    # auto config art for icon fallback
    if not hasattr(cls, "art") or cls.art == vextension.art:
        icon = tinyaddon.get_addon(cls._tinyxbmc["addon"]).getAddonInfo("icon")
        cls.art = {"thumb": icon, "poster": icon, "icon": icon}

    # auto config title form info or class name
    if not hasattr(cls, "title") or not isinstance(cls.title, string_types) or \
            cls.title == vextension.title:
        if hasattr(cls, "info") and isinstance(cls.info, dict) and \
                isinstance(cls.info.get("title"), string_types):
            cls.title = cls.info["title"]
        else:
            cls.title = cls.__class__.__name__.title()

    # make title unicode
    if six.PY2 and not isinstance(cls.title, unicode):
        try:
            cls.title = unicode(cls.title)
        except UnicodeError:
            try:
                import chardet
                enc = chardet.detect(cls.title)
                cls.title = unicode(cls.title.decode(enc["encoding"]))
            except Exception:
                cls.title = unicode(cls.title.encode("ascii", "ignore"))


class index(container.container):
    def init(self):
        self._next = True
        self.__bg = None
        self.option(_useragent, _timeout)

    @property
    def bgprg(self):
        if self.__bg is None:
            self.__bg = gui.bgprogress(self.chan.title)
        return self.__bg

    def onclose(self):
        if self.__bg is not None:
            self.__bg.close()

    def _isimp(self, base, mtd, clsob=None):
        if not clsob:
            clsob = self.chan
        if not hasattr(clsob, mtd):
            return False
        clsmtd = getattr(clsob, mtd)
        chnmtd = getattr(base, mtd)
        if six.PY2:
            return not clsmtd.__func__ == chnmtd.__func__
        else:
            return not clsmtd.__func__ == chnmtd

    def _context(self, mode=None, *args, **kwargs):
        if mode == "settings":
            tinyaddon.builtin("Addon.OpenSettings(%s)" % args[0])
        elif mode == "meta":
            try:
                six.next(self.getscrapers(**kwargs))
            except Exception:
                print(traceback.format_exc())
                return
            self._cachemeta(*args)
            tinyaddon.builtin("Container.Refresh")

    def _cachemeta(self, arg, info, art, typ, scrape=True, percent=None):
        if hasattr(arg, "__len__") and not len(arg):
            print("VODS: Warning, argument is empty, nothing to cache")
            return info, art
        if typ == "movie":
            base = movieextension
        elif typ == "show":
            base = showextension
        elif typ == "episode":
            base = showextension
        else:
            return info, art
        mname = "cache%ss" % typ
        if self._isimp(base, mname):
            path = ".".join([str(x) for x in self.chan._tinyxbmc.values()])
            cachehay = self.hay(path)
            cinfo = cachehay.find("%s%sinfo" % (repr(arg), typ)).data
            cart = cachehay.find("%s%sart" % (repr(arg), typ)).data
            if cinfo == {} and cart == {} and scrape:
                cache = getattr(self.chan, mname)
                try:
                    cinfo, cart = cache(arg)
                except Exception:
                    print(traceback.format_exc())
                    return info, art
                name = cinfo.get("title", info.get("title"))
                if not name:
                    name = cinfo.get("tvshowtitle", info.get("tvshowtitle", "media"))
                cachehay.throw("%s%sinfo" % (repr(arg), typ), cinfo)
                cachehay.throw("%s%sart" % (repr(arg), typ), cart)
                if not (cinfo == {} and cart == {}) and percent:
                    self.bgprg.update(int(percent), "Caching", name)
            info.update(cinfo)
            art.update(cart)
        return info, art

    def cacheresolve(self, arg, info, art):
        if info or art:
            hay = self.hay(_resolvehay)
            key = json.dumps(arg)
            if info:
                hay.throw(key + "_info", info)
            if art:
                hay.throw(key + "_art", art)

    def getscrapers(self, id, addon=None, path=None, package=None, module=None,
                    instance=None, mtd=None, args=[], page=None):
        for plg in extension.getplugins(id, addon, path, package, module, instance):
            ret = None
            try:
                chan = plg(self, page, plg._tinyxbmc["addon"])
                self.chan = chan
                if mtd:
                    m = getattr(chan, mtd)
                    ret = m(*args)
            except Exception:
                print(traceback.format_exc())
                continue

            # auto config art for icon fallback
            if not hasattr(chan, "art") or chan.art == scraperextension.art:
                icon = tinyaddon.get_addon(plg._tinyxbmc["addon"]).getAddonInfo("icon")
                if not icon:
                    # there seems to be a bug in Matrix for .getAddonInfo("icon"), instead use this hack
                    icon = tinyaddon.get_addon(plg._tinyxbmc["addon"]).getAddonInfo("path")
                    icon = os.path.join(icon, "icon.png")
                chan.art = {"thumb": icon, "poster": icon, "icon": icon}

            makenameart(chan)
            yield ret

    def index(self, *args, **kwargs):
        d = self.item("Search", method="search")
        d.dir()
        for _ in self.getscrapers([_extmovie, _extshow]):
            d = self.item(self.chan.title, self.chan.info, self.chan.art)
            if isinstance(self.chan, movieextension):
                d.method = "getmovies"
                args = []
            elif isinstance(self.chan, showextension):
                d.method = "getshows"
                args = [None]
            else:
                continue
            settings = self.item("Extension Settings", method="_context")
            d.context(settings, False, "settings", self.chan._tinyxbmc["addon"])
            d.dir(None, *args, **self.chan._tinyxbmc)
        return tinyconst.CT_ALBUMS

    def search(self, typ=None, cache=False, **kwargs):
        funcs = {1: "searchmovies", 2: "searchshows", 3: "searchepisodes"}
        if not typ:
            self.item("Search Movies", method="search").dir(1, cache, id=_extmovie, **kwargs)
            self.item("Search Shows", method="search").dir(2, cache, id=_extshow, **kwargs)
            self.item("Search Episodes", method="search").dir(3, cache, id=_extshow, **kwargs)
            return
        elif typ in funcs:
            conf, txt = gui.keyboard()
            if conf:
                self.item(method=funcs[typ]).redirect(txt, cache, **kwargs)
                return
        self.item(method="search").redirect()
        return tinyconst.CT_FILES

    def searchmovies(self, keyw, cache=False, **kwargs):
        for _ in self.getscrapers(mtd="searchmovies", args=[keyw], **kwargs):
            numitems = len(self.chan.items)
            if numitems:
                gui.notify(self.chan.title, "Found %d" % numitems, False)
            for i, [name, arg, info, art] in enumerate(self.chan.items):
                percent = (i + 1) * 100 / numitems
                info, art = self._cachemeta(arg, info, art, "movie", cache, percent)
                if info == {}:
                    info = {"title": name}
                self.cacheresolve(arg, info, art)
                lname = "[%s] %s" % (self.chan.title, name)
                li = self.item(lname, info, art, method="geturls")
                select = self.item("Select Source", info, art, method="selecturl")
                li.context(select, True, arg, **self.chan._tinyxbmc)
                if self._isimp(movieextension, "cachemovies") and not cache:
                    context = self.item("Query Meta Information", method="_context")
                    args = [arg, info, art, "movie"]
                    li.context(context, False, "meta", *args, **self.chan._tinyxbmc)
                li.resolve(arg, False, **self.chan._tinyxbmc)
        return tinyconst.CT_MOVIES

    def searchshows(self, keyw, cache=False, **kwargs):
        for _ in self.getscrapers(mtd="searchshows", args=[keyw], **kwargs):
            numitems = len(self.chan.items)
            if numitems:
                gui.notify(self.chan.title, "Found %d" % numitems, False)
            for i, [name, arg, info, art] in enumerate(self.chan.items):
                percent = (i + 1) * 100 / numitems
                info, art = self._cachemeta(arg, info, art, "show", cache, percent)
                if info == {}:
                    info = {"tvshowtitle": name}
                lname = "[%s] %s" % (self.chan.title, name)
                canseason = self._isimp(showextension, "getseasons")
                if canseason:
                    li = self.item(lname, info, art, method="getseasons")
                else:
                    li = self.item(lname, info, art, method="getepisodes")
                if self._isimp(showextension, "cacheshows") and not cache:
                    context = self.item("Query Meta Information", method="_context")
                    args = [arg, info, art, "show"]
                    li.context(context, False, "meta", *args, **self.chan._tinyxbmc)
                if canseason:
                    li.dir(None, arg, **self.chan._tinyxbmc)
                else:
                    li.dir(None, arg, None, **self.chan._tinyxbmc)
        return tinyconst.CT_TVSHOWS

    def searchepisodes(self, keyw, cache=False, **kwargs):
        for _ in self.getscrapers(mtd="searchepisodes", args=[keyw], **kwargs):
            numitems = len(self.chan.items)
            if numitems:
                gui.notify(self.chan.title, "Found %d" % numitems, False)
            for i, [name, arg, info, art] in enumerate(self.chan.items):
                percent = (i + 1) * 100 / numitems
                info, art = self._cachemeta(arg, info, art, "episode", cache, percent)
                self.cacheresolve(arg, info, art)
                lname = "[%s] %s" % (self.chan.title, name)
                li = self.item(lname, info, art, method="geturls")
                select = self.item("Select Source", info, art, method="selecturl")
                if self._isimp(showextension, "cacheepisodes") and not cache:
                    context = self.item("Query Meta Information", method="_context")
                    args = [arg, info, art, "episode"]
                    li.context(context, False, "meta", *args, **self.chan._tinyxbmc)
                li.context(select, True, arg, **self.chan._tinyxbmc)
                li.resolve(arg, False, **self.chan._tinyxbmc)
        return tinyconst.CT_EPISODES

    @channelmethod
    def getcategories(self):
        for name, cat, info, art, in self.chan.items:
            li = self.item(name, info, art)
            if self._isimp(movieextension, "getmovies"):
                li.method = "getmovies"
                li.dir(None, cat, **self.chan._tinyxbmc)
            elif self._isimp(showextension, "getshows") or \
                    self._isimp(showextension, "getepisodes"):
                li.method = "getshows"
                li.dir(None, cat, **self.chan._tinyxbmc)
        return tinyconst.CT_ALBUMS

    @channelmethod
    def getmovies(self, cat=None):
        if not self.chan.page and not cat:
            if self._isimp(movieextension, "searchmovies"):
                li = self.item("Search", method="search")
                li.dir(1, None, **self.chan._tinyxbmc)
            if self._isimp(movieextension, "getcategories"):
                li = self.item("Categories", method="getcategories")
                li.dir(None, **self.chan._tinyxbmc)
        numitems = len(self.chan.items)
        for i, [name, movie, info, art] in enumerate(self.chan.items):
            percent = (i + 1) * 100 / numitems
            info, art = self._cachemeta(movie, info, art, "movie", True, percent)
            self.cacheresolve(movie, info, art)
            li = self.item(name, info, art, method="geturls")
            select = self.item("Select Source", info, art, method="selecturl")
            li.context(select, True, movie, **self.chan._tinyxbmc)
            li.resolve(movie, False, **self.chan._tinyxbmc)
        return tinyconst.CT_MOVIES

    @channelmethod
    def getshows(self, cat=None):
        if not self.chan.page and not cat:
            if self._isimp(showextension, "searchshows"):
                li = self.item("Search Shows", method="search")
                li.dir(2, None, **self.chan._tinyxbmc)
            if self._isimp(showextension, "searchepisodes"):
                li = self.item("Search Episodes", method="search")
                li.dir(3, None, **self.chan._tinyxbmc)
            if self._isimp(showextension, "getcategories"):
                li = self.item("Categories", method="getcategories")
                li.dir(None, **self.chan._tinyxbmc)
            if not len(self.chan.items):
                return self.getepisodes(None, None, None, **self.chan._tinyxbmc)
        canseason = self._isimp(showextension, "getseasons")
        numitems = len(self.chan.items)
        for i, [name, show, info, art] in enumerate(self.chan.items):
            percent = (i + 1) * 100 / numitems
            info, art = self._cachemeta(show, info, art, "show", True, percent)
            if canseason:
                li = self.item(name, info, art, method="getseasons")
                li.dir(None, show, **self.chan._tinyxbmc)
            else:
                li = self.item(name, info, art, method="getepisodes")
                li.dir(None, show, None, **self.chan._tinyxbmc)
        return tinyconst.CT_TVSHOWS

    @channelmethod
    def getseasons(self, show):
        for name, sea, info, art in self.chan.items:
            li = self.item(name, info, art, method="getepisodes")
            li.dir(None, show, sea, **self.chan._tinyxbmc)
        return tinyconst.CT_ALBUMS

    @channelmethod
    def getepisodes(self, show, sea):
        numitems = len(self.chan.items)
        for i, [name, url, info, art] in enumerate(self.chan.items):
            percent = (i + 1) * 100 / numitems
            info, art = self._cachemeta(url, info, art, "episode", True, percent)
            li = self.item(name, info, art, method="geturls")
            select = self.item("Select Source", info, art, method="selecturl")
            li.context(select, True, url, **self.chan._tinyxbmc)
            li.resolve(url, False, **self.chan._tinyxbmc)
            self.cacheresolve(url, info, art)
        return tinyconst.CT_EPISODES

    def selecturl(self, url, **kwargs):
        key = json.dumps(url)
        info = self.hay(_resolvehay).find(key + "_info").data
        art = self.hay(_resolvehay).find(key + "_art").data
        try:
            links = six.next(self.getscrapers(mtd="geturls", args=[url], **kwargs))
        except Exception:
            print(traceback.format_exc())
            return
        for link in tools.safeiter(links):
            if not isinstance(link, string_types):
                continue
            item = self.item(link, info, art, method="geturls")
            self.cacheresolve(link, info, art)
            item.resolve(link, True, **kwargs)

    def logplayer(self, msg, percent=0):
        self.player.dlg.update(percent, msg)

    def geturls(self, url, direct, **kwargs):
        key = json.dumps(url)
        info = self.hay(_resolvehay).find(key + "_info").data
        art = self.hay(_resolvehay).find(key + "_art").data
        playerins = {}

        def getplayer(priority):
            target, hasinit, pcls = playerins[priority]
            if hasinit:
                return target, hasinit
            else:
                # self.logplayer("VODS is initializing %s" % target)
                try:
                    ins = pcls(self)
                    playerins[priority] = (target, ins, pcls)
                    makenameart(ins)
                    return target, ins
                except Exception:
                    print(traceback.format_exc())
                    return target, None

        def prepareplayers(priority, entrypoint):
            for player in extension.getplugins(entrypoint):
                priority += 1
                target = ":".join([str(x) for x in player._tinyxbmc.values()])
                playerins[priority] = (target, False, player)
            return priority

        if not direct:
            try:
                links = six.next(self.getscrapers(mtd="geturls", args=[url], **kwargs))
            except Exception:
                print(traceback.format_exc())
        else:
            try:
                six.next(self.getscrapers(**kwargs))
            except Exception:
                print(traceback.format_exc())
            links = iter([url])
        priority = 0
        if self.chan.useaddonplayers:
            priority = prepareplayers(priority, _extaddonplayer)
        if self.chan.usedirect:
            priority += 1
            playerins[priority] = ("direct", linkplayerextension(self), None)
        if self.chan.uselinkplayers:
            priority = prepareplayers(priority, _extlinkplayer)
        aplayers = ", ".join([playerins[x][0].replace("None", "") for x in sorted(playerins,
                                                                                  reverse=True)])
        self.logplayer("VODS found players (%s): %s" % (len(playerins), aplayers))
        for kodilink in tools.safeiter(links):
            if isinstance(kodilink, const.URL):
                yield kodilink
                continue
            if self.player.dlg.iscanceled():
                    raise StopIteration
            link, headers = net.fromkodiurl(kodilink)
            if six.PY2:
                alink = link.encode("ascii", "replace")
            else:
                alink = link
            if not isinstance(link, six.string_types):
                self.logplayer("VODS received broken link, skipping...: %s" % alink)
                continue
            self.logplayer("VODS is scraping link: %s" % alink)
            for priority in sorted(playerins, reverse=True):
                if self.player.dlg.iscanceled():
                    raise StopIteration
                target, pcls = getplayer(priority)
                if six.PY2:
                    atarget = target.encode("ascii", "replace").replace("None", "")
                else:
                    atarget = target
                self.logplayer("VODS is trying player: %s %s" % (alink, atarget))
                if not pcls:
                    self.logplayer("VODS received broken player, skipping...: %s %s" % (alink,
                                                                                        atarget))
                    continue
                found = False
                isaddon = False
                for url in tools.safeiter(pcls.geturls(link, headers)):
                    if self.player.dlg.iscanceled():
                        raise StopIteration
                    if not url:
                        continue
                    if six.PY2:
                        aurl = url.encode("ascii", "replace")
                    else:
                        aurl = url
                    found = True
                    if url.startswith("plugin://"):
                        try:
                            url = pcls.builtin % url
                        except Exception:
                            print(traceback.format_exc())
                            continue
                        isaddon = True
                    yield url, info, art
                if found and not isaddon:
                    while True:
                        if not self._isplaying == 1 or self.player.dlg.iscanceled():
                            break
                    if self._isplaying == 2:
                        self.logplayer("VODS started playback : %s" % aurl, 100)
                        break
