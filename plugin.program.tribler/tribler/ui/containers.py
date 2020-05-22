'''
Created on 3 May 2020

@author: boogie
'''
import threading
import time
from tinyxbmc import container
from tinyxbmc import gui

from tribler.api.metadata import metadata
from tribler.api.torrentinfo import torrentinfo
from tribler.api.download import download
from tribler.defs import DHT_TIMEOUT, HTTP_TIMEOUT


def timerprogress(caption, timeout, progress_callback, apicallback, **kwargs):
    if progress_callback:
        bgprogress = progress_callback
    else:
        bgprogress = gui.bgprogress(caption)
    state = {"progress": None}

    def progress():
        for i in range(int(timeout * 1.3)):
            if state["progress"] or bgprogress.isFinished():
                break
            bgprogress.update(int(100 * float(i) / timeout))
            time.sleep(1)
        bgprogress.close()

    threading.Thread(target=progress).start()
    state["progress"] = apicallback(**kwargs)
    if state["progress"] and not progress_callback:
        container.refresh()
    return state["progress"]


class common(container.container):
    @staticmethod
    def trackerquery(infohash, name=None, refresh=1, progress_callback=None):
        if not name:
            name = infohash
        caption = "Tracker Query: %s" % name
        return timerprogress(caption, DHT_TIMEOUT, progress_callback, metadata.torrenthealth,
                             infohash=infohash, refresh=refresh
                             )

    @staticmethod
    def metadataquery(uri=None, infohash=None, hops=None, progress_callback=None):
        url = uri or infohash
        caption = "Metadata Query: %s" % url
        return timerprogress(caption, HTTP_TIMEOUT, progress_callback, torrentinfo.get,
                             uri=uri, hops=hops, infohash=infohash
                             )

    @staticmethod
    def subscribechannel(chanid, publickey, subscribed):
        ret = metadata.subscribe(chanid, publickey, subscribed)
        container.refresh()
        return ret

    @staticmethod
    def setdownloadstate(infohash, state):
        ret = download.setstate(infohash, state)
        time.sleep(2)
        container.refresh()
        return ret

    @staticmethod
    def deletedownload(infohash, silent=False):
        remove_data = False
        confirm = silent or gui.yesno("Are you sure?", "Are you sure you want to remove the torrent?")
        if confirm:
            remove_data = silent or gui.yesno("Remove Files Also?", "Do you want to completely remove the stored files from the file system as well?")
            ret = download.delete(infohash, remove_data)
            if ret.get("removed"):
                txt = "Torrent"
                if remove_data:
                    txt += " + stored data"
                txt += " has been removed."
                if not silent:
                    gui.ok("Removed", txt)
                container.refresh()
                return ret

    @staticmethod
    def callapiwithrefresh(address, *args, **kwargs):
        mdlname, mtdname = address.split(".")
        mdl = __import__("tribler.api.%s" % mdlname, locals=None, globals=None, fromlist=[None], level=0)
        method = getattr(getattr(mdl, mdlname), mtdname)
        ret = method(*args, **kwargs)
        container.refresh()
        return ret
