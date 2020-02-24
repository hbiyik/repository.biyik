'''
Created on Sep 29, 2019

@author: boogie
'''

import subprocess
import shlex
import re
import platform

from tinyxbmc import hay

from anon import defs


class Base(object):
    def __init__(self, tempdir, *args, **kwargs):
        self.tempdir = tempdir
        self.cfg = {}
        self.stack = hay.stack("anon")
        self.nontors = ["127.0.0.0/8",
                        "10.0.0.0/8", "192.168.0.0/16",
                        "172.16.0.0/12",
                        "0.0.0.0/8",
                        "100.64.0.0/10",
                        "169.254.0.0/16",
                        "192.0.0.0/24",
                        "192.0.2.0/24", "192.88.99.0/24", "198.18.0.0/15", "198.51.100.0/24",
                        "203.0.113.0/24", "224.0.0.0/4", "240.0.0.0/4", "255.255.255.255/32"]
        self.init(*args, **kwargs)
        for k, v in self.cfg.iteritems():
            data = self.stack.find(k).data
            if not data == {}:
                self.cfg[k] = data
        for k, v in defs.defconfig.iteritems():
            data = self.stack.find(k).data
            if data == {}:
                data = v
            self.cfg[k] = data
        self.defaultgw, self.interface = self.default_if_gw()
        self.ip, self.subnet = self.if_ip_subnet(self.interface)
        self.nontors.append(self.subnet)

    def missing_reqs(self):
        yield

    def init(self):
        pass

    def run_cmd(self, command, stdout=True, stdin=None):
        try:
            popen = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stdin=stdin)
        except Exception:
            if stdout:
                return []
            else:
                return
        if stdout:
            return iter(popen.stdout.readline, b"")
        else:
            return popen

    def default_if_gw(self):
        raise Exception
        return "?", "?"

    def if_ip_subnet(self, dev):
        raise Exception
        return "?", "?"

    def config(self, key, value):
        self.stack.throw(key, value)
        self.stack.snapshot()
        self.cfg[key] = value

    def getsetting(self, key):
        data = self.stack.find(key).data
        if data == {}:
            data = self.cfg[key]
        if data == "auto":
            _, dev = self.default_if_gw()
            if dev:
                data = dev
            else:
                data = "?"
        return data

    def setsetting(self, key, value):
        self.stack.throw(key, value)
        self.cfg[key] = value
        self.stack.snapshot()

    def reset(self):
        pass

    def start_tor(self):
        pass

    def stop_tor(self):
        pass

    def anonymize(self):
        pass

    def set_dns(self):
        pass

    def start_ovpn(self):
        pass

    def stop_ovpn(self):
        pass

    def findpids(self, process):
        pass

    def stats(self):
        return {}
