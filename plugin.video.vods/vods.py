# -*- coding: utf-8 -*-
'''
    Author    : Huseyin BIYIK <husenbiyik at hotmail>
    Year      : 2016
    License   : GPL

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from vodsmodel import scraperextension
from vodsmodel import extension

from tinyxbmc import net


class showextension(scraperextension):

    def getcategories(self):
        #  inherit this
        pass

    def getshows(self, catargs=None):
        #  inherit this
        pass

    def cacheshows(self, id):
        #  inherit this
        pass

    def searchshows(self, keyword=None):
        pass

    def getseasons(self, showargs=None):
        #  inherit this
        pass

    def getepisodes(self, showargs=None, seaargs=None):
        #  inherit this
        pass

    def cacheepisodes(self, id):
        #  inherit this
        pass

    def searchepisodes(self, keyword=None):
        #  inherit this
        pass

    def geturls(self, id):
        #  inherit this
        yield id


class movieextension(scraperextension):

    def getcategories(self):
        #  inherit this
        pass

    def getmovies(self, catargs=None):
        #  inherit this
        pass

    def cachemovies(self, id):
        #  inherit this
        pass

    def searchmovies(self, keyword=None):
        #  inherit this
        pass

    def geturls(self, id):
        #  inherit this
        yield id


class linkplayerextension(extension):
    def geturls(self, url, headers=None):
        yield net.tokodiurl(url, headers=headers)


class addonplayerextension(extension):
    builtin = "RunPlugin(%s)"

    def geturls(self, url, headers=None):
        yield url