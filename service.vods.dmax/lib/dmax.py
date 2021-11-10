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
import re

import vods
import htmlement

from tinyxbmc import const


class dmaxtr(vods.showextension):
    title = u"DMAX TR"
    domain = "https://www.dmax.com.tr"
    uselinkplayers = False
    useaddonplayers = False
    dropboxtoken = const.DB_TOKEN

    def iterelems(self, xpath, url=None, page=None, tree=None, cat=None):
        if not tree:
            if not page:
                page = self.download(url)
            tree = htmlement.fromstring(page)
        for elem in tree.iterfind(xpath):
            if cat:
                catid = elem.get("data-serie-category-id")
                if not catid == cat:
                    continue
            img = elem.find(".//img")
            if img is not None:
                img = img.get("src")
            else:
                img = "DefaultFolder.png"
            title = elem.find(".//h3")
            if title is None:
                continue
            else:
                title = title.text
            info = {}
            art = {"icon": img, "thumb": img, "poster": img}
            if xpath.endswith("/a"):
                link = elem.get("href")
            else:
                link = elem.find(".//a").get("href")
            yield title, link, info, art

    def getcategories(self):
        tree = htmlement.fromstring(self.download(self.domain + "/programlar"))
        for cat in tree.iterfind(".//ul[@class='category-list category-type']/li"):
            catid = cat.get("data-category-id")
            if catid == "0":
                continue
            self.additem(cat.text, catid)

    def getshows(self, cat, keyw=None):
        if cat or filter:
            xpath = ".//li[@class='content_pool_item_add content_pool_item']"
            url = self.domain + "/programlar"
            for args in self.iterelems(xpath, url, None, None, cat):
                if keyw and not keyw.lower() in args[0].lower():
                    continue
                self.additem(*args)

    def searchshows(self, keyw):
        self.getshows(None, keyw)

    def getepisodes(self, show=None, sea=None):
        if not show and not sea:
            url = self.domain + "/kesfet"
            xpath = ".//div[@class='promoted-content-item-box content_pool as_container']/a"
        else:
            url = self.domain + show + "/bolumler"
            xpath = ".//div[@class='promoted-content-item content_pool_item_add content_pool_item']"
        for args in self.iterelems(xpath, url):
            self.additem(*args)

    def geturls(self, url):
        page = self.download(self.domain + url, referer=self.domain)
        video = re.search("window\.location = '(.+)'", page)
        if video:
            yield video.group(1)
