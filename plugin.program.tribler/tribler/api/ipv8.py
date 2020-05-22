'''
Created on 26 Mar 2020

@author: boogie
'''
from . import common


class ipv8:
    @staticmethod
    def circuits():
        return common.call("GET", "ipv8/tunnel/circuits")

    @staticmethod
    def overlays():
        return common.call("GET", "ipv8/overlays")
