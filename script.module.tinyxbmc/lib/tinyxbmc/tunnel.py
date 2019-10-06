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
import urlparse
import traceback

from tinyxbmc import hay
from tinyxbmc import const
from tinyxbmc import extension
from tinyxbmc import tools
from tinyxbmc import gui


class tunnels():
    def __init__(self, url, stack=None):
        self.netloc = urlparse.urlparse(url).netloc
        self.shouldclose = False
        self.isclosed = False
        self.write = False
        if not stack:
            self.shouldclose = True
            stack = hay.stack(const.TUNCACHEHAY, common=True)
        self.stack = stack
        self.cached = self.stack.find(self.netloc).data
        print self.cached
        self.prehttp = []
        self.prehttps = []
        self.exts = extension.getplugins(const.TUNNELEXT)
        self.__gen = self.generator()
        self.progress = None

    def update(self, *args, **kwargs):
        if not self.progress:
            self.progress = gui.progress("Proxy for: %s" % self.netloc)
        self.progress.update(*args, **kwargs)

    def iscanceled(self):
        if not self.progress:
            return False
        else:
            return self.progress.iscanceled()

    def generator(self):
        for _, cache in self.cached.copy().iteritems():
            if self.iscanceled():
                break
            print "Open Cached tunnels for %s: %s" % (self.netloc, repr(cache))
            # self.update(100, "Cached Tunnel", cache.get("http", ""), cache.get("https",""))
            yield cache  # try cached first
        for tun in self.exts:
            try:
                it = tun().gettunnels()
                if self.iscanceled():
                    break
            except Exception:
                print traceback.format_exc()
                continue
            for ret in tools.safeiter(it):
                if self.iscanceled():
                    break
                if self._check(ret):
                    print "Extensioned tunnel %s: %s" % (self.netloc, repr(ret))
                    http, https = ret
                    if http in self.prehttp or https in self.prehttps:
                        continue
                    else:
                        self.prehttp.append(http)
                        self.prehttps.append(https)
                    self.update(100, "Trying New Tunnel", http, https)
                    tunneld = {"http": http, "https": https}
                    yield tunneld  # then try extensions

    def __next__(self):
        return self.__gen.next()

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __exit__(self, *args, **kwargs):
        self.close()

    def _id(self, tunnel):
        return "%s|%s" % (tunnel.get("http", ""),
                          tunnel.get("https", ""))

    def _check(self, tunnel):
        if isinstance(tunnel, (tuple, list)) and len(tunnel) == 2:
            return tunnel

    def fail(self, tunnel):
        if tunnel:
            print "Failed tunnel %s: %s" % (self.netloc, repr(tunnel))
            tid = self._id(tunnel)
            if tid in self.cached:
                self.cached.pop(tid)
                self.write = True

    def success(self, tunnel):
        if tunnel:
            print "Succesfull tunnel %s: %s" % (self.netloc, repr(tunnel))
            tid = self._id(tunnel)
            if tid not in self.cached:
                self.cached[tid] = tunnel
                self.write = True

    def close(self):
        if not self.isclosed:
            if self.progress:
                self.progress.close()
            print "Save cached tunnels %s: %s" % (self.netloc, repr(self.cached))
            if self.write:
                self.stack.throw(self.netloc, self.cached)
                self.write = False
            if self.shouldclose:
                print "Closing tunnel hay"
                self.stack.close()
                self.shouldclose = False
            self.isclosed = True


class fallback():
    def __init__(self, *args):
        self.proxies = iter(args)

    def __next__(self):
        return self.proxies.next()

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def fail(self, *args, **kwargs):
        pass

    def success(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass
