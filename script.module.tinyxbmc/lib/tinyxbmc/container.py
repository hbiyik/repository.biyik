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
# we want to patch python since some standart libraries in kodi python interpreter needs mocking
from tinyxbmc import mocks
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmc

import json
import importlib

import time
import sys
import six
from six.moves.urllib import parse

from tinyxbmc import hay
from tinyxbmc import const
from tinyxbmc import tools
from tinyxbmc import gui
from tinyxbmc import net
from tinyxbmc import addon
from tinyxbmc import collector

REMOTE_DBG = False
PROFILE = False

if REMOTE_DBG:
    # pdevpath = "C:\\Users\\z0042jww\\.p2\\pool\\plugins\\org.python.pydev.core_7.2.1.201904261721\\pysrc"
    # pdevpath = "/home/boogie/.p2/pool/plugins/org.python.pydev.core_7.2.1.201904261721/pysrc/"
    pdevpath = "/home/boogie/.p2/pool/plugins/org.python.pydev.core_9.3.0.202203051235/pysrc/"
    # pdevpath = "/home/boogie/src/pydevd"
    sys.path.append(pdevpath)
    import pydevd  # @UnresolvedImport
    pydevd.settrace(stdoutToServer=True, stderrToServer=True, suspend=False)

if PROFILE:
    import pprofile
    profiler = pprofile.Profile()

_startt = time.time()
_default_method = "index"


def refresh():
    xbmc.executebuiltin("Container.Refresh")


