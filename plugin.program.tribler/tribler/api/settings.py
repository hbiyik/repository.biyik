'''
Created on 26 Mar 2020

@author: boogie
'''
from tinyxbmc import container

from . import common


class settings(container.container):
    @staticmethod
    def get():
        return common.call("GET", "settings")

    @staticmethod
    def set(**settings):
        return common.call("POST", "settings", **settings)
