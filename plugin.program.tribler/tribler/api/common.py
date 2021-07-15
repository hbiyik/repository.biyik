'''
Created on 26 Mar 2020

@author: boogie
'''
import re
from distutils.version import LooseVersion
from tinyxbmc import net
from tinyxbmc import gui
from tinyxbmc import addon
from requests.exceptions import StreamConsumedError, ConnectionError, ConnectTimeout, ReadTimeout

from tribler import defs

import traceback
import os
from six.moves import configparser

import json
from tribler.defs import HTTP_TIMEOUT, MIN_TRIBLER_VERSION


API_SECTION = None


def localconfig():
    config = None
    section = None
    base_dir = os.getenv('APPDATA')
    if base_dir:
        base_dir = os.path.join(base_dir, ".Tribler")
    if not base_dir or not os.path.exists(base_dir):
        base_dir = os.path.expanduser("~/.Tribler")
    for version_dir in os.listdir(base_dir):
        if config:
            break
        version_dir_check = re.search("[0-9\.]+", version_dir)
        if version_dir_check and version_dir == version_dir_check.group(0):
            # TO-DO: always use latest
            # receive config path from settings
            if LooseVersion(version_dir) >= LooseVersion(MIN_TRIBLER_VERSION):
                subdir = os.path.join(base_dir, version_dir)
                if os.path.isdir(subdir):
                    for subfile in os.listdir(subdir):
                        if subfile == "triblerd.conf":
                            try:
                                conffile = os.path.join(subdir, subfile)
                                config = configparser.ConfigParser()
                                config.read(conffile)
                                config.address = None
                                for key in ("port", "http_port"):
                                    for section in ("http_api", "api"):
                                        try:
                                            config.address = "http://localhost:%s" % config.get(section, key)
                                        except (configparser.NoSectionError, configparser.NoOptionError):
                                            # print(traceback.format_exc())
                                            continue
                                        print("using config from: %s" % conffile)
                                        break
                            except Exception:
                                print(traceback.format_exc())
    return section, config


class remoteconfig(object):
    def __init__(self, address, apikey):
        if address.endswith("/"):
            address = address[:-1]
        self.address = address
        self.js = net.http(address + "/settings", headers={"X-Api-Key": apikey}, json=True)

    def get(self, group, stg):
        return self.js["settings"].get(group, {}).get(stg)


settings = addon.kodisetting("plugin.program.tribler")
if settings.getstr("conmode").lower() == "remote":
    try:
        config = remoteconfig(settings.getstr("address"), settings.getstr("apikey"))
    except Exception:
        print(traceback.format_exc())
        gui.ok("Tribler", "Can not connect to daemon at %s" % settings.getstr("address"))
else:
    try:
        API_SECTION, config = localconfig()
    except Exception:
        print(traceback.format_exc())
        gui.ok("Tribler", "Can not find local installation")
        config = None


def call(method, endpoint, **data):
    url = "%s/%s" % (config.address, endpoint)
    headers = {"X-Api-Key": config.get(API_SECTION, "key")}
    if method in ["GET"] or method == "PUT" and endpoint == "remote_query":
        params = data
        js = True
    else:
        params = None
        js = data

    try:
        resp = net.http(url, timeout=defs.HTTP_TIMEOUT, params=params, headers=headers, json=js, method=method)
    except ReadTimeout:
        resp = {"error": "Read timeout out in %s seconds" % HTTP_TIMEOUT}
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


def makemagnet(infohash):
    return "magnet:?xt=urn:btih:%s" % infohash


def format_size(num, suffix='B'):
    for unit in ['', 'k', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)


class event(object):
    def __init__(self, timeout):
        self.url = "%s/events" % config.address
        self.headers = {"X-Api-Key": config.get(API_SECTION, "key")}
        self.timeout = timeout
        self.prepare()

    def prepare(self):
        self.response = net.http(self.url, timeout=self.timeout, headers=self.headers, stream=True, text=False)

    def iter(self):
        try:
            for content in self.response.iter_lines(delimiter="\n\ndata: "):
                try:
                    js = json.loads(content)
                except ValueError:
                    continue
                yield js["event"]
            self.response.close()
        except GeneratorExit:
            self.response.close()
        except (StreamConsumedError, AttributeError, ConnectionError, ConnectTimeout):
            raise StopIteration
