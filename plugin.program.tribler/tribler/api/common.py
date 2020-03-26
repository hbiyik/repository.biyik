'''
Created on 26 Mar 2020

@author: boogie
'''
from tinyxbmc import net
from tinyxbmc import gui

import os
import ConfigParser


def getconfig():
    try:
        base_dir = os.path.expanduser("~/.Tribler")
        for d in os.listdir(base_dir):
            subdir = os.path.join(base_dir, d)
            if os.path.isdir(subdir):
                for subfile in os.listdir(subdir):
                    if subfile == "triblerd.conf":
                        config = ConfigParser.ConfigParser()
                        config.read(os.path.join(subdir, subfile))
                        break
                if config:
                    break
    except Exception:
        config = None
    return config


config = getconfig()


def call(method, endpoint, **data):
    url = "http://localhost:%s/%s" % (config.get("http_api", "port"), endpoint)
    headers = {"X-Api-Key": config.get("http_api", "key")}
    print url
    print data
    if endpoint in ["search"]:
        params = data
        js = True
    else:
        params = None
        js = data

    resp = net.http(url, params=params, headers=headers, json=js, method=method)
    import json
    print json.dumps(resp)
    if "error" in resp:
        if isinstance(resp["error"], dict):
            title = resp["error"].get("code", "ERROR")
            msg = resp["error"].get("message", "Unknown Error")
        else:
            title = "ERROR"
            msg = str(resp["error"])
        gui.ok(title, msg)
    else:
        return resp