class container(object):
    def __init__(self, addonid=None, *iargs, **ikwargs):
        self.dropboxtoken = None
        with collector.LogException("TINYXBMC ERROR", const.DB_TOKEN, ignore=False) as errorcol:
            if PROFILE:
                profiler.enable()
            self.__inittime = time.time()
            self.sysaddon = sys.argv[0]
            self.player = None
            self.playertimeout = 60
            self.emptycontainer = True
            aurl = parse.urlparse(self.sysaddon)
            if aurl.scheme.lower() in ["plugin", "script"]:
                self.addon = aurl.netloc
            elif addonid:
                self.addon = addonid
            else:
                raise Exception("Unknown Addon name")
            try:
                self.syshandle = int(sys.argv[1])
            except Exception:
                self.syshandle = -1
            try:
                serial = sys.argv[2][1:]
                data = json.loads(parse.unquote_plus(serial))
            except Exception:
                data = {}
            self._items = []
            self._playlist = []
            self._hays = {}
            self._container = data.get("container", self.__class__.__name__)
            self._module = data.get("module", self.__class__.__module__)
            self._method = data.get("method", _default_method)
            self._media = data.get("media", None)
            args = data.get("args", [])
            kwargs = data.get("kwargs", {})
            self._disp_container = self._container
            self._disp_module = self._module
            self._disp_method = self._method
            self._isplaying = 0  # 0 stopped, 1: trying, 2: started
            self.ondispatch()
            if self._disp_module == self.__class__.__module__:
                if self._disp_container == self.__class__.__name__:
                    self._container = self
                else:
                    self._module = sys.modules[self._disp_module]
                    self._container = getattr(self._module, self._disp_container)()
                    return
            else:
                self._module = importlib.import_module(self._disp_module)
                self._container = getattr(self._module, self._disp_container)()
                return
            self.__itime = (time.time() - _startt) * 1000
            dispatchdata = "MODULE    : %s\r\n" % self._disp_module
            dispatchdata += "CONTAINER : %s\r\n" % self._disp_container
            dispatchdata += "METHOD    : %s\r\n" % self._disp_method
            dispatchdata += "ARGUMENTS : %s\r\n" % repr(args)
            dispatchdata += "KW ARGS   : %s\r\n" % repr(kwargs)
            dispatchdata += "MEDIA     : %s\r\n" % repr(self._media)
            errorcol.msg = dispatchdata
            xbmc.log("TinyXBMC is Dispatching")
            xbmc.log("\r\n" + dispatchdata)
            self._container.useragent = const.USERAGENT
            self._container.httptimeout = const.HTTPTIMEOUT
            self._container.autoupdate = False
            with collector.LogException("TINYXBMC EXTENSION ERROR", None, ignore=True) as ext_errcoll:
                ext_errcoll.token = self._container.dropboxtoken
                self._container.init(*iargs, **ikwargs)
            self._method = getattr(self._container, self._disp_method)
            if self._container._media == "resolver":
                redirects = []
                self.player = xbmcplayer(timeout=self.playertimeout)
                for u, finfo, fart in tools.dynamicret(tools.safeiter(self._method(*args, **kwargs))):
                    imdbid = finfo.get("imdbnumber", finfo.get("code", None))
                    if imdbid:
                        xbmcgui.Window(10000).setProperty('script.trakt.ids', json.dumps({u'imdb': imdbid}))
                    if not isinstance(u, (six.string_types, const.URL)):
                        addon.log("Provided url %s is not playable" % repr(u))
                        continue
                    if self.player.dlg.iscanceled():
                        break
                    self.player.fallbackinfo = finfo
                    self.player.fallbackart = fart
                    self._container._isplaying = 1
                    if isinstance(u, six.string_types) and "plugin://" in u:
                        # play in another addonid
                        redirects.append(u)
                        continue
                    state = self.player.stream(u)
                    if state:
                        self._container._isplaying = 2
                        self._close()
                        return
                    else:
                        self._container._isplaying = 0
                        self.player.dlg.update(100, "Skipping broken url: %s" % u)
                if not self._container._isplaying == 2 and len(redirects):
                    redirects = list(set(redirects))
                    if len(redirects) == 1:
                        u = redirects[0]
                    else:
                        u = gui.select("Select Addon", *redirects)
                    if self.player.canresolve:
                        self.player.stream("", xbmcgui.ListItem())
                    tools.builtin(u)
                    state = self.player.waitplayback(u)
                    self._close()
                    self._container._isplaying = 2
                    return
                if self._container._isplaying == 0:
                    self.player.dlg.close()
            elif self._container._media == "player":
                p = xbmc.PlayList(1)
                p.clear()
                for u, info, art in tools.dynamicret(tools.safeiter(self._method(*args, **kwargs))):
                    item = xbmcgui.ListItem(path=u)
                    item.setInfo("video", info)
                    gui.setArt(item, art)
                    p.add(u, item)
                xbmc.Player().play(p)
            else:
                def _onexception():
                    self._close()
                    sys.exit()
                with collector.LogException("TINYXBMC EXTENSION ERROR", None, ignore=True) as ext_errcoll:
                    ext_errcoll.onexception = _onexception
                    ext_errcoll.token = self._container.dropboxtoken
                    cnttyp = self._method(*args, **kwargs)
                itemlen = len(self._container._items)
                if cnttyp in const.CT_ALL:
                    xbmcplugin.setContent(self.syshandle, cnttyp)
                if itemlen:
                    for url, item, isfolder in self._container._items:
                        if cnttyp in const.CT_ALL:
                            setview = self.item("Set view default for %s" % cnttyp.upper())
                            setview.method = "_setview"
                            item.context(setview, False, cnttyp)
                            item.docontext()
                        xbmcplugin.addDirectoryItem(self.syshandle, url, item.item, isfolder, itemlen)
                if self.emptycontainer or itemlen:
                    xbmcplugin.endOfDirectory(self.syshandle, cacheToDisc=True)
                if self._container.autoupdate:
                    d = self.item("Auto Update", method="_update")
                    d.run(self._container.autoupdate)
                if cnttyp in const.CT_ALL:
                    views = self.hay(const.OPTIONHAY).find("views").data
                    if cnttyp in views:
                        spath = tools.getSkinDir()
                        view = views[cnttyp].get(spath, None)
                        if view:
                            for _ in range(0, 10 * 20):
                                if xbmc.getCondVisibility('Container.Content(%s)' % cnttyp):
                                    xbmc.executebuiltin("Container.SetSortMethod(27)")
                                    xbmc.executebuiltin('Container.SetViewMode(%d)' % view)
                                    break
                                xbmc.sleep(100)
            self._close()
            if PROFILE:
                profiler.disable()
                profiler.dump_stats("tinyxbmcprofile.txt")
                with open("cachegrind.out.tinyxbmc", "w") as f:
                    profiler.callgrind(f)

    def option(self, useragent=None, httptimeout=None):
        opthay = self.hay(const.OPTIONHAY)
        if useragent:
            self._container.useragent = useragent
            opthay.throw("useragent", useragent)
        if httptimeout:
            self._container.httptimeout = httptimeout
            opthay.throw("httptimeout", httptimeout)

    def resolver(self, url):
        yield net.urlfromdict(url)

    def player(self, url):
        yield url

    def _update(self, wait):
        xbmc.sleep(wait * 1000)
        refresh()

    def _close(self):
        for _, hay in self._hays.items():
            hay.close()
        self.onclose()
        dtime = (time.time() - self.__inittime) * 1000
        etime = (time.time() - _startt) * 1000
        xbmc.log("****** TinyXBMC is Dispatched ******")
        xbmc.log("INIT TIME      : %s ms" % self.__itime)
        xbmc.log("DISPATCH TIME  : %s ms" % dtime)
        xbmc.log("EXECUTION TIME : %s ms" % etime)
        xbmc.log("************************************")

    def _art(self, art, headers=None):
        d = art.copy()
        if not headers:
            headers = {}
        if "user-agent" not in [x.lower() for x in headers.keys()]:
            headers["user-agent"] = self._container.useragent
        for k, v in d.items():
            try:
                d[k] = net.tokodiurl(v, headers=headers)
            except Exception:
                pass
        return d

    def _setview(self, ct):
        stack = self.hay(const.OPTIONHAY)
        data = stack.find("views").data
        current = data.get(ct, {})
        spath = tools.getSkinDir()
        current[spath] = tools.getskinview()
        data[ct] = current
        stack.throw("views", data)
        gui.notify(ct.upper(), "Default view is updated")

    def init(self, *args, **kwargs):
        pass

    def item(self, name="item", info=None, art=None, module=None, container=None, method=None):
        if not info:
            info = {}
        if not art:
            art = {}
        if isinstance(name, int):
            if six.PY2:
                name = xbmcaddon.Addon().getLocalizedString(name).encode('utf-8')
            else:
                name = xbmcaddon.Addon().getLocalizedString(name)
        if not art.get("icon"):
            art["icon"] = "DefaultFolder.png"
        if not art.get("thumb"):
            art["thumb"] = "DefaultFolder.png"
        tinyitem = itemfactory(self, name, info, art, module, container, method)
        return tinyitem

    def play(self, url, name="item", info=None, art=None):
        if not info:
            info = {}
        if not art:
            art = {}
        item = xbmcgui.ListItem(label=name)
        gui.setArt(item, self._art(art))
        item.setInfo("videos", info)
        self._playlist.append((url, item))

    def index(self, *args, **kwargs):
        # item = self.item("Hello TinyXBMC")
        # item.dir()
        pass

    def ondispatch(self):
        pass

    def onclose(self):
        pass

    def hay(self, hayid, *args, **kwargs):
        if hayid not in self._hays:
            kwargs["aid"] = self.addon
            if "compress" not in kwargs:
                kwargs["compress"] = 0
            if "serial" not in kwargs:
                kwargs["serial"] = "json"
            h = hay.stack(hayid, *args, **kwargs)
            self._hays[hayid] = h
        else:
            h = self._hays[hayid]
        return h

    def download(self, url, params=None, data=None, headers=None, timeout=None,
                 json=None, method="GET", referer=None, useragent=None, encoding="utf-8",
                 verify=None, stream=None, proxies=None, cache=10, text=True):

        if not (headers and "user-agent" in [x.lower() for x in headers] or useragent):
            useragent = self._container.useragent
        if not timeout:
            timeout = self._container.httptimeout
        ret = net.http(url, params, data, headers, timeout, json, method, referer,
                       useragent, encoding, verify, stream, proxies, cache, text)
        return ret


