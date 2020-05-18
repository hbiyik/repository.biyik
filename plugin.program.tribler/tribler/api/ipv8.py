'''
Created on 26 Mar 2020

@author: boogie
'''
from tinyxbmc import container

from . import common


class ipv8(container.container):
    @staticmethod
    def circuits():
        return common.call("GET", "ipv8/tunnel/circuits")

    @staticmethod
    def overlays():
        return common.call("GET", "ipv8/overlays")
