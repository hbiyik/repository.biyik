'''
Created on 26 Mar 2020

@author: boogie
'''
import json
import hashlib
import bencode
from tinyxbmc import container

from . import common


class torrentinfo(container.container):
    @staticmethod
    def get(uri, hops=None, infohash=None):
        if not uri:
            uri = common.makemagnet(infohash)
        kwargs = {"uri": uri}
        if hops:
            kwargs["hops"] = hops
        resp = common.call("GET", "torrentinfo", **kwargs)
        if resp and resp.get("metainfo"):
            metainfo = json.loads(resp["metainfo"].decode("hex"))
            metainfo["info"]["pieces"] = metainfo["info"]["pieces"].decode("hex")
            metainfo["infohash"] = hashlib.sha1(bencode.encode(metainfo['info'])).digest().encode("hex")
            return metainfo
        else:
            return resp
