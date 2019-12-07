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

import vods
import re
import json
import htmlement

from tinyxbmc import net


class cnnturk(vods.showextension):
    title = u"Cnn Türk"
    domain = "https://www.cnnturk.com"
    art = {
           "icon": "http://www.gundemgazetesi.net/d/other/cnn_t_rk-001.png",
           "thumb": "http://www.gundemgazetesi.net/d/other/cnn_t_rk-001.png"
           }
    perpage = 50
    uselinkplayers = False
    useaddonplayers = False
    cats = {"Programlar": "/tv-cnn-turk/programlar/",
            "Belgeseller": "/tv-cnn-turk/belgeseller/",
            u"Arşiv": "/tv-cnn-turk/arsiv/"
            }

    def _getjson(self, path, sort="IxName asc", subpath="false",
                 contenttype="TVShowContainer", skip=0, top=999):
        rets = []
        query = {
               "url": "",
               "q": "",
               "serviceType": "",
               "orderBy": sort,
               "paths": path,
               "subPath": subpath,
               "tags": "",
               "skip": skip,
               "top": top,
               "contentTypes": contenttype,
               "customTypes": "",
               "viewName": "load-vertical",
               "lastStartDate": "undefined"
               }
        u = "%s/action/loadmore" % self.domain
        page = self.download(u, params=query, referer=self.domain)
        images = re.findall('<img src="(.*?)" alt="(.*?)"', page)
        namergx = '<a href="(.*?)".*?title="(.*?)">'
        hastime = False
        if "<time>" in page:
            hastime = True
            namergx = namergx + ".*?<time>(.*?)</time>"
        names = re.findall(namergx, page, re.DOTALL)
        for row in names:
            _id = row[0]
            name = row[1]
            if hastime:
                dt = row[2]
            else:
                dt = ""
            for img, alt in images:
                if alt == name:
                    break
            if not img.startswith("http"):
                img = "http:" + img
            rets.append([_id, img, name, dt])
        return rets

    def getcategories(self):
        for k, v in self.cats.iteritems():
            self.additem(k, v)

    def scrapeshows(self, cat, flt=None):
        js = self._getjson(cat)
        for program in js:
            show, img, name, _ = program
            if flt and not flt.lower() in name.lower():
                continue
            art = {"thumb": img, "icon": img, "poster": img}
            info = {"tvshowtitle": name}
            show = show.replace(self.domain, "")
            self.additem(name, show, info, art)

    def cacheshows(self, show):
        info = {}
        try:
            page = self.download("%s%s" % (self.domain, show))
            # show = re.findall('data-paths="(.*?)"', page)[0]
            desc = re.findall('<meta name="description" content="(.*?)"', page)[0]
            info = {"plot": desc, "plotoutline": desc}
        except Exception:
            pass
        return info, {}

    def getshows(self, cat):
        if cat:
            self.scrapeshows(cat)

    def searchshows(self, keyw):
        for _, cat in self.cats.iteritems():
            self.scrapeshows(cat, keyw)

    def searchepisodes(self, keyword=None):
        self.getepisodes(None, None, keyword, 500)

    def getepisodes(self, show=None, sea=None, flt=None, perpage=None):
        if not perpage:
            perpage = self.perpage
        if not self.page:
            p = 0
        else:
            p = self.page
        if not show:
            show = "/videolar/"
        page = self.download("%s%s" % (self.domain, show))
        show = re.findall('data-paths="(.*?)"', page)[0]
        js = self._getjson(show, "StartDate desc", "true", "NewsVideo,TVShow", p, perpage)
        for episode in js:
            url, img, name, dt = episode
            if flt and not flt.lower() in name.lower():
                continue
            info = {"date": dt}
            art = {"thumb": img, "icon": img, "poster": img}
            if not dt == "":
                name = "%s - %s" % (dt, name)
            self.additem(name, url, info, art)
        if len(js) == perpage:
            self.setnextpage(p + perpage, "Daha Eski")

    def cacheepisodes(self, url):
        info = {"plot": "", "plotoutline": ""}
        tree = htmlement.fromstring(self.download(self.domain + url))
        title = tree.find('.//meta[@property="og:title"]')
        plot1 = tree.find(".//div[@class='detail-content']/p")
        plot2 = tree.find(".//h2[@class='detail-description']")
        if plot1 is not None:
            info["plot"] = info["plotoutline"] = plot1.text
        elif plot2 is not None:
            info["plot"] = info["plotoutline"] = plot2.text
        if title is not None:
            info["title"] = title.get("content")
        return info, {}

    def geturls(self, url):
        eurl = self.domain + url
        epipage = self.download(eurl)
        cid = re.findall('\["contentid", "(.*?)"\]', epipage)[0]
        js = self.download("%s/action/media/%s" % (self.domain, cid))
        js = json.loads(js)
        # js["Media"]["Link"].get("ServiceUrl")
        m3u8 = "%s%s" % ("https://soledge7.dogannet.tv/",
                         js["Media"]["Link"]["SecurePath"])
        yield net.tokodiurl(m3u8, headers={"referer": eurl})
