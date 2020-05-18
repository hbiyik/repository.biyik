'''
Created on 26 Mar 2020

@author: boogie
'''
from tinyxbmc import gui
from tinyxbmc import container

import common


class download(container.container):
    @staticmethod
    def add(uri, silent=False):
        try:
            hops = int(common.config.get("download_defaults", "number_hops"))
        except Exception:
            hops = 1
        try:
            anon_seed = 1 if common.config.get("download_defaults", "safeseeding_enabled") else 0
        except Exception:
            anon_seed = 1
        resp = common.call("PUT", "downloads", uri=uri,
                           anon_hops=hops,
                           safe_seeding=anon_seed)
        if resp and not silent:
            gui.ok("Torrent Added", resp.get("infohash", ""))

    @staticmethod
    def setstate(ihash, state):
        if state == "stop":
            download.setvodmode(ihash, False)
        resp = common.call("PATCH", "downloads/%s" % ihash, state=state)
        if resp.get("modified"):
            container.refresh()

    @staticmethod
    def setvodmode(ihash, vod_mode, fileindex=None):
        if vod_mode:
            resp = common.call("PATCH", "downloads/%s" % ihash, vod_mode=True, fileindex=fileindex)
        else:
            resp = common.call("PATCH", "downloads/%s" % ihash, vod_mode=False)
        if resp.get("modified"):
            container.refresh()
        return resp

    @staticmethod
    def sethops(ihash, hops):
        return common.call("PATCH", "downloads/%s" % ihash, anon_hops=hops)

    @staticmethod
    def delete(ihash, remove_data=None, silent=False):
        if silent:
            confirm = True
        else:
            txt = "Are you sure you want to remove the torrent?"
            if remove_data is None:
                remove_data = gui.yesno("Remove Files", "Do you want to completely remove the stored files from the file system as well?")
                txt += " This will also remove the stored files!"
            confirm = gui.yesno("Delete Torrent", txt)
        if confirm:
            resp = common.call("DELETE", "downloads/%s" % ihash, remove_data=remove_data)
            if not silent:
                if resp and resp.get("removed"):
                    txt = "Trorent"
                    if remove_data:
                        txt += " + stored data"
                    txt += " has been removed."
                    gui.ok("Removed", txt)
            container.refresh()

    @staticmethod
    def list(get_files=0):
        downloads = common.call("GET", "downloads", get_files=get_files)
        if downloads:
            return downloads.get("downloads", [])
        else:
            return []
