'''
Created on 2 May 2020

@author: boogie
'''
import os
import time
import threading
import pyxbmct
from pyxbmct.addonskin import Skin

from tribler import defs
from tribler.api.common import makemagnet
from tribler.api.download import download
from tribler.api.settings import settings
from tribler.api.ipv8 import ipv8
from tribler.api.common import format_size, config
from tribler.ui import containers

from tinyxbmc import gui


estuary = Skin()
estuary.estuary = True
bgimg = os.path.join(estuary.images, 'AddonWindow', 'dialogheader.png')


def lockelements(*elements):
    def wrap(f):
        def invoke_func(self, *args, **kwargs):
            for element in elements:
                getattr(self, element).setEnabled(False)
            ret = f(self, *args, **kwargs)
            for element in elements:
                getattr(self, element).setEnabled(True)
            return ret

        return invoke_func
    return wrap


class TorrentWindow(pyxbmct.AddonDialogWindow):

    def __init__(self, infohash, uri=None, hasdownload=None):
        super(TorrentWindow, self).__init__()
        self.basewidth = None
        self.infohash = infohash
        self.isclosing = False
        self.uri = makemagnet(self.infohash) if self.infohash and not uri else uri
        self.settings = None
        self.setGeometry(1200, 700, 29, 4)
        self.set_controls()
        self.autoNavigation()
        self.streamurl = None
        self.streamname = None
        self.__hops = None
        self.__anonupload = None
        self.__circuits = []
        self.__triblertunnelcommunity = []
        self.__dhtdiscoverycommunity = []
        self.__discoverycommunity = []
        self.__state = None
        self.__hasmeta = False
        self.__hastrackers = None
        self.__hasdownload = hasdownload
        self.__total = 0
        self.__prebuff = 0
        self.__header = 0
        self.__footer = 0
        self.anonimitylock = False
        self.vodmode = False
        self.fileindex = 0
        self.setWindowTitle(self.infohash)
        if self.hasdownload or self.hasdownload is None:
            self.updatewithdownload()
        if self.vodmode:
            self.on_button_stream()
        self.applysettings()
        self.updatecontrols()
        if not self.hasmeta:
            threading.Thread(target=self.on_button_querymetadata).start()
        threading.Thread(target=self.updatethread).start()
        self.autofocus()

    @property
    def circuits(self):
        return self.__circuits

    @circuits.setter
    def circuits(self, value):
        self.__circuits = value
        if self.hops or self.anonupload:
            num = 0
            for circuit in self.circuits:
                if circuit["actual_hops"] == self.hops and circuit["type"] == "DATA" and circuit["state"] == "READY":
                    num += 1
        else:
            num = "-"
        self.circuits_label.setLabel("Circuits: %s/%s" % (num, len(self.circuits)))

    @property
    def triblertunnelcommunity(self):
        return self.__triblertunnelcommunity

    @triblertunnelcommunity.setter
    def triblertunnelcommunity(self, value):
        self.__triblertunnelcommunity = value
        self.tunnelc_label.setLabel("Tunnel Community: %s" % len(self.triblertunnelcommunity))

    @property
    def dhtdiscoverycommunity(self):
        return self.__dhtdiscoverycommunity

    @dhtdiscoverycommunity.setter
    def dhtdiscoverycommunity(self, value):
        self.__dhtdiscoverycommunity = value
        self.dhtc_label.setLabel("DHT Community: %s" % len(self.dhtdiscoverycommunity))

    @property
    def discoverycommunity(self):
        return self.__discoverycommunity

    @discoverycommunity.setter
    def discoverycommunity(self, value):
        self.__discoverycommunity = value
        self.discoverc_label.setLabel("Discovery Community: %s" % len(self.discoverycommunity))

    @property
    def hops(self):
        return self.__hops

    @hops.setter
    @lockelements("download_no_hops", "download_1_hop", "download_2_hops", "download_3_hops")
    def hops(self, value):
        self.anonimitylock = True
        onehop = twohops = threehops = nohops = False
        if value == 1:
            onehop = True
        elif value == 2:
            twohops = True
        elif value == 3:
            threehops = True
        else:
            value = 0
            nohops = True
        if self.hops != value and self.hasdownload:
            download.sethops(self.infohash, value)
        self.__hops = value
        self.anonupload = self.anonupload
        self.download_no_hops.setSelected(nohops)
        self.download_1_hop.setSelected(onehop)
        self.download_2_hops.setSelected(twohops)
        self.download_3_hops.setSelected(threehops)
        self.anonimitylock = False

    @property
    def anonupload(self):
        return self.hops > 0 or self.__anonupload

    @anonupload.setter
    def anonupload(self, value):
        self.anonimitylock = True
        self.upload_enc.setEnabled(False)
        self.upload_noenc.setEnabled(False)
        value = bool(value)
        if self.hops:
            value = True
        elif self.hasdownload:
            for dload in download.list(get_files=1):
                if dload["infohash"] == self.infohash:
                    value = dload["safe_seeding"]
                    break
        self.upload_enc.setSelected(value)
        self.upload_noenc.setSelected(not value)
        self.__anonupload = value
        if not self.hops:
            self.upload_enc.setEnabled(True)
            self.upload_noenc.setEnabled(True)
            self.upload_label.setEnabled(True)
        else:
            self.upload_enc.setEnabled(False)
            self.upload_noenc.setEnabled(False)
            self.upload_label.setEnabled(False)
        self.anonimitylock = False

    def autofocus(self):
        for control in (self.button_stream, self.button_start, self.button_stop, self.button_close):
            if control.isEnabled():
                self.setFocus(control)
                break

    def updatethread(self):
        while not self.isclosing:
            if self.hasmeta and self.hastrackers is None:
                threading.Thread(target=self.on_button_updatetrackers).start()
            if self.hasdownload:
                self.updatewithdownload()
            if self.vodmode and self.prebuff == 1 and self.header == 1 and self.footer == 1:
                self.streamurl = "%s/downloads/%s/stream/%s?apikey=%s" % (config.address,
                                                                          self.infohash,
                                                                          self.fileindex,
                                                                          config.get("http_api", "key"))
                self.streamname = download.files(self.infohash)[self.fileindex]["name"]
                self.close()
            circuits = ipv8.circuits()
            overlays = ipv8.overlays()
            if circuits:
                self.circuits = circuits.get("circuits", [])
            if overlays:
                for overlay in overlays.get("overlays", []):
                    if overlay["overlay_name"] in ["DiscoveryCommunity", "DHTDiscoveryCommunity", "TriblerTunnelCommunity"]:
                        setattr(self, overlay["overlay_name"].lower(), overlay["peers"])
            time.sleep(defs.TORRENT_UPDATE_INTERVAL)

    def updatecontrols(self):
        start = stop = stream = peers = recheck = meta = False
        if self.hasmeta:
            stream = True
        if self.hasmeta and (self.isstopped or not self.hasdownload):
            start = True
        if self.hasdownload and not self.isstopped:
            stop = True
        if self.hasdownload and self.state not in ["DLSTATUS_ALLOCATING_DISKSPACE", "DLSTATUS_WAITING4HASHCHECK", "DLSTATUS_HASHCHECKING"]:
            recheck = True
        if self.state in defs.dl_states_short["DOWNLOADING"] or defs.dl_states_short["SEEDING"]:
            peers = True
        if not self.hasmeta:
            meta = True
        self.button_start.setEnabled(start)
        self.button_stop.setEnabled(stop)
        self.button_stream.setEnabled(stream)
        self.button_recheck.setEnabled(recheck)
        self.button_peers.setEnabled(peers)
        self.button_querymeta.setEnabled(meta)
        if self.vodmode:
            self.button_stream.setLabel("Stop Streaming")
        else:
            self.button_stream.setLabel("Start Streaming")

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
            self.settings = settings.get()
            self.hops = self.settings["settings"]["download_defaults"]["number_hops"]
            self.anonupload = self.settings["settings"]["download_defaults"]["safeseeding_enabled"]

    def set_controls(self):
        row = 0  # 0
        self.placeControl(pyxbmct.Label('Status:'), row, 0)
        self.status = pyxbmct.Label('NOT IN DOWNLOADS')
        self.placeControl(self.status, row, 1)

        row += 1  # 1
        self.placeControl(pyxbmct.Label('Seeders:'), row, 0)
        self.seeders = pyxbmct.Label('')
        self.placeControl(self.seeders, row, 1)
        self.placeControl(pyxbmct.Label('Peers:'), row, 2)
        self.peers = pyxbmct.Label('')
        self.placeControl(self.peers, row, 3)

        row += 1  # 2
        self.placeControl(pyxbmct.Label('Download Speed:'), row, 0)
        self.speed_download = pyxbmct.Label('')
        self.placeControl(self.speed_download, row, 1)
        self.placeControl(pyxbmct.Label('Downloaded:'), row, 2)
        self.size_downloaded = pyxbmct.Label('')
        self.placeControl(self.size_downloaded, row, 3)

        row += 1  # 3
        self.placeControl(pyxbmct.Label('Upload Speed:'), row, 0)
        self.speed_upload = pyxbmct.Label('')
        self.placeControl(self.speed_upload, row, 1)
        self.placeControl(pyxbmct.Label('Uploaded:'), row, 2)
        self.size_uploaded = pyxbmct.Label('')
        self.placeControl(self.size_uploaded, row, 3)

        row += 1  # 4
        self.placeControl(pyxbmct.Label('File List:'), row, 0)
        self.totalfiles = pyxbmct.Label('')
        self.placeControl(self.totalfiles, row, 1)
        self.placeControl(pyxbmct.Label('Total Size:'), row, 2)
        self.totalsize = pyxbmct.Label('')
        self.placeControl(self.totalsize, row, 3)

        row += 1  # 5
        self.file_list = pyxbmct.List()
        self.placeControl(self.file_list, row, 0, 6, 4)

        row += 4  # 9
        self.placeControl(pyxbmct.Label('Trackers:'), row, 0, 1, 4)

        row += 1  # 10
        self.tracker_list = pyxbmct.List()
        self.placeControl(self.tracker_list, row, 0, 5, 4)

        row += 3  # 13
        self.placeControl(pyxbmct.Label('Download Anonymity:'), row, 0, 1, 4)
        self.download_no_hops = pyxbmct.RadioButton("Direct")
        self.download_1_hop = pyxbmct.RadioButton("1 Hop")
        self.download_2_hops = pyxbmct.RadioButton("2 Hops")
        self.download_3_hops = pyxbmct.RadioButton("3 Hops")

        row += 1
        self.placeControl(self.download_no_hops, row, 0, 2)
        self.placeControl(self.download_1_hop, row, 1, 2)
        self.placeControl(self.download_2_hops, row, 2, 2)
        self.placeControl(self.download_3_hops, row, 3, 2)

        row += 2
        self.upload_label = pyxbmct.Label('Seeding Anonymity:')
        self.placeControl(self.upload_label, row, 0, 1, 4)
        self.upload_noenc = pyxbmct.RadioButton("Direct")
        self.upload_enc = pyxbmct.RadioButton("Anonymous")

        row += 1
        self.placeControl(self.upload_noenc, row, 0, 2, 2)
        self.placeControl(self.upload_enc, row, 2, 2, 2)

        row += 2
        self.dhtc_label = pyxbmct.Label("")
        self.tunnelc_label = pyxbmct.Label("")
        self.discoverc_label = pyxbmct.Label("")
        self.circuits_label = pyxbmct.Label("")
        self.placeControl(self.circuits_label, row, 0)
        self.placeControl(self.dhtc_label, row, 1)
        self.placeControl(self.tunnelc_label, row, 2)
        self.placeControl(self.discoverc_label, row, 3)

        row += 1

        self.connect(self.download_no_hops, lambda: setattr(self, "hops", None))
        self.connect(self.download_1_hop, lambda: setattr(self, "hops", 1))
        self.connect(self.download_2_hops, lambda: setattr(self, "hops", 2))
        self.connect(self.download_3_hops, lambda: setattr(self, "hops", 3))

        self.connect(self.upload_enc, lambda: setattr(self, "anonupload", True))
        self.connect(self.upload_noenc, lambda: setattr(self, "anonupload", False))

        # 19
        self.progress_total_label = pyxbmct.Label('Total Progress:')
        self.placeControl(self.progress_total_label, row, 0)
        self.progress_total = pyxbmct.Image(bgimg)
        self.placeControl(self.progress_total, row, 1, 1, 3)

        row += 1  # 20
        self.progress_prebuff_label = pyxbmct.Label('Prebuffering Progress:')
        self.placeControl(self.progress_prebuff_label, row, 0)
        self.progress_prebuff = pyxbmct.Image(bgimg)
        self.placeControl(self.progress_prebuff, row, 1, 1, 3)

        row += 1  # 21
        self.placeControl(pyxbmct.Label('Header Progress:'), row, 0)
        self.progress_header = pyxbmct.Image(bgimg)
        self.placeControl(self.progress_header, row, 1, 1, 3)

        row += 1  # 22
        self.placeControl(pyxbmct.Label('Footer Progress:'), row, 0)
        self.progress_footer = pyxbmct.Image(bgimg)
        self.placeControl(self.progress_footer, row, 1, 1, 3)

        row += 2  # 24
        self.button_recheck = pyxbmct.Button("Force Recheck")
        self.button_peers = pyxbmct.Button("Peers")
        self.button_updatetrackers = pyxbmct.Button("Update Trackers")
        self.button_querymeta = pyxbmct.Button("Query Metadata")
        self.placeControl(self.button_recheck, row, 0, 2)
        self.placeControl(self.button_peers, row, 1, 2)
        self.placeControl(self.button_updatetrackers, row, 2, 2)
        self.placeControl(self.button_querymeta, row, 3, 2)

        row += 2  # 26
        self.button_start = pyxbmct.Button("Start")
        self.button_stream = pyxbmct.Button("")
        self.button_stop = pyxbmct.Button("Stop")
        self.button_close = pyxbmct.Button("Close")
        self.placeControl(self.button_start, row, 0, 2)
        self.placeControl(self.button_stop, row, 1, 2)
        self.placeControl(self.button_stream, row, 2, 2)
        self.placeControl(self.button_close, row, 3, 2)

        self.basewidth = self.progress_total.getWidth()

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

    @lockelements("button_start")
    def on_button_start(self):
        if self.hasdownload:
            download.setstate(self.infohash, "resume")
        else:
            download.add(self.uri, True)
            self.hasdownload = True

    @lockelements("button_stop")
    def on_button_stop(self):
        download.setstate(self.infohash, "stop")

    @lockelements("button_stream")
    def on_button_stream(self):
        if self.vodmode:
            download.setvodmode(self.infohash, False)
        else:
            if not self.hasdownload:
                download.add(self.uri, True)
                self.hasdownload = True
            self.fileindex = fileindex(self.infohash)
            if self.fileindex is not None:
                download.setvodmode(self.infohash, True, self.fileindex)

    @lockelements("button_recheck")
    def on_button_recheck(self):
        download.setstate(self.infohash, "recheck")

    def on_button_peers(self):
        pass

    def on_button_querymetadata(self):
        if self.uri:
            self.button_querymeta.setEnabled(False)
            tinfo = containers.common.metadataquery(self.uri, None, self.hops, progress_callback=Progress("Metadata Update",
                                                                                                          self,
                                                                                                          self.progress_prebuff_label,
                                                                                                          self.progress_prebuff))
            files = []
            infohash = tinfo.get("infohash")
            if tinfo and tinfo.get("info"):
                if not self.infohash and infohash:
                    self.infohash = infohash
                tinfo = tinfo["info"]
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
        if self.hastrackers is None:
            self.hastrackers = False
        if self.infohash:
            self.button_updatetrackers.setEnabled(False)
            health = containers.common.trackerquery(self.infohash, None, refresh, progress_callback=Progress("Tracker Update",
                                                                                                             self,
                                                                                                             self.progress_total_label,
                                                                                                             self.progress_total))
            self.button_updatetrackers.setEnabled(True)
            self.updatetrackers(health.get("health", {}).items())

    def updatetrackers(self, trackers, updatepeers=True):
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
        if updatepeers:
            self.seeders.setLabel(str(seeders))
            self.peers.setLabel(str(peers))
        self.hastrackers = bool(len(trackers))

    def updatewithdownload(self):
        hasdownload = False
        if self.infohash:
            for dload in download.list(get_files=1):
                if dload["infohash"] == self.infohash:
                    hasdownload = True
                    self.hasmeta = bool(dload["files"])
                    self.updatefiles(dload["files"])
                    self.hastrackers = bool(dload["trackers"])
                    self.updatetrackers([(x["url"], {"leechers": x["peers"]}) for x in dload["trackers"]], False)
                    self.setWindowTitle(dload["name"])
                    self.speed_download.setLabel(format_size(dload["speed_down"]) + "/s")
                    self.speed_upload.setLabel(format_size(dload["speed_up"]) + "/s")
                    self.vodmode = dload["vod_mode"]
                    self.state = dload["status"]
                    if self.vodmode:
                        self.status.setLabel("PREBUFFERING")
                    else:
                        self.status.setLabel(defs.dl_states[self.state])
                    self.totalsize.setLabel(format_size(dload["size"]))
                    self.peers.setLabel("%s/%s" % (dload["num_connected_peers"], dload["num_peers"]))
                    self.seeders.setLabel("%s/%s" % (dload["num_connected_seeds"], dload["num_seeds"]))
                    self.size_downloaded.setLabel(format_size(dload["total_down"]))
                    self.size_uploaded.setLabel(format_size(dload["total_up"]))
                    if not self.anonimitylock and not self.hops == dload["hops"]:
                        self.hops = dload["hops"]
                    if not self.anonimitylock and not self.anonupload == dload["safe_seeding"]:
                        self.anonupload = dload["safe_seeding"]
                    self.total = dload["progress"]
                    self.prebuff = dload["vod_prebuffering_progress"]
                    self.header = dload.get("vod_header_progress", 0)
                    self.footer = dload.get("vod_footer_progress", 0)
        self.hasdownload = hasdownload

    def close(self, *args, **kwargs):
        self.isclosing = True
        super(TorrentWindow, self).close(*args, **kwargs)


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


def fileindex(infohash):
    lof = [x["name"] for x in download.files(infohash)]
    if len(lof) == 1:
        findex = 0
    else:
        findex = gui.select("Select File", lof)
    if int(findex) < 0:
        return None
    else:
        return findex
