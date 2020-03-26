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
from tinyxbmc import container
from tinyxbmc import gui

from tribler import defs
from tribler import api


class navi(container.container):

    def index(self):
        self.item("Search", method="search").dir()
        self.item("Add Torrent", method="addtorrent").dir()
        self.item("Downloads", method="downloads").dir()

    def search(self, txt_filter=None):
        if not txt_filter:
            conf, txt_filter = gui.keyboard("", "Search")
            if conf:
                self.item("Redirect", method="search").redirect(txt_filter)
        else:
            resp = api.search.query(txt_filter)
            if resp:
                for result in sorted(resp.get("results", []), key=lambda i: i.get("subscribed"), reverse=True):
                    subbed = result.get("subscribed")
                    if subbed is None:
                        prefix = "S%s L%s: " % (result["num_seeders"], result["num_leechers"])
                    elif subbed:
                        prefix = "SUB CH: "
                    else:
                        prefix = "CH: "
                    itemname = prefix + result["name"]
                    self.item(itemname).call()

    def addtorrent(self):
        self.item("Add Torrent From Remote Magnet or URL", method="addtorrent_url").call()
        self.item("Add Torrent From Local Torrent File or Mdblob DB", method="addtorrent_file").call()

    def addtorrent_file(self):
        fpath = gui.browse(1, "Select Torrent")
        if not fpath == "":
            fpath = u"file://" + unicode(fpath.decode("utf8"))
            api.download.add(fpath)

    def addtorrent_url(self):
        conf, txt = gui.keyboard("", "Magnet Link")
        if conf:
            txt = unicode(txt.decode("utf8"))
            api.download.add(txt)

    def downloads(self, cat=None):
        downloads = api.call("GET", "downloads")
        if not cat:
            for state in defs.dl_states_short:
                self.item(state.title(), method="downloads").dir(state)
            self.item("Credit Mining", method="downloads").dir("credit_mining")
            self.item("All", method="downloads").dir("all")
        else:
            for download in downloads.get("downloads", []):
                if cat == "credit_mining" and not download.get("credit_mining"):
                    continue
                if cat not in ["all", "credit_mining"] and download.get("credit_mining"):
                    continue
                elif cat not in ["all", "credit_mining"] and not download["status"] in defs.dl_states_short[cat]:
                    continue
                else:
                    itemname = "%s%% %s | %s (D: %s U:%s)" % (int(download["progress"] * 100),
                                                              "STREAMING" if download["vod_mode"] else defs.dl_states[download["status"]],
                                                              download["name"],
                                                              download["speed_down"],
                                                              download["speed_up"])
                    d_item = self.item(itemname,
                                       module="tribler.api.stream",
                                       container="stream",
                                       method="testplayer")
                    ctxs = []
                    ihash = download["infohash"]
                    if download["status"] in defs.dl_states_short["STOPPED"]:
                        ctxs.append((self.item("Start",
                                               module="tribler.api.download",
                                               container="download",
                                               method="setstate"), "resume"))
                    else:
                        ctxs.append((self.item("Stop",
                                               module="tribler.api.download",
                                               container="download",
                                               method="setstate"), "stop"))
                    if download.get("vod_mode"):
                        ctxs.append((self.item("Stop Streaming",
                                               module="tribler.api.download",
                                               container="download",
                                               method="setvodmode"), False))
                    ctxs.append((self.item("Recheck",
                                           module="tribler.api.download",
                                           container="download",
                                           method="setstate"), "recheck"))
                    ctxs.append((self.item("Delete",
                                           module="tribler.api.download",
                                           container="download", method="delete"), None))
                    for ctx, state in ctxs:
                        d_item.context(ctx, False, ihash, state)
                    d_item.resolve(ihash)


navi()
