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
import traceback
import inspect
import time
import sys
from distutils.version import LooseVersion
from urllib import parse

REMOTE_DBG = False
# REMOTE_DBG = "192.168.2.10"
PROFILE = False

if REMOTE_DBG:
    import pydevd  # @UnresolvedImport
    pydevd.settrace(REMOTE_DBG, stdoutToServer=True, stderrToServer=True, suspend=False)

if PROFILE:
    import pprofile
    profiler = pprofile.Profile()

from tinyxbmc import const
from tinyxbmc import mediaurl
from tinyxbmc import hay
from tinyxbmc import const
from tinyxbmc import tools
from tinyxbmc import gui
from tinyxbmc import net
from tinyxbmc import addon
from tinyxbmc import collector
from tinyxbmc import mediaurl
from tinyxbmc import flare

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
                if not serial:
                    data = {}
                else:
                    data = json.loads(parse.unquote_plus(serial), object_hook=mediaurl.BaseUrl.fromdict)
            except Exception:
                addon.log("Failed to parse parameters to dispatch %s" % repr(sys.argv))
                addon.log(traceback.format_exc())
                data = {}
            self._items = []
            self._playlist = []
            self._hays = {}
            self._container = data.get("container", self.__class__.__name__)
            self._module = data.get("module", self.__class__.__module__)
            self._method = data.get("method", _default_method)
            self._mediakwargs = data.get("mediakwargs", None)
            args = data.get("args", [])
            kwargs = data.get("kwargs", {})
            self._disp_container = self._container
            self._disp_module = self._module
            self._disp_method = self._method
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
            dispatchdata = "TinyXBMC is Dispatching\r\n"
            dispatchdata += "MODULE    : %s\r\n" % self._disp_module
            dispatchdata += "CONTAINER : %s\r\n" % self._disp_container
            dispatchdata += "METHOD    : %s\r\n" % self._disp_method
            dispatchdata += "ARGUMENTS : %s\r\n" % repr(args)
            dispatchdata += "KW ARGS   : %s\r\n" % repr(kwargs)
            dispatchdata += "MEDIA     : %s\r\n" % repr(self._mediakwargs)
            errorcol.msg = dispatchdata
            addon.log(dispatchdata)
            self._container.useragent = flare.USERAGENT
            self._container.httptimeout = const.HTTPTIMEOUT
            self._container.autoupdate = False
            with collector.LogException("TINYXBMC EXTENSION ERROR", None, ignore=True) as ext_errcoll:
                ext_errcoll.token = self._container.dropboxtoken
                self._container.init(*iargs, **ikwargs)
            self._method = getattr(self._container, self._disp_method)
            info = art = {}
            if self._mediakwargs:
                # parse info and art from cache
                info = self._mediakwargs.get("info") or {}
                art = self._mediakwargs.get("art") or {}
                # use script.trakt imdbid
                imdbid = info.get("imdbnumber", info.get("code"))
                if imdbid:
                    xbmcgui.Window(10000).setProperty('script.trakt.ids', json.dumps({u'imdb': imdbid}))
                else:
                    xbmcgui.Window(10000).clearProperty('script.trakt.ids')
            if self._container._mediakwargs:
                self._media_resolver(info, art, *args, **kwargs)
            else:
                self._method_dispatcher(*args, **kwargs)
            self._close()
            if PROFILE:
                profiler.disable()
                profiler.dump_stats("tinyxbmcprofile.txt")
                with open("cachegrind.out.tinyxbmc", "w") as f:
                    profiler.callgrind(f)

    def _media_resolver(self, info, art, *args, **kwargs):
        if self._mediakwargs.get("self"):
            it = iter(args)
        elif not inspect.isgeneratorfunction(self._method):
            addon.log("Provided method is not a generator")
            return
        else:
            it = self._method(*args, **kwargs)

        self.player = Player(silent=bool(self._mediakwargs.get("silent")),
                             canresolve=bool(self._mediakwargs.get("resolve")))
        with self.player:
            for u in tools.safeiter(it, self.player.iscanceled):
                # use only mediaurl type
                if not isinstance(u, mediaurl.BaseUrl):
                    try:
                        u = mediaurl.LinkUrl(u)
                    except Exception:
                        self.log("Skipping broken url: %s" % repr(u), 100)
                        continue
                if self.player.stream(u, info, art):
                    break
                else:
                    self.log("Skipping broken url: %s" % u, 100)
        self.player = None

    def _method_dispatcher(self, *args, **kwargs):
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
                if isfolder:
                    showinfo = self.item(19033)
                    item.context(showinfo, "builtin", "Action(Info)")
                    item.docontext()
                xbmcplugin.addDirectoryItem(self.syshandle, url, item.item, isfolder, itemlen)
        if self.emptycontainer or itemlen:
            xbmcplugin.endOfDirectory(self.syshandle, cacheToDisc=True)
        if self._container.autoupdate:
            d = self.item("Auto Update", method="_update")
            d.run(self._container.autoupdate)
        if cnttyp in const.CT_ALL:
            views = self.hay(const.OPTIONHAY).find(const.OPTION_VIEWS).data
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

    def log(self, msg, percent=0):
        if self.player:
            self.player.log(msg, percent)
        else:
            addon.log(msg)

    def _update(self, wait):
        xbmc.sleep(wait * 1000)
        refresh()

    def _close(self):
        for _, hay in self._hays.items():
            hay.close()
        self.onclose()
        dtime = (time.time() - self.__inittime) * 1000
        etime = (time.time() - _startt) * 1000
        addon.log("****** TinyXBMC is Dispatched ******")
        addon.log("INIT TIME      : %s ms" % self.__itime)
        addon.log("DISPATCH TIME  : %s ms" % dtime)
        addon.log("EXECUTION TIME : %s ms" % etime)
        addon.log("************************************")

    def _setview(self, ct):
        stack = self.hay(const.OPTIONHAY)
        data = stack.find(const.OPTION_VIEWS).data
        current = data.get(ct, {})
        spath = tools.getSkinDir()
        current[spath] = tools.getskinview()
        data[ct] = current
        stack.throw(const.OPTION_VIEWS, data)
        gui.notify(ct.upper(), "Default view is updated")

    def init(self, *args, **kwargs):
        pass

    def item(self, name="item", info=None, art=None, module=None, container=None, method=None,
             context_remove_old=False, media_silent=False, media_resolve=True):
        if not info:
            info = {}
        if not art:
            art = {}
        if isinstance(name, int):
            name = xbmcaddon.Addon().getLocalizedString(name) or xbmc.getLocalizedString(name)
        if not art.get("icon"):
            art["icon"] = const.DEFAULT_FOLDER
        if not art.get("thumb"):
            art["thumb"] = const.DEFAULT_FOLDER
        module = module or self._disp_module
        container = container or self._disp_container
        method = method or self._disp_method
        tinyitem = Item(name, info, art, self.sysaddon, module, container, method,
                        context_remove_old, media_silent, media_resolve, self)
        return tinyitem

    def index(self, *args, **kwargs):
        # item = self.item("Hello TinyXBMC")
        # item.dir()
        pass

    def ondispatch(self):
        pass

    def onclose(self):
        pass

    def hay(self, hayid, compress=0, serial="json", aid=""):
        if aid == "":
            aid = self.addon
        if hayid not in self._hays:
            h = hay.stack(hayid, serial, compress, aid=aid)
            self._hays[hayid] = h
        else:
            h = self._hays[hayid]
        return h

    def download(self, url, params=None, data=None, headers=None, timeout=None,
                 json=None, method="GET", referer=None, useragent=None, encoding="utf-8",
                 verify=None, stream=None, proxies=None, cache=10, text=True):

        timeout = timeout or self._container.httptimeout
        useragent = useragent or self._container.useragent
        ret = net.http(url, params, data, headers, timeout, json, method, referer,
                       useragent, encoding, verify, stream, proxies, cache, text)
        return ret


class Item:
    def __init__(self, name, info, art, addonid, module, container, method,
                 context_remove_old=False, media_silent=False, media_resolve=True, containerobj=None):
        item = xbmcgui.ListItem(label=name)
        for k, v in art.items():
            v, headers = net.fromkodiurl(v)
            art[k] = net.tokodiurl(v, headers, useragent=containerobj._container.useragent if containerobj else None)
        setArt(item, art)
        item.setInfo("video", info)
        self.name = name
        self.info = info
        self.art = art
        self.item = item
        self.addonid = addonid
        self.module = module
        self.container = container
        self.method = method
        self.contexts = []
        self.isfolder = False
        self.isself = False
        self.context_remove_old = context_remove_old
        self.media_silent = media_silent
        self.media_resolve = media_resolve
        self.containerobj = containerobj
        if containerobj and \
            self.addonid == containerobj.sysaddon and \
            self.module == containerobj._disp_module and \
            self.container == containerobj._disp_container and \
                self.method == containerobj._disp_method:
            self.isself = True

    def checkcontainer(self, container):
        pass

    def _dourl(self, ismedia, args, kwargs):
        data = {"module": self.module,
                "container": self.container,
                "method": self.method,
                "args": args,
                "kwargs": kwargs,
                }
        if ismedia:
            data["mediakwargs"] = {"info": self.info,
                                   "art": self.art,
                                   "self": bool(self.isself),
                                   "resolve": bool(self.media_resolve),
                                   "silent": bool(self.media_silent)}
        serial = parse.quote_plus(json.dumps(data, sort_keys=True))
        return '%s?%s' % (self.addonid, serial)

    def dourl(self, *args, **kwargs):
        return self._dourl(False, args, kwargs)

    def docontext(self):
        self.item.addContextMenuItems(self.contexts, self.context_remove_old)

    def _dir(self, ismedia, args, kwargs):
        url = self._dourl(ismedia, args, kwargs)
        self.docontext()
        if self.media_resolve:
            self.item.setProperty('IsPlayable', 'true')
        if self.containerobj:
            self.containerobj._items.append([url, self, self.isfolder])
        return url

    def dir(self, *args, **kwargs):
        #  item is added to container as a navigatable folder (isfolder=True)
        self.isfolder = True
        return self._dir(False, args, kwargs)

    def call(self, *args, **kwargs):
        #  item is added to container as a callable folder (isfolder=False)
        self.isfolder = False
        return self._dir(False, args, kwargs)

    def run(self, *args, **kwargs):
        #  item is not added to container but called on runtime
        url = self.dourl(*args, **kwargs)
        xbmc.executebuiltin('RunPlugin(%s)' % url)
        return url

    def redirect(self, *args, **kwargs):
        #  item is not added to container but directory is changed to another container
        #  on runtime
        url = self.dourl(*args, **kwargs)
        xbmc.executebuiltin('Container.Update(%s)' % url)
        return url

    def resolve(self, *args, **kwargs):
        return self._dir(True, args, kwargs)

    def context(self, sub, isdir, *args, **kwargs):
        # sub.item.addContextMenuItems(sub.contexts)  # nested fun :)
        if isdir == "builtin":
            self.contexts.append([sub.name, *args])
        else:
            url = sub.dourl(*args, **kwargs)
            if isdir:
                self.contexts.append([sub.name, 'Container.Update(%s)' % url])
            else:
                self.contexts.append([sub.name, 'RunPlugin(%s)' % url])


