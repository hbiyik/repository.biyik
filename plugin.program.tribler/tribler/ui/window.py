'''
Created on 2 May 2020

@author: boogie
'''
import os
import threading
import pyxbmct
from pyxbmct.addonskin import Skin

from tribler import defs
from tribler.api.download import download
from tribler.api.settings import settings
from tribler.api.common import format_size
from tribler.ui.containers import common


estuary = Skin()
estuary.estuary = True
bgimg = os.path.join(estuary.images, 'AddonWindow', 'dialogheader.png')


class Torrent(pyxbmct.AddonDialogWindow):

    def __init__(self, infohash, hasdownload=None):
        super(Torrent, self).__init__("Download")
        self.basewidth = None
        self.isclosing = False
        self.infohash = infohash
        self.settings = settings.get()
        self.setGeometry(1200, 700, 27, 4)
        self.set_controls()
        self.autoNavigation()
        self.__state = None
        self.__hasmeta = False
        self.__hastrackers = False
        self.__hasdownload = hasdownload
        self.__hops = None
        self.__anonupload = None
        self.__total = 0
        self.__prebuff = 0
        self.__header = 0
        self.__footer = 0
        self.setWindowTitle(self.infohash)
        if self.hasdownload or self.hasdownload is None:
            self.updatewithdownload()
        self.applysettings()
        self.updatecontrols()
        if not self.hastrackers:
            threading.Thread(target=self.on_button_updatetrackers, args=(0,)).start()
        if not self.hasmeta:
            threading.Thread(target=self.on_button_querymetadata).start()

    def updatecontrols(self):
        start = stop = stream = peers = recheck = meta = False
        if self.hasmeta and (self.isstopped or not self.hasdownload):
            start = stream = True
        if not self.isstopped:
            stop = True
        if self.hasdownload:
            recheck = True
        if self.status in defs.dl_states_short["DOWNLOADING"] or self.status in defs.dl_states_short["SEEDING"]:
            peers = True
        if not self.hasmeta:
            meta = True
        self.button_start.setEnabled(start)
        self.button_stop.setEnabled(stop)
        self.button_stream.setEnabled(stream)
        self.button_recheck.setEnabled(recheck)
        self.button_peers.setEnabled(peers)
        self.button_querymeta.setEnabled(meta)

    @property
    def state(self):
        return self.__state

    @state.setter
    def state(self, value):
        self.__state = value
        self.updatecontrols()

    @property
    def isstopped(self):
        return self.state in defs.dl_states_short["STOPPED"]

    @property
    def hasmeta(self):
        return self.infohash is not None and self.__hasmeta

    @hasmeta.setter
    def hasmeta(self, value):
        self.__hasmeta = value
        self.updatecontrols()

    @property
    def hastrackers(self):
        return self.infohash is not None and self.__hastrackers

    @hastrackers.setter
    def hastrackers(self, value):
        self.__hastrackers = value

    @property
    def hasdownload(self):
        return self.infohash is not None and self.__hasdownload

    @hasdownload.setter
    def hasdownload(self, value):
        self.__hasdownload = value
        self.updatecontrols()

    @property
    def hops(self):
        return self.__hops

    @hops.setter
    def hops(self, value):
        if value == 1:
            self.on_download_1_hop()
        elif value == 2:
            self.on_download_2_hops()
        elif value == 3:
            self.on_download_3_hops()
        else:
            self.on_dowload_no_hops()

    @property
    def anonupload(self):
        return self.__anonupload

    @anonupload.setter
    def anonupload(self, value):
        if value:
            self.on_upload_enc()
        else:
            self.on_upload_noenc()

    @property
    def total(self):
        return self.__total

    @total.setter
    def total(self, value):
        self.setpercent(self.progress_total, value)
        self.__total = value

    @property
    def prebuff(self):
        return self.__prebuff

    @prebuff.setter
    def prebuff(self, value):
        self.setpercent(self.progress_prebuff, value)
        self.__prebuff = value

    @property
    def header(self):
        return self.__header

    @header.setter
    def header(self, value):
        self.setpercent(self.progress_header, value)
        self.__header = value

    @property
    def footer(self):
        return self.__footer

    @footer.setter
    def footer(self, value):
        self.setpercent(self.progress_footer, value)
        self.__footer = value

    def applysettings(self):
        if not self.hasdownload:
            self.hops = self.settings["settings"]["download_defaults"]["number_hops"]
            self.anonupload = self.settings["settings"]["download_defaults"]["safeseeding_enabled"]
        else:
            pass
            # TODO: handle download config

    def set_controls(self):
        self.placeControl(pyxbmct.Label('Status:'), 0, 0)
        self.status = pyxbmct.Label('')
        self.placeControl(self.status, 0, 1, 1, 3)

        self.placeControl(pyxbmct.Label('Seeders:'), 1, 0)
        self.seeders = pyxbmct.Label('')
        self.placeControl(self.seeders, 1, 1)

        self.placeControl(pyxbmct.Label('Peers:'), 1, 2)
        self.peers = pyxbmct.Label('')
        self.placeControl(self.peers, 1, 3)

        self.placeControl(pyxbmct.Label('Download Speed:'), 2, 0)
        self.speed_download = pyxbmct.Label('')
        self.placeControl(self.speed_download, 2, 1)

        self.placeControl(pyxbmct.Label('Downloaded:'), 2, 2)
        self.size_downloaded = pyxbmct.Label('')
        self.placeControl(self.size_downloaded, 2, 3)

        self.placeControl(pyxbmct.Label('Upload Speed:'), 3, 0)
        self.speed_upload = pyxbmct.Label('')
        self.placeControl(self.speed_upload, 3, 1)

        self.placeControl(pyxbmct.Label('Uploaded:'), 3, 2)
        self.size_uploaded = pyxbmct.Label('')
        self.placeControl(self.size_uploaded, 3, 3)

        self.placeControl(pyxbmct.Label('File List:'), 4, 0)
        self.totalfiles = pyxbmct.Label('')
        self.placeControl(self.totalfiles, 4, 1)
        self.placeControl(pyxbmct.Label('Total Size:'), 4, 2)
        self.totalsize = pyxbmct.Label('')
        self.placeControl(self.totalsize, 4, 3)
        self.placeControl(pyxbmct.Label('File List:'), 4, 0, 1, 4)
        self.file_list = pyxbmct.List()
        self.placeControl(self.file_list, 5, 0, 6, 4)

        self.placeControl(pyxbmct.Label('Trackers:'), 9, 0, 1, 4)
        self.tracker_list = pyxbmct.List()
        self.placeControl(self.tracker_list, 10, 0, 5, 4)

        self.placeControl(pyxbmct.Label('Download Anonymity:'), 13, 0, 1, 4)
        self.download_no_hops = pyxbmct.RadioButton("Direct")
        self.download_1_hop = pyxbmct.RadioButton("1 Hop")
        self.download_2_hops = pyxbmct.RadioButton("2 Hops")
        self.download_3_hops = pyxbmct.RadioButton("3 Hops")
        self.placeControl(self.download_no_hops, 14, 0, 2)
        self.placeControl(self.download_1_hop, 14, 1, 2)
        self.placeControl(self.download_2_hops, 14, 2, 2)
        self.placeControl(self.download_3_hops, 14, 3, 2)

        self.placeControl(pyxbmct.Label('Upload Anonymity:'), 16, 0, 1, 4)
        self.upload_noenc = pyxbmct.RadioButton("Direct")
        self.upload_enc = pyxbmct.RadioButton("Encrypted Proxy")
        self.placeControl(self.upload_noenc, 17, 0, 2, 2)
        self.placeControl(self.upload_enc, 17, 2, 2, 2)

        self.progress_total_label = pyxbmct.Label('Total Progress:')
        self.placeControl(self.progress_total_label, 19, 0)
        self.progress_total = pyxbmct.Image(bgimg)
        self.placeControl(self.progress_total, 19, 1, 1, 3)

        self.progress_prebuff_label = pyxbmct.Label('Prebuffering Progress:')
        self.placeControl(self.progress_prebuff_label, 20, 0)
        self.progress_prebuff = pyxbmct.Image(bgimg)
        self.placeControl(self.progress_prebuff, 20, 1, 1, 3)

        self.placeControl(pyxbmct.Label('Header Progress:'), 21, 0)
        self.progress_header = pyxbmct.Image(bgimg)
        self.placeControl(self.progress_header, 21, 1, 1, 3)

        self.placeControl(pyxbmct.Label('Footer Progress:'), 22, 0)
        self.progress_footer = pyxbmct.Image(bgimg)
        self.placeControl(self.progress_footer, 22, 1, 1, 3)

        self.button_recheck = pyxbmct.Button("Force Recheck")
        self.button_peers = pyxbmct.Button("Peers")
        self.button_updatetrackers = pyxbmct.Button("Update Trackers")
        self.button_querymeta = pyxbmct.Button("Query Metadata")
        self.placeControl(self.button_recheck, 24, 0, 2)
        self.placeControl(self.button_peers, 24, 1, 2)
        self.placeControl(self.button_updatetrackers, 24, 2, 2)
        self.placeControl(self.button_querymeta, 24, 3, 2)

        self.button_start = pyxbmct.Button("Start")
        self.button_stream = pyxbmct.Button("Stream")
        self.button_stop = pyxbmct.Button("Stop")
        self.button_close = pyxbmct.Button("Close")
        self.placeControl(self.button_start, 26, 0, 2)
        self.placeControl(self.button_stop, 26, 1, 2)
        self.placeControl(self.button_stream, 26, 2, 2)
        self.placeControl(self.button_close, 26, 3, 2)

        self.basewidth = self.progress_total.getWidth()

        self.connect(self.download_no_hops, self.on_dowload_no_hops)
        self.connect(self.download_1_hop, self.on_download_1_hop)
        self.connect(self.download_2_hops, self.on_download_2_hops)
        self.connect(self.download_3_hops, self.on_download_3_hops)

        self.connect(self.upload_enc, self.on_upload_enc)
        self.connect(self.upload_noenc, self.on_upload_noenc)

        self.connect(self.button_recheck, self.on_button_recheck)
        self.connect(self.button_peers, self.on_button_peers)
        self.connect(self.button_updatetrackers, self.on_button_updatetrackers)
        self.connect(self.button_querymeta, self.on_button_querymetadata)

        self.connect(self.button_start, self.on_button_start)
        self.connect(self.button_stream, self.on_button_stream)
        self.connect(self.button_stop, self.on_button_stop)
        self.connect(self.button_close, self.close)
        self.connect(pyxbmct.ACTION_NAV_BACK, self.close)

        self.setpercent(self.progress_total, 0)
        self.setpercent(self.progress_prebuff, 0)
        self.setpercent(self.progress_header, 0)
        self.setpercent(self.progress_footer, 0)

    def setpercent(self, progress, percent):
        progress.setWidth(min(max(int(self.basewidth * percent), 1), self.basewidth))

    def getpercent(self, progress):
        return float(progress.getWidth()) / self.basewidth

    def on_dowload_no_hops(self):
        self.download_no_hops.setSelected(True)
        self.download_1_hop.setSelected(False)
        self.download_2_hops.setSelected(False)
        self.download_3_hops.setSelected(False)
        self.__hops = None

    def on_download_1_hop(self):
        self.download_no_hops.setSelected(False)
        self.download_1_hop.setSelected(True)
        self.download_2_hops.setSelected(False)
        self.download_3_hops.setSelected(False)
        self.__hops = 1

    def on_download_2_hops(self):
        self.download_no_hops.setSelected(False)
        self.download_1_hop.setSelected(False)
        self.download_2_hops.setSelected(True)
        self.download_3_hops.setSelected(False)
        self.__hops = 2

    def on_download_3_hops(self):
        self.download_no_hops.setSelected(False)
        self.download_1_hop.setSelected(False)
        self.download_2_hops.setSelected(False)
        self.download_3_hops.setSelected(True)
        self.__hops = 3

    def on_upload_enc(self):
        self.upload_enc.setSelected(True)
        self.upload_noenc.setSelected(False)
        self.__anonupload = True

    def on_upload_noenc(self):
        self.upload_enc.setSelected(False)
        self.upload_noenc.setSelected(True)
        self.__anonupload = False

    def on_button_start(self):
        pass

    def on_button_stop(self):
        pass

    def on_button_stream(self):
        pass

    def on_button_recheck(self):
        pass

    def on_button_peers(self):
        pass

    def on_button_querymetadata(self):
        if self.infohash:
            self.button_querymeta.setEnabled(False)
            tinfo = common.metadataquery(None, self.infohash, self.hops, progress_callback=Progress("Metadata Update",
                                                                                                    self,
                                                                                                    self.progress_prebuff_label,
                                                                                                    self.progress_prebuff))
            tinfo = tinfo.get("info")
            files = []
            if tinfo:
                self.setWindowTitle(tinfo.get("name", self.infohash))
                lof = tinfo.get("files")
                if lof:
                    files = [{"name": os.path.join(*x["path"]), "size":x["length"]} for x in lof]
                else:
                    files = [{"name": tinfo["name"], "size": tinfo["length"]}]
            self.updatefiles(files)

    def updatefiles(self, files):
        if files:
            self.file_list.reset()
            self.totalfiles.setLabel("%s Files" % len(files))
            totalsize = 0
            for subfile in files:
                totalsize += subfile["size"]
                self.file_list.addItem("%s (%s)" % (subfile["name"],
                                                    format_size(subfile["size"])))
            self.totalsize.setLabel(format_size(totalsize))
            self.hasmeta = True
        else:
            self.hasmeta = False

    def on_button_updatetrackers(self, refresh=1):
        if self.infohash:
            self.button_updatetrackers.setEnabled(False)
            health = common.trackerquery(self.infohash, None, refresh, progress_callback=Progress("Tracker Update",
                                                                                                  self,
                                                                                                  self.progress_total_label,
                                                                                                  self.progress_total))
            self.button_updatetrackers.setEnabled(True)
            self.updatetrackers(health.get("health", {}).items())

    def updatetrackers(self, trackers):
        self.tracker_list.reset()
        seeders = 0
        peers = 0
        for tracker, trackerinfo in trackers:
            if "error" in trackerinfo:
                sp = "E:%s" % trackerinfo["error"]
            else:
                seeder = trackerinfo.get("seeders", 0)
                peer = trackerinfo.get("leechers", 0)
                sp = "S:%sP:%s" % (seeder, peer)
                seeders += seeder
                peers += peer
            self.tracker_list.addItem("%s %s" % (tracker, sp))
        self.seeders.setLabel(str(seeders))
        self.peers.setLabel(str(peers))
        self.hastrackers = bool(seeders + peers)

    def close(self):
        self.isclosing = True
        super(Torrent, self).close()

    def updatewithdownload(self):
        hasdownload = False
        if self.infohash:
            for dload in download.list(get_files=1):
                if dload["infohash"] == self.infohash:
                    hasdownload = True
                    self.hasmeta = bool(dload["files"])
                    self.updatefiles(dload["files"])
                    self.hastrackers = bool(dload["trackers"])
                    self.updatetrackers([(x["url"], {"leechers": x["peers"]}) for x in dload["trackers"]])
                    self.setWindowTitle(dload["name"])
                    self.speed_download.setLabel(format_size(dload["speed_down"]) + "/s")
                    self.speed_upload.setLabel(format_size(dload["speed_up"]) + "/s")
                    self.state = dload["status"]
                    self.status.setLabel(defs.dl_states[self.state])
                    self.totalsize.setLabel(format_size(dload["size"]))
                    self.peers.setLabel(str(dload["num_peers"]))
                    self.seeders.setLabel(str(dload["num_seeds"]))
                    self.size_downloaded.setLabel(format_size(dload["total_down"]))
                    self.size_uploaded.setLabel(format_size(dload["total_up"]))
                    self.hops = dload["hops"]
                    self.anonupload = dload["safe_seeding"]
                    self.total = dload["progress"]
                    self.prebuff = dload["vod_prebuffering_progress"]
                    self.header = dload["vod_header_progress"]
                    self.footer = dload["vod_footer_progress"]
        self.hasdownload = hasdownload


class Progress():
    def __init__(self, label, context, caption, progress):
        self.context = context
        self.caption = caption
        self.progress = progress
        self.prepercent = context.getpercent(context.progress_total)
        self.prelabel = caption.getLabel()
        self.caption.setLabel(label)

    def update(self, value):
        self.context.setpercent(self.progress, float(value) / 100)

    def close(self):
        self.context.setpercent(self.progress, self.prepercent)
        self.caption.setLabel(self.prelabel)

    def isFinished(self):
        return self.context.isclosing
