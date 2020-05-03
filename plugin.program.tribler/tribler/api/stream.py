'''
Created on 26 Mar 2020

@author: boogie
'''
from tinyxbmc import gui
from tinyxbmc import container

from tribler import defs

import common
from download import download
import time


class stream(container.container):
    def init(self, *args, **kwargs):
        self.playertimeout = 60 * 3

    @staticmethod
    def iterstreams(ihash, fileindex=None, info=None, art=None):
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
            for jdownload in common.call("GET", "downloads").get("downloads", []):
                if stop:
                    break
                if jdownload["infohash"] == ihash:
                    resp = common.call("GET", "downloads/%s/files" % ihash)
                    if lof is None:
                        lof = [x["name"] for x in resp["files"]]
                    if not len(lof):
                        stop = True
                    elif len(lof) == 1:
                        findex = 0
                    elif findex is None:
                        findex = gui.select("Select File", lof)
                    if int(findex) < 0:
                        stop = True
                    download.setstate(ihash, "resume")
                    download.setvodmode(ihash, True, findex)
                    if jdownload['vod_prebuffering_progress'] < 1 or jdownload['vod_header_progress'] < 1 or jdownload['vod_footer_progress'] < 1:
                        if not progress:
                            progress = gui.progress("Prebuffering")
                        if progress.iscanceled():
                            stop = True
                        print jdownload['vod_prebuffering_progress']
                        print 111111111111
                        progress.update(int(jdownload['vod_prebuffering_progress'] * 100),
                                        "%s: %s / %s" % (defs.dl_states[jdownload["status"]],
                                                         jdownload["total_down"],
                                                         jdownload["size"]),
                                        "Header Percent: %s%%" % int(jdownload['vod_header_progress'] * 100),
                                        "Footer Percent: %s%%" % int(jdownload['vod_footer_progress'] * 100),
                                        )
                        time.sleep(1)
                    else:
                        if progress:
                            progress.close()
                        info["path"] = lof[findex]
                        url = "%s/downloads/%s/stream/%s?apikey=%s" % (common.config.address,
                                                                       ihash,
                                                                       findex,
                                                                       common.config.get("http_api", "key"))
                        yield url, info, art
                        stop = True

    def testplayer(self, ihash, findex=0):
        url = "%s/downloads/%s/stream/%s?apikey=%s" % (common.config.address,
                                                       ihash,
                                                       findex,
                                                       common.config.get("http_api", "key"))
        yield url