class itemfactory(object):
    def __init__(self, context, name, info, art, module=None, container=None, method=None):
        self.name = name
        self.info = info
        self.art = art
        item = xbmcgui.ListItem(label=name)
        gui.setArt(item, context._art(art))
        item.setInfo("video", info)
        # item.addStreamInfo('video', {'Codec': ''})
        self.item = item
        self._cntx = context
        if not module:
            module = self._cntx._disp_module
        if not container:
            container = self._cntx._disp_container
        if not method:
            method = self._cntx._disp_method
        self.module = module
        self.container = container
        self.method = method
        self.removeold = False
        self.media = None
        self._contexts = []

    def dourl(self, media, *args, **kwargs):
        data = {"module": self.module,
                "container": self.container,
                "method": self.method,
                "args": args,
                "kwargs": kwargs,
                "media": media,
                }
        serial = parse.quote_plus(json.dumps(data, sort_keys=True))
        self.url = '%s?%s' % (self._cntx.sysaddon, serial)
        return self.url

    def docontext(self):
        self.item.addContextMenuItems(self._contexts, self.removeold)

    def _dir(self, isFolder, url=None, media=None, *args, **kwargs):
        if not url:
            url = self.dourl(media, *args, **kwargs)
        self.docontext()
        if media == "resolver":
            self.item.setProperty('IsPlayable', 'true')
        self._cntx._container._items.append([url, self, isFolder])

    def dir(self, *args, **kwargs):
        #  item is added to container as a navigatable folder (isFolder=True)
        self._dir(True, None, None, *args, **kwargs)

    def call(self, *args, **kwargs):
        #  item is added to container as a callable folder (isFolder=False)
        self._dir(False, None, None, *args, **kwargs)

    def run(self, *args, **kwargs):
        #  item is not added to container but called on runtime
        url = self.dourl(None, *args, **kwargs)
        xbmc.executebuiltin('RunPlugin(%s)' % url)

    def redirect(self, *args, **kwargs):
        #  item is not added to container but directory is changed to another container
        #  on runtime
        url = self.dourl(None, *args, **kwargs)
        if tools.kodiversion() > 17:
            xbmc.executebuiltin('Container.Update(%s, replace)' % url)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), True, False, False)
        else:
            xbmc.executebuiltin('Container.Update(%s)' % url)

    def resolve(self, *args, **kwargs):
        if self._cntx._disp_method == self.method:
            self.method = "resolver"
        self._dir(False, None, "resolver", *args, **kwargs)

    def play(self, *args, **kwargs):
        if self._cntx._disp_method == self.method:
            self.method = "player"
        self._dir(False, None, "player", *args, **kwargs)

    def context(self, sub, isdir, *args, **kwargs):
        url = sub.dourl(sub.media, *args, **kwargs)
        sub.item.addContextMenuItems(sub._contexts)  # nested fun :)
        if isdir:
            self._contexts.append([sub.name, 'Container.Update(%s)' % url])
        else:
            self._contexts.append([sub.name, 'RunPlugin(%s)' % url])


