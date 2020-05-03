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
from tribler.defs import YES, NO, BLUE
from tribler import api
from tribler.ui.window import Torrent

import datetime


class navi(container.container):

    def index(self):
        self.item("Search Torrents", method="search").dir(False)
        self.item("Search Channels", method="search").dir(True)
        self.item("Subscribed Channels", method="channels").dir(True)
        self.item("Discovered Channels", method="channels").dir(False)
        self.item("Add Torrent", method="addtorrent").dir()
        self.item("Downloads", method="downloads").dir()

    def channels(self, subbed=False):
        self.handlechannels(api.channel.list(subbed))

    def channeltorrents(self, chanid, publickey, total, start=1, count=200):
        num, torrents = api.channel.get(chanid, publickey, start, count)
        last = len(torrents) + start
        if not len(torrents):
            torrents.extend(api.remote.query(channel_pk=publickey,
                                             timeout=None,
                                             max_results=min(count, total - num)))
        self.handletorrents(torrents)
        if total > last:
            self.item("Next", method="channeltorrents").dir(chanid,
                                                            publickey,
                                                            total,
                                                            last)

    def search(self, ischannel=False, txt_filter=None):
        if not txt_filter:
            conf, txt_filter = gui.keyboard("", "Search")
            if conf:
                txt_filter = "\"%s\"*" % txt_filter
                self.item("Redirect", method="search").redirect(ischannel, txt_filter)
        else:
            results = sorted(api.search.query(txt_filter),
                             key=lambda x: x.get("torrents") or x.get("num_seeders"),
                             reverse=True)
            metadata_type = "channel" if ischannel else "torrent"
            if not len(results):
                results = api.remote.query(txt_filter=txt_filter, metadata_type=metadata_type)
            if ischannel:
                self.handlechannels(results)
            else:
                self.handletorrents(results)
            self.item("Query GigaChannels", method="searchgiga").dir(txt_filter, metadata_type)

    def searchgiga(self, txt_filter, metadata_type):
        results = api.remote.query(txt_filter=txt_filter, metadata_type=metadata_type)
        if metadata_type == "torrent":
            self.handletorrents(results)
        else:
            self.handlechannels(results)
        self.item("Query GigaChannels", method="searchgiga").dir(txt_filter, metadata_type)

    def handletorrents(self, torrents):
        downloads = [x["infohash"] for x in api.download.list()]
        for torrent in torrents:
            updated = datetime.datetime.utcfromtimestamp(torrent["updated"])
            subbed = torrent.get("subscribed")
            if subbed is not None:
                continue
            infohash = torrent["infohash"]
            isdownload = infohash in downloads
            itemname = "%s%s %s%s %s%s - %s - U: %s" % (BLUE("SE: "),
                                                        torrent["num_seeders"],
                                                        BLUE("LE: "),
                                                        torrent["num_leechers"],
                                                        BLUE("DOWN: "),
                                                        YES if isdownload else NO,
                                                        torrent["name"],
                                                        BLUE(updated.strftime(("%d.%m.%Y %H:%M"))))
            item = self.item(itemname, method="downloadwindow")
            cntx_health = self.item("Check Health",
                                    module="tribler.ui.containers",
                                    container="common",
                                    method="trackerquery")
            item.context(cntx_health, False, infohash, torrent["name"])
            if not isdownload:
                cntx_download = self.item("Start Download",
                                          module="tribler.api.download",
                                          container="download",
                                          method="add")
                item.context(cntx_download, False,
                             api.makemagnet(infohash))
            item.call(infohash, isdownload)

    def handlechannels(self, channels):
        for channel in channels:
            subbed = channel.get("subscribed")
            if subbed is None:
                continue
            mining = channel.get("credit_mining")
            num, _ = api.channel.get(channel["id"], channel["public_key"], 0, 0, hide_xxx=0)
            torrents = channel["torrents"]
            if torrents and channel.get("state") not in ["Personal", "Complete"]:
                num_tor = torrents if num >= torrents else "%s/%s" % (num, torrents)
            else:
                num_tor = torrents
            itemname = "%s%s %s%s %s%s - %s" % (BLUE("SUB: "),
                                                YES if subbed else NO,
                                                BLUE("MINE: "),
                                                YES if mining else NO,
                                                BLUE("TOR: "),
                                                BLUE(num_tor),
                                                channel["name"])
            item = self.item(itemname, method="channeltorrents")
            cntx_sub = self.item("Unubscribe" if subbed else "Subscribe",
                                 module="tribler.api.metadata",
                                 container="metadata",
                                 method="subscribe")
            item.context(cntx_sub, False,
                         channel["id"],
                         channel["public_key"],
                         False if subbed else True)
            cntx_mine = self.item("Stop Mining" if mining else "Start Mining",
                                  module="tribler.api.settings",
                                  container="settings",
                                  method="setmining")
            item.context(cntx_mine, False,
                         channel["id"],
                         False if mining else True)
            item.dir(channel["id"], channel["public_key"], channel["torrents"])

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
        if not cat:
            for state in defs.dl_states_short:
                self.item(state.title(), method="downloads").dir(state)
            self.item("Credit Mining", method="downloads").dir("credit_mining")
            self.item("All", method="downloads").dir("all")
        else:
            for download in api.download.list():
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
                    d_item = self.item(itemname, method="downloadwindow")
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
                    d_item.call(ihash)

    def downloadwindow(self, infohash, hasdownload=None):
        import time
        t1 = time.time()
        window = Torrent(infohash, hasdownload)
        print time.time() - t1
        window.doModal()
        container.refresh()


navi()
