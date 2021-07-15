'''
Created on 26 Mar 2020

@author: boogie
'''
from tinyxbmc import gui

from tribler.api import common

import uuid
import threading
import time


class remote:
    @staticmethod
    def query(txt_filter=None, channel_pk=None, metadata_type="torrent", sort_by="updated", sort_desc=1, timeout=None, max_results=None, hide_xxx=0):
        loop_timeout = 3
        e = common.event(timeout or loop_timeout)
        state = {"start": None, "stop": False, "queries": 0, "results": []}
        uids = []

        def progress():
            progress = gui.progress("Querying GigaChannel")
            state["start"] = time.time()
            while True:
                elapsed = time.time() - state["start"]
                if timeout is not None and elapsed > timeout or \
                        progress.iscanceled() or \
                        max_results is not None and len(state["results"]) >= max_results:
                    e.response.close()
                    state["stop"] = True
                    break
                else:
                    if timeout is not None:
                        percent = int(100 * elapsed / timeout)
                    else:
                        percent = int(100 * (elapsed % loop_timeout) / loop_timeout)
                        if elapsed > loop_timeout:
                            percent = 100
                            e.response.close()
                    progress.update(percent, "Found %s Results in %s queries. %s" % (len(state["results"]),
                                                                                     state["queries"],
                                                                                     "MAX RESULTS: " + str(max_results) if max_results else ""))

        threading.Thread(target=progress).start()
        while True:
            e.prepare()
            if state["stop"]:
                break
            uid = str(uuid.uuid4())
            uids.append(uid)
            common.call("PUT", "remote_query",
                        sort_by=sort_by,
                        sort_desc=sort_desc,
                        txt_filter=txt_filter,
                        uuid=uid,
                        channel_pk=channel_pk,
                        metadata_type=metadata_type)
            for ev in e.iter():
                if ev.get("uuid") in uids:
                    uids.remove(uid)
                    state["queries"] += 1
                    state["results"].extend(ev.get("results", []))
                    break
            if timeout is None:
                state["start"] = time.time()
        return state["results"]
