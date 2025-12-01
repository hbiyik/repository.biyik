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
from vods import scraperextension
from player import Players
from vodsmodel import extension as vextension

import meta

from tinyxbmc import container
from tinyxbmc import extension
from tinyxbmc import gui
from tinyxbmc import const as tinyconst
from tinyxbmc import addon as tinyaddon
from tinyxbmc import tools
from tinyxbmc import net
from tinyxbmc import const
from tinyxbmc import collector
from tinyxbmc import mediaurl
from tinyxbmc import flare

import os
from datetime import datetime


ADDONPREFIX = "plugin.program.vods-"
CACHEHAY = "vods_cache"
USERAGENT = flare.USERAGENT
TIMEOUT = 5
EXTMOVIE = "vodsmovie"
EXTSHOW = "vodsshow"


def channelmethod(chanmethod):
    def wrapped(self, page, *args, **kwargs):
        with collector.LogException("VODS", const.DB_TOKEN, True) as errcoll:
            next(self.getscrapers(page=page,
                                  mtd=chanmethod.__name__,
                                  args=args,
                                  **kwargs))
            if errcoll.hasexception:
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
    if not hasattr(cls, "title") or not isinstance(cls.title, str) or \
            cls.title == vextension.title:
        if hasattr(cls, "info") and isinstance(cls.info, dict) and \
                isinstance(cls.info.get("title"), str):
            cls.title = cls.info["title"]
        else:
            cls.title = cls.__class__.__name__.title()


