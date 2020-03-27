'''
Created on 26 Mar 2020

@author: boogie
'''
from tinyxbmc import container

import common
import event

import uuid


class remote(container.container):
    @staticmethod
    def query(txt_filter=None, channel_pk=None, metadata_type="torrent", sort_by="updated", sort_desc=1):
        uid = str(uuid.uuid4())
        common.call("PUT", "remote_query",
                    sort_by=sort_by,
                    sort_desc=sort_desc,
                    txt_filter=txt_filter,
                    uuid=uid,
                    channel_pk=channel_pk,
                    metadata_type=metadata_type)

        def callback(js):
            return js.get("event", {}).get("uuid") == uid

        js = event.event.wait(callback)
        if js:
            return js["event"].get("results", [])
        else:
            return []
