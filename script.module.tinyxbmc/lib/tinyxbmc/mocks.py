'''
Created on Nov 9, 2021

@author: boogie
'''
import tempfile
from tinyxbmc import tools

tempfile._get_default_tempdir = lambda: tools.translatePath("special://home/temp")
