'''
Created on 26 Mar 2020

@author: boogie
'''
from . import common


class settings:
    @staticmethod
    def get():
        return common.call("GET", "settings")

    @staticmethod
    def set(**settings):
        return common.call("POST", "settings", **settings)
