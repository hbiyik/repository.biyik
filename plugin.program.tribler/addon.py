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
from tinyxbmc import net

from tribler import defs

import ConfigParser
import os
import time


class navi(container.container):

    def init(self):
        # currently only find already running linux app
        # in future call a binary and dispatch cross platform
        self.config = None
        base_dir = os.path.expanduser("~/.Tribler")
        for d in os.listdir(base_dir):
            subdir = os.path.join(base_dir, d)
            if os.path.isdir(subdir):
                for subfile in os.listdir(subdir):
                    if subfile == "triblerd.conf":
                        self.config = ConfigParser.ConfigParser()
                        self.config.read(os.path.join(subdir, subfile))
                        break
                if self.config:
                    break
        if not self.config:
            gui.ok("ERROR", "Can not find Tribler installation")
            return

    def api(self, method, endpoint, **data):
        url = "http://localhost:%s/%s" % (self.config.get("http_api", "port"), endpoint)
        headers = {"X-Api-Key": self.config.get("http_api", "key")}
        resp = net.http(url, headers=headers, json=data, method=method)
        if "error" in resp:
            if isinstance(resp["error"], dict):
                title = resp["error"].get("code", "ERROR")
                msg = resp["error"].get("message", "Unknown Error")
            else:
                title = "ERROR"
                msg = str(resp["error"])
            gui.ok(title, msg)
        else:
            return resp

    def index(self):
        self.item("Add Torrent", method="addtorrent").dir()
        self.item("Downloads", method="downloads").dir()

    def addtorrent(self):
        self.item("Add Torrent From Remote Magnet or URL", method="addtorrent_url").call()
        self.item("Add Torrent From Local Torrent File or Mdblob DB", method="addtorrent_file").call()

    def addtorrent_api(self, uri):
        resp = self.api("PUT", "downloads", uri=uri,
                        anon_hops=int(self.config.get("download_defaults", "number_hops")),
                        safe_seeding=1 if self.config.get("download_defaults", "safeseeding_enabled") else 0)
        if resp:
            gui.ok("Torrent Added", resp.get("infohash", ""))

    def addtorrent_file(self):
        fpath = gui.browse(1, "Select Torrent")
        if not fpath == "":
            fpath = u"file://" + unicode(fpath.decode("utf8"))
            self.addtorrent_api(fpath)

    def addtorrent_url(self):
        conf, txt = gui.keyboard("", "Magnet Link")
        if conf:
            txt = unicode(txt.decode("utf8"))
            self.addtorrent_api(txt)

    def downloads(self, cat=None):
        downloads = self.api("GET", "downloads")
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
                    d_item = self.item("%s%% %s | %s (D: %s U:%s)" % (int(download["progress"] * 100),
                                                                      "STREAMING" if download["vod_mode"] else defs.dl_states[download["status"]],
                                                                      download["name"],
                                                                      download["speed_down"],
                                                                      download["speed_up"]
                                                                      ), method="testplayer")
                    ctxs = []
                    ihash = download["infohash"]
                    if download["status"] in defs.dl_states_short["STOPPED"]:
                        ctxs.append((self.item("Start", method="download_state"), "resume"))
                    else:
                        ctxs.append((self.item("Stop", method="download_state"), "stop"))
                    if download.get("vod_mode"):
                        ctxs.append((self.item("Stop Streaming", method="download_setvodmode"), False))
                    ctxs.append((self.item("Recheck", method="download_state"), "recheck"))
                    ctxs.append((self.item("Delete", method="download_delete"), None))
                    for ctx, state in ctxs:
                        d_item.context(ctx, False, ihash, state)
                    d_item.resolve(ihash)

    def download_state(self, ihash, state):
        if state == "stop":
            self.download_setvodmode(ihash, False)
        resp = self.api("PATCH", "downloads/%s" % ihash, state=state)
        if resp.get("modified"):
            container.refresh()

    def download_setvodmode(self, ihash, vod_mode, fileindex=None):
        if vod_mode:
            resp = self.api("PATCH", "downloads/%s" % ihash, vod_mode=True, fileindex=fileindex)
        else:
            resp = self.api("PATCH", "downloads/%s" % ihash, vod_mode=False)
        if resp.get("modified"):
            container.refresh()
        return resp

    def iterstreams(self, ihash, fileindex=None, info=None, art=None):
        self.playertimeout = 60 * 3
        progress = None
        findex = None
        lof = None
        stop = False
        if not info:
            info = {}
        if fileindex:
            findex = fileindex
        while True:
            if stop:
                break
            for download in self.api("GET", "downloads").get("downloads", []):
                if stop:
                    break
                if download["infohash"] == ihash:
                    resp = self.api("GET", "downloads/%s/files" % ihash)
                    if lof is None:
                        lof = [x["name"] for x in resp["files"] if x.get("included")]
                    if not len(lof):
                        stop = True
                    elif len(lof) == 1:
                        findex = 0
                    elif findex is not None:
                        findex = gui.select("Select File", lof)
                    if int(findex) < 0:
                        stop = True
                    self.download_state(ihash, "resume")
                    if not download['vod_mode']:
                        self.download_setvodmode(ihash, True, findex)
                    if download['vod_prebuffering_progress'] < 0.1:
                        if not progress:
                            progress = gui.progress("Prebuffering")
                        if progress.iscanceled():
                            stop = True
                        progress.update(int(download['vod_prebuffering_progress'] * 100),
                                        "%s: %s / %s" % (defs.dl_states[download["status"]],
                                                         download["total_down"],
                                                         download["size"]),
                                        "Total Percent: %s" % int(download['vod_prebuffering_progress'] * 100),
                                        "Consecutive Percent: %s" % int(download['vod_prebuffering_progress_consec'] * 100),
                                        )
                        time.sleep(1)
                    else:
                        if progress:
                            progress.close()
                        info["path"] = lof[findex]
                        url = "http://localhost:%s/downloads/%s/stream/%s?apikey=%s" % (self.config.get("http_api", "port"),
                                                                                        ihash,
                                                                                        findex,
                                                                                        self.config.get("http_api", "key"))
                        yield url, info, art
                        stop = True

    def testplayer(self, ihash, findex=0):
        url = "http://localhost:%s/downloads/%s/stream/%s?apikey=%s" % (self.config.get("http_api", "port"),
                                                                        ihash,
                                                                        findex,
                                                                        self.config.get("http_api", "key"))
        yield url

    def download_delete(self, ihash, remove_data=None):
        txt = "Are you sure you want to remove the torrent?"
        if remove_data is None:
            remove_data = gui.yesno("Remove Files", "Do you want to completely remove the stored files from the file system as well?")
            txt += " This will also remove the stored files!"
        confirm = gui.yesno("Delete Torrent", txt)
        if confirm:
            resp = self.api("DELETE", "downloads/%s" % ihash, remove_data=remove_data)
            if resp and resp.get("removed"):
                txt = "Trorent"
                if remove_data:
                    txt += " + stored data"
                txt += " has been removed."
                gui.ok("Removed", txt)
                container.refresh()


navi()
