'''
Created on 26 Mar 2020

@author: boogie
'''
from tinyxbmc import container
from tinyxbmc import net

from . import common

import json


class event(container.container):
    @staticmethod
    def wait(callback, timeout=10):
        url = "http://localhost:%s/events" % common.config.get("http_api", "port")
        headers = {"X-Api-Key": common.config.get("http_api", "key")}
        resp = net.http(url, timeout=timeout, headers=headers, stream=True, text=False)
        for content in resp.iter_lines(delimiter="\n\ndata: "):
            try:
                js = json.loads(content)
            except ValueError:
                print "." + content.encode("ascii", "replace") + "."
                continue
            print "+" + content.encode("ascii", "replace") + "+"
            if callback(js):
                return js
