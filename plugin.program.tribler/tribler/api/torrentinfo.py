'''
Created on 26 Mar 2020

@author: boogie
'''
import json
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
            return json.loads(resp["metainfo"].decode("hex"))
        else:
            return resp