class xbmcplayer(xbmc.Player):

    def __init__(self, fallbackinfo=None, fallbackart=None, *args, **kwargs):
        if not fallbackinfo:
            fallbackinfo = {}
        if not fallbackart:
            fallbackart = {}
        self.alive = False
        self.fallbackinfo = fallbackinfo
        self.fallbackart = fallbackart
        xbmc.Player.__init__(self)
        self.timeout = int(kwargs.get("timeout", 10))  # max time to wait after player initiated the playback but not yet played
        self.ttol = 3  # max time to wait for player to initiate the playback
        self.dlg = xbmcgui.DialogProgress()
        self.dlg.create('Opening Media', 'Waiting for media')
        self.canresolve = True
        self.waiting = False

    def stream(self, url, li=None):
        if isinstance(url, const.URL):
            u = net.tokodiurl(url.url, headers=url.headers, pushverify="false", pushua=const.USERAGENT)
        else:
            u = net.tokodiurl(url, pushverify="false", pushua=const.USERAGENT)
        if not li:
            li = xbmcgui.ListItem(path=u)
        if isinstance(url, const.URL) and url.inputstream:
            # utilize inputstream adaptive
            if tools.kodiversion() >= 19:
                li.setProperty('inputstream', url.inputstream)
            else:
                li.setProperty('inputstreamaddon', url.inputstream)
            li.setProperty('inputstream.adaptive.manifest_type', url.manifest)
            if isinstance(url, net.mpdurl) and url.lurl:
                li.setProperty('inputstream.adaptive.license_type', url.license)
                url.lurl, url.lheaders = net.fromkodiurl(net.tokodiurl(url.lurl, headers=url.lheaders, pushua=const.USERAGENT, pushverify="false"))
                li.setProperty('inputstream.adaptive.license_key', url.kodilurl)
        if self.dlg.iscanceled():
            return
        if self.canresolve:
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)
        else:
            if self.fallbackinfo:
                li.setInfo("video", self.fallbackinfo)
            if self.fallbackart:
                gui.setArt(li, self.fallbackart)
            self.play(u, li)
        return self.waitplayback(u)

    def waitplayback(self, u=""):
        self.waiting = True
        factor = 5
        startt = time.time()
        for i in range(self.timeout * factor):
            p = 100 * i / (self.timeout * factor)
            self.dlg.update(int(p), u)
            xbmc.executebuiltin('Dialog.Close(12002,true)​')
            if self.alive or \
                (not self.isPlaying() and time.time() - startt > self.ttol) or \
                    self.dlg.iscanceled():
                if not self.alive:
                    if time.time() - startt > self.ttol:
                        addon.log("Can't play media because player can not initiate the playback (%i seconds): %s" % (self.ttol, u))
                    if self.dlg.iscanceled():
                        addon.log("Can't play media because user cancelled: %s" % u)
                else:
                    addon.log("Succesfully playing: %s" % u)
                break
            xbmc.sleep(int(1000 / factor))
        if not self.alive:
            if self.isPlaying():
                addon.log("Can't play media because player initiate the playback, but the playback did not start in time (%i seconds): %s" % (self.timeout, u))
            self.canresolve = False
            xbmc.executebuiltin('Dialog.Close(12002,true)​')
            self.dlg.create('Opening Media', 'Waiting for media')
        else:
            xbmc.executebuiltin('Dialog.Close(all,true)​')
        self.dlg.update(100, "")
        self.waiting = False
        return self.alive

    def onPlayBackStarted(self):
        if tools.kodiversion() < 18:
            self.dlg.close()
            self.alive = True

    def onAVStarted(self):
        self.dlg.close()
        self.alive = True
