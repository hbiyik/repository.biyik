'''
Created on 26 Mar 2020

@author: boogie
'''
import common


class download:
    @staticmethod
    def add(uri):
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
        return resp.get("infohash")

    @staticmethod
    def setstate(ihash, state):
        if state == "stop":
            download.setvodmode(ihash, False)
        return common.call("PATCH", "downloads/%s" % ihash, state=state)

    @staticmethod
    def setvodmode(ihash, vod_mode, fileindex=None):
        if vod_mode:
            resp = common.call("PATCH", "downloads/%s" % ihash, vod_mode=True, fileindex=fileindex)
        else:
            resp = common.call("PATCH", "downloads/%s" % ihash, vod_mode=False)
        return resp

    @staticmethod
    def sethops(ihash, hops):
        return common.call("PATCH", "downloads/%s" % ihash, anon_hops=hops)

    @staticmethod
    def delete(ihash, remove_data=None):
        return common.call("DELETE", "downloads/%s" % ihash, remove_data=remove_data)

    @staticmethod
    def list(get_files=0):
        downloads = common.call("GET", "downloads", get_files=get_files)
        if downloads:
            return downloads.get("downloads", [])
        else:
            return []

    @staticmethod
    def files(infohash):
        resp = common.call("GET", "downloads/%s/files" % infohash)
        if resp and "files" in resp:
            return resp.get("files", [])
        else:
            return []