class Player(xbmc.Player):
    def __init__(self, silent=False, canresolve=True, timeout=10):
        self.silent = silent
        self.canresolve = canresolve
        self.playerinit = False
        self.started = False
        self.stopped = False
        self.dlg = None
        xbmc.Player.__init__(self)

    def __enter__(self):
        if not self.silent:
            self.dlg = xbmcgui.DialogProgressBG()
            self.dlg.create('Opening Media', 'Waiting for media')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def log(self, msg, percent=None):
        if self.dlg:
            self.dlg.update(percent or 0, msg)
        if percent is not None:
            msg = f"[{percent}%] {msg}"
        addon.log(msg)

    def close(self):
        if self.dlg:
            self.dlg.close()
            self.dlg = None

    def iscanceled(self):
        if self.dlg:
            return self.dlg.isFinished()
        return False

    def stream(self, url, info, art):
        self.playerinit = False
        self.started = False
        self.stopped = False
        u = url.kodiurl
        li = xbmcgui.ListItem(path=u)
        if url.inputstream:
            # utilize inputstream adaptive
            for pkey, pval in url.props().items():
                li.setProperty(pkey, pval)
        if self.iscanceled():
            return
        if self.canresolve:
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)
        else:
            if info:
                li.setInfo("video", info)
            if art:
                setArt(li, art)
            self.play(u, li)

        factor = 5
        timeout = True
        for i in range(url.timeout * factor):
            p = 100 * i / (url.timeout * factor)
            if self.dlg:
                self.dlg.update(int(p), u)
            xbmc.executebuiltin('Dialog.Close(12002,true)​')
            if self.iscanceled() or self.started or self.stopped:
                timeout = False
                break
            xbmc.sleep(int(1000 / factor))

        if self.started:
            xbmc.executebuiltin('Dialog.Close(all,true)​')
            addon.log("Started playing: %s" % u)
        else:
            if timeout:
                addon.log("Can't play media because playback did not start in %i seconds: %s" % (url.timeout, u))
            if self.iscanceled():
                addon.log("Can't play media because playback is cancelled by user: %s" % u)
            if self.stopped:
                addon.log("Can't play media because playback is stopped by the player: %s" % u)
            self.canresolve = False
            xbmc.executebuiltin('Dialog.Close(12002,true)​')
            if self.dlg:
                self.dlg.update(0, "Waiting for media")
            # inputstream.adaptive bug
            if self.playerinit:
                self.stop()

        self.log("", 100)
        return self.started

    def onPlayBackStarted(self):
        self.playerinit = True
        self.log("PlaybackStarted")
        if tools.kodiversion() < 18:
            self.started = True

    def onPlayBackEnded(self):
        self.log("PlaybackEnded")
        self.stopped = True

    def onPlayBackError(self):
        self.log("PlaybackError")
        self.stopped = True

    def onPlayBackStopped(self):
        self.log("PlaybacStopped")
        self.stopped = True

    def onAVStarted(self):
        self.log("AVStarted")
        self.started = True


def setArt(item, d):
    for k, v in d.items():
        v, headers = net.fromkodiurl(v)
        d[k] = net.tokodiurl(v, headers, pushnoverify=True, pushua=True, pushcookie=True)
    if LooseVersion(xbmcgui.__version__) >= LooseVersion("2.14.0"):  # @UndefinedVariable
        item.setArt(d)
    else:
        icon = d.get("icon", d.get("poster", d.get("thumb")))
        thumb = d.get("thumb", d.get("poster", d.get("icon")))
        if icon:
            item.setIconImage(icon)
        if thumb:
            item.setThumbnailImage(thumb)
    return item
