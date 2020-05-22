'''
Created on 26 Mar 2020

@author: boogie
'''

from . import common


class channel:
    @staticmethod
    def list(subscribed, first=1, last=500, sort_by="updated", sort_desc=1):
        resp = common.call("GET", "channels",
                           subscribed=1 if subscribed else None,
                           first=first,
                           last=last,
                           sort_by=sort_by,
                           sort_desc=sort_desc)
        if resp:
            return resp.get("results", [])
        else:
            return []

    @staticmethod
    def get(chanid, publickey, first=1, last=20, sort_by="updated", sort_desc=1, include_total=1, hide_xxx=0):
        resp = common.call("GET", "channels/%s/%s" % (publickey, chanid),
                           first=first,
                           last=last,
                           sort_by=sort_by,
                           sort_desc=sort_desc,
                           include_total=include_total,
                           hide_xxx=hide_xxx)
        if resp:
            results = resp.get("results")
            if results is not None:
                return resp["total"], results
            else:
                return 0, []
        else:
            return 0, []
