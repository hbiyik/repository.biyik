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
import urllib
import vods
import htmlement
import json

ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.108 Safari/537.36"


class motorsports(vods.showextension):
    title = u"Motorsports.tv"
    domain = "https://eu.motorsport.tv"
    uselinkplayers = False
    useaddonplayers = False

    def getcategories(self):
        self.additem("Racing Series", "racing")
        self.additem("Programs", "program")
        self.additem("Channels", "channel")

    def getshows(self, cat, keyw=None):
        if cat:
            js = self.getjson(self.domain + "/" + cat)
            for itemid, item in js[cat + "List"]["response"]["entities"][cat].iteritems():
                link = "/%s/%s/%s" % (cat, item["title"], itemid)
                art = {"icon": item["avatar"]["retina"],
                       "thumb": item["avatar"]["retina"],
                       "poster": item["avatar"]["retina"],
                       }
                fanart = item["featureImage"]["retina"]
                if fanart:
                    art["fanart"] = fanart
                elif "largeBgimage" in item:
                    fanart = item["largeBgimage"].get("retina", art["icon"])
                info = {"plot": item.get("description", ""),
                        "plotoutline": item.get("description", "")
                        }
                self.additem(item["title"], (link, art, cat), info, art)

    def searchshows(self, keyw):
        self.getshows(None, keyw)

    def getjson(self, uri):
        page = self.download(uri)
        return json.loads(re.search("window\.APP_STATE\=(.+?)<\/script>", page).group(1))

    def getepisodes(self, show=None, sea=None):
        uri, art, cat = show
        js = self.getjson(self.domain + uri)
        for carousel in js[cat + "Item"]["response"]["carousels"]:
            for episode in carousel["episodes"]:
                if not episode["type"] == "default":
                    continue
                epiart = art.copy()
                epiart["icon"] = epiart["icon"] = epiart["icon"] = episode["images"]["retina"]
                print episode["date"]
                self.additem(carousel["title"] + " : " + episode[u"title"], episode[u"link"], None, epiart)

    def geturls(self, url):
        url = self.domain + url
        print url
        tree = htmlement.fromstring(self.download(url))
        video = tree.find(".//video")
        print video
        if video is not None:
            headers = {"User-Agent": ua, "Referer": url}
            kodiurl = "%s|%s" % (video.get("src"), urllib.urlencode(headers))
            print kodiurl
            yield kodiurl