class index(container.container):
    def init(self):
        self.dropboxtoken = const.DB_TOKEN
        self._next = True
        self.__bg = None
        self.today = datetime.today()

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
        return not clsmtd.__func__ == chnmtd

    def getimdb(self, info, istv):
        imdbid = info.get("imdbnumber")
        if not imdbid:
            return
        if not isinstance(imdbid, str) or not imdbid.startswith("tt"):
            return
        results = meta.findimdb(imdbid, istv)
        if not results:
            return
        return imdbid

    def cachemeta(self, info, art, arg=None, istv=False, percent=None):
        imdbid = info.get("imdbnumber")
        season = info.get("season")
        if not isinstance(season, int):
            season = None
        episode = info.get("episode")
        if not isinstance(episode, int):
            episode = None

        key = imdbid or arg
        # lookup in cache
        lang = tools.language()
        cachehay = self.hay(".".join([str(x) for x in self.chan._tinyxbmc.values()]))
        cachekey = f"{key}_{season}_{episode}_{lang}"
        details = cachehay.find(cachekey).data
        airedlater = False
        newinfo = {}
        newart = {}

        if details:
            # fetch from cache
            newinfo = meta.kodiinfo(details, istv, season, episode, lang)
            newart = meta.kodiart(details, lang)
            # check if cahed data is mature enough, if before aired, then fetch & cache again
            airdate = newinfo.get("aired")
            airedlater = airdate is not None and datetime.strptime(airdate, "%Y-%m-%d") > self.today

        if not details or airedlater:
            # query imdbid with a callback to the scraper if no cache is hit
            if imdbid is None:
                if arg is None or not self._isimp(showextension, "getimdb") or not self._isimp(movieextension, "getimdb"):
                    return
                with collector.LogException("VODS", const.DB_TOKEN, True) as errcoll:
                    imdbid = self.chan.getimdb(arg)
                    if errcoll.hasexception:
                        return
            # sanity check of imdbid
            if not isinstance(imdbid, str) or not imdbid.startswith("tt"):
                return
            details = meta.query(imdbid, istv, season, episode, lang)
            if not details:
                return
            # make cache
            cachehay.throw(cachekey, details)
            newinfo = meta.kodiinfo(details, istv, season, episode, lang)
            newart = meta.kodiart(details, lang)
            if percent is not None:
                name = newinfo.get("tvshowtitle", info.get("title", imdbid))
                if season is not None and episode is not None:
                    name = f"{name} S{season}E{episode}"
                elif season is not None:
                    name = f"{name} S{season}"
                self.bgprg.update(int(percent), " Meta", name)

        info.update(newinfo)
        art.update(newart)

    def getscrapers(self, id, addon=None, path=None, package=None, module=None,
                    instance=None, mtd=None, args=[], page=None):
        for plg in extension.getplugins(id, addon, path, package, module, instance):
            ret = None
            with collector.LogException("VODS ADDON: %s" % plg._tinyxbmc["addon"], None, True) as errcoll:
                # channel instantiate
                chan = plg(self, page, plg._tinyxbmc["addon"])
                self.chan = chan
                errcoll.token = self.chan.dropboxtoken
                if mtd:
                    # channel method call
                    m = getattr(chan, mtd)
                    ret = m(*args)

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

    def cacheextentions(self, refresh=False):
        extentions = []
        for _ in self.getscrapers([EXTMOVIE, EXTSHOW]):
            if isinstance(self.chan, movieextension):
                method = "getmovies"
                args = []
            elif isinstance(self.chan, showextension):
                method = "getshows"
                args = [None]
            else:
                continue
            extentions.append([self.chan.title,
                               self.chan.info,
                               self.chan.art,
                               method,
                               args,
                               self.chan._tinyxbmc])
        hay = self.hay(CACHEHAY)
        hay.throw("index", extentions)
        if refresh:
            container.refresh()

    def index(self, *args, **kwargs):
        d = self.item("Search", method="mainsearch")
        d.dir()
        hay = self.hay(CACHEHAY)
        scrapers = hay.find("index").data
        if not scrapers:
            self.cacheextentions()
            scrapers = hay.find("index").data
        for title, info, art, method, args, kwargs in scrapers:
            d = self.item(title, info, art)
            d.method = method
            settings = self.item("Extension Settings")
            d.context(settings, "builtin", "Addon.OpenSettings(%s)" % kwargs["addon"])
            d.dir(None, *args, **kwargs)
        d = self.item("Update Extentions", method="cacheextentions")
        d.call(refresh=True)
        return tinyconst.CT_ALBUMS

    def mainsearch(self, **kwargs):
        self.item("Search Movies", method="getsearchinput").call("searchmovies", id=EXTMOVIE, **kwargs)
        self.item("Search Shows", method="getsearchinput").call("searchshows", id=EXTSHOW, **kwargs)
        self.item("Search Episodes", method="getsearchinput").call("searchepisodes", id=EXTSHOW, **kwargs)
        return tinyconst.CT_FILES

    def getsearchinput(self, funcname, **kwargs):
        conf, keyw = gui.keyboard()
        if not conf:
            return tinyconst.CT_FILES
        self.item("Redirect", method=funcname).redirect(keyw, **kwargs)

    def searchmovies(self, keyw, **kwargs):
        for _ in self.getscrapers(mtd="searchmovies", args=[keyw], **kwargs):
            numitems = len(self.chan.items)
            if numitems:
                gui.notify(self.chan.title, "Found %d" % numitems, False)
            for i, [name, arg, info, art] in enumerate(self.chan.items):
                percent = (i + 1) * 100 / numitems
                self.cachemeta(info, art, arg, False, percent)
                if not info:
                    info = {"title": name}
                lname = "[%s] %s" % (self.chan.title, name)
                self.addvideo(lname, arg, info, art)
        return tinyconst.CT_MOVIES

    def searchshows(self, keyw, **kwargs):
        for _ in self.getscrapers(mtd="searchshows", args=[keyw], **kwargs):
            numitems = len(self.chan.items)
            if numitems:
                gui.notify(self.chan.title, "Found %d" % numitems, False)
            for i, [name, arg, info, art] in enumerate(self.chan.items):
                percent = (i + 1) * 100 / numitems
                self.cachemeta(info, art, arg, True, percent)
                if not info:
                    info = {"tvshowtitle": name}
                lname = "[%s] %s" % (self.chan.title, name)
                canseason = self._isimp(showextension, "getseasons")
                if canseason:
                    li = self.item(lname, info, art, method="getseasons")
                    li.dir(None, arg, **self.chan._tinyxbmc)
                else:
                    li = self.item(lname, info, art, method="getepisodes")
                    li.dir(None, arg, None, **self.chan._tinyxbmc)

        return tinyconst.CT_TVSHOWS

    def searchepisodes(self, keyw, **kwargs):
        for _ in self.getscrapers(mtd="searchepisodes", args=[keyw], **kwargs):
            numitems = len(self.chan.items)
            if numitems:
                gui.notify(self.chan.title, "Found %d" % numitems, False)
            for i, [name, arg, info, art] in enumerate(self.chan.items):
                percent = (i + 1) * 100 / numitems
                self.cachemeta(info, art, arg, True, percent)
                lname = "[%s] %s" % (self.chan.title, name)
                self.addvideo(lname, arg, info, art)
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
        return tinyconst.CT_VIDEOS

    @channelmethod
    def getmovies(self, cat=None):
        if not self.chan.page and not cat:
            if self._isimp(movieextension, "searchmovies"):
                li = self.item("Search", method="getsearchinput")
                li.call("searchmovies", **self.chan._tinyxbmc)
            if self._isimp(movieextension, "getcategories"):
                li = self.item("Categories", method="getcategories")
                li.dir(None, **self.chan._tinyxbmc)
        numitems = len(self.chan.items)
        for i, [name, movie, info, art] in enumerate(self.chan.items):
            percent = (i + 1) * 100 / numitems
            self.cachemeta(info, art, movie, False, percent)
            self.addvideo(name, movie, info, art)
        return tinyconst.CT_MOVIES

    @channelmethod
    def getshows(self, cat=None):
        if not self.chan.page and not cat:
            if self._isimp(showextension, "searchshows"):
                li = self.item("Search Shows", method="getsearchinput")
                li.call("searchshows", **self.chan._tinyxbmc)
            if self._isimp(showextension, "searchepisodes"):
                li = self.item("Search Episodes", method="getsearchinput")
                li.call("searchepisodes", **self.chan._tinyxbmc)
            if self._isimp(showextension, "getcategories"):
                li = self.item("Categories", method="getcategories")
                li.dir(None, **self.chan._tinyxbmc)
            if not len(self.chan.items):
                return self.getepisodes(None, None, None, **self.chan._tinyxbmc)
        canseason = self._isimp(showextension, "getseasons")
        numitems = len(self.chan.items)
        for i, [name, show, info, art] in enumerate(self.chan.items):
            percent = (i + 1) * 100 / numitems
            self.cachemeta(info, art, show, True, percent)
            if canseason:
                li = self.item(name, info, art, method="getseasons")
                li.dir(None, show, **self.chan._tinyxbmc)
            else:
                li = self.item(name, info, art, method="getepisodes")
                li.dir(None, show, None, **self.chan._tinyxbmc)
        return tinyconst.CT_TVSHOWS

    @channelmethod
    def getseasons(self, show):
        numitems = len(self.chan.items)
        for i, (name, sea, info, art) in enumerate(self.chan.items):
            percent = (i + 1) * 100 / numitems
            self.cachemeta(info, art, sea, True, percent)
            li = self.item(name, info, art, method="getepisodes")
            li.dir(None, show, sea, **self.chan._tinyxbmc)
        return tinyconst.CT_VIDEOS

    def addvideo(self, name, url, info, art):
        li = self.item(name, info, art, method="geturls")
        select = self.item("Select Source", info, art, method="selecturl")
        li.context(select, True, url, info, art, **self.chan._tinyxbmc)
        li.resolve(url,
                   addonplayers=self.chan.useaddonplayers,
                   linkplayers=self.chan.uselinkplayers,
                   **self.chan._tinyxbmc)

    @channelmethod
    def getepisodes(self, show, sea):
        numitems = len(self.chan.items)
        for i, [name, url, info, art] in enumerate(self.chan.items):
            percent = (i + 1) * 100 / numitems
            self.cachemeta(info, art, url, True, percent)
            self.addvideo(name, url, info, art)
        return tinyconst.CT_EPISODES

    def selecturl(self, url, info, art, **kwargs):
        with collector.LogException("VODS", const.DB_TOKEN, True) as errcoll:
            links = next(self.getscrapers(mtd="geturls", args=[url], **kwargs))
            if errcoll.hasexception:
                return
        for link in tools.safeiter(links):
            if isinstance(link, str):
                item = self.item(link, info, art, method="geturls")
            elif isinstance(link, mediaurl.BaseUrl):
                item = self.item(link.prettyurl, info, art, method="geturls")
            else:
                self.log("Scraper returned a broken link: %s" % (repr(link)))
                continue
            item.resolve(link,
                         addonplayers=self.chan.useaddonplayers,
                         linkplayers=self.chan.uselinkplayers)

    def geturls(self, *args, addonplayers=True, linkplayers=True, **kwargs):
        self.log("Scraping with args: %s" % repr(args))
        players = Players(addonplayers, linkplayers)
        if kwargs:
            links = next(self.getscrapers(mtd="geturls", args=args, **kwargs))
        else:
            links = iter(args)
        for scraperlink in tools.safeiter(links, self.player.iscanceled):
            if isinstance(scraperlink, mediaurl.BaseUrl):
                self.log("Openning direct link: %s" % scraperlink.prettyurl)
                yield scraperlink
                continue
            if not isinstance(scraperlink, str):
                # scrapers must return a string link
                self.log("Skipping broken link from scraper: %s" % scraperlink)
                continue
            scraperlink, scraperheaders = net.fromkodiurl(scraperlink)
            for player in tools.safeiter(players.list(), self.player.iscanceled):
                self.log("Using %s to scrape: %s" % (players.target(player), scraperlink))
                for playerlink in tools.safeiter(player.geturls(scraperlink, scraperheaders), self.player.iscanceled):
                    if not isinstance(playerlink, mediaurl.BaseUrl):
                        self.log("Skipping broken link from player: %s" % repr(playerlink))
                        continue
                    self.log("Openning resolved link: %s" % playerlink.prettyurl)
                    yield playerlink
