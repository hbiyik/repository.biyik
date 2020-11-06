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
import htmlement
import re
import json

from tinyxbmc import tools

icon = tools.relpath(__file__, "..", "icon.png")
domain = "https://topdocumentaryfilms.com"

sort = {
        "Recent": "recent",
        "Rating": "highest_rated",
        "Votes": "most_rated",
        "Shares": "most_shared",
        "Comments": "comment_count",
    }


class tdf(vods.movieextension):
    usedirect = False
    info = {
        "title": "Top Documentary Films"
        }
    art = {
           "icon": icon,
           "thumb": icon,
           "poster": icon,
           }

    def scrapegrid(self, u, p, page):
        etree = htmlement.fromstring(self.download(u, params=p))
        for docu in etree.findall(".//article[@class='module']"):
            if docu is None:
                continue
            info = {}
            art = {}
            url = None
            year = docu.find(".//div[@class='meta-bar']")
            title = docu.find(".//h2/a")
            img = docu.find(".//img")
            rating = docu.find(".//span[@class='archive_rating']")
            plot = docu.find(".//p")
            if year is not None:
                if year.text is not None:
                    info["year"] = year.text.split(",")[0].strip()
                genre = year.find(".//div[@class='meta-bar']/a")
                if genre is not None:
                    info["genre"] = genre.text
            if title is not None:
                info["title"] = title.text
                url = title.get("href")
            if img is not None:
                imsrc = img.get("src")
                if imsrc is None:
                    imsrc = img.get("data-src")
                art["thumb"] = art["icon"] = art["poster"] = imsrc
            if rating is not None:
                info["rating"] = rating.text
            if plot is not None:
                info["plot"] = info["plotoutline"] = plot.text
            if url:
                self.additem(info["title"], (url, True), info, art)
        for num in etree.findall(".//div[@class='pagination module']/a"):
            if num.text and num.text.isdigit() and int(num.text) > page:
                self.setnextpage(page + 1, "Next")

    def getcategories(self):
        catxpath = ".//ul[@class='cat-list']/..//a"
        for cat in htmlement.fromstring(self.download(domain)).findall(catxpath):
            self.additem(cat.text, cat.get("href"))

    def getmovies(self, cat=None):
        if not cat:
            cat = ""
        else:
            cat = "/category/" + cat.split("/category/")[1]
        if not self.page:
            page = 1
        else:
            page = self.page
        p = {"r_sortby": sort[self.setting.getstr("sort")], "r_orderby": "desc"}
        u = "%s%s/page/%s" % (domain, cat, page)
        self.scrapegrid(u, p, page)

    def searchmovies(self, keyw):
        cx = "011178800675992829151:dicog11xg70"
        key = "AIzaSyCVAXiUzRYsML1Pv6RwSG1gunmMikTzQqY"
        tpage = self.download("https://cse.google.com/cse/cse.js", params={"cx": cx},
                              referer=domain)
        tkn = re.search('"cse_token":"(.+?)"', tpage)
        p2 = {
            'key': key,
            'gss': '.com',
            'cse_tok': tkn.group(1),
            'rsz': 'filtered_cse',
            'prettyPrint': 'false',
            'callback': 'google.search.Search.apiary6560',
            'cx': cx,
            'googlehost': 'www.google.com',
            # 'nocache': '1510856902614',
            # 'gs_l': 'partner.12...606018.606433.2.620424.4.4.0.0.0.0.124.377.3j1.4.0
            # .gsnos,n=13...0.467j96235j4..1ac.1.25.partner..11.2.198.BrLemIoISlw',
            'q': '\"%s\"' % keyw,
            'source': 'gcsc',
            'num': '20',
            'sig': 'e58ec880d43cfc659265840a556af195',
            'hl': 'en',
            'oq': '\"%s\"' % keyw,
        }

        u = "https://www.googleapis.com/customsearch/v1element"
        page = self.download(u,
                             params=p2,
                             referer=domain
                             )
        js = re.search("google.search.Search.apiary.*?\((.*?)\);", page)
        if js:
            jsob = json.loads(js.group(1))
            for result in jsob.get("results", []):
                rs = result.get("richSnippet")
                if rs:
                    info = {}
                    art = {}
                    mv = rs.get("movie")
                    if mv:
                        info["title"] = mv["name"]
                        info["year"] = mv.get("datepublished", "")
                        info["genre"] = mv.get("genre", "")
                        image = mv.get("image", "DefaultFolder.png")
                        art["icon"] = art["thumb"] = art["poster"] = image
                    else:
                        info["title"] = result.get("title", "")
                        image = rs.get("cseImage", {}).get("src", "DefaultFodler.png")
                        art["icon"] = art["thumb"] = art["poster"] = image
                    info["director"] = rs.get("person", {}).get("name")
                    info["plot"] = info["plotoutline"] = result.get("content")
                    vo = rs.get("videoobject")
                    print info, art
                    if not vo:
                        self.additem(info["title"], (result["url"], True), info, art)
                    else:
                        self.additem(info["title"], (vo["embedurl"], False), info, art)

    def geturls(self, args):
        url, scrape = args
        if not scrape:
            yield url
        else:
            page = self.download(url, referer=domain)
            tree = htmlement.fromstring(page)
            for u in tree.findall(".//meta[@itemprop='embedUrl']"):
                url = u.get("content")
                if "youtube-nocookie.com" in url:
                    url = re.search("(?:\"|\')VIDEO_ID(?:\"|\')\s*?:\s*?(?:\"|\')(.+?)(?:\"|\')", self.download(url)).group(1)
                    url = "https://www.youtube.com/watch?v=%s" % url
                yield url
