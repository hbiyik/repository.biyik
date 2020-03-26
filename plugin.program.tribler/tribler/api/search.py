'''
Created on 26 Mar 2020

@author: boogie
'''
from tinyxbmc import container

from . import common


class search(container.container):
    @staticmethod
    def query(txt_filter, first=1, include_total=1, hide_xxx=1):
        return common.call("GET", "search",
                           txt_filter=txt_filter,
                           first=first,
                           hide_xxx=hide_xxx)
