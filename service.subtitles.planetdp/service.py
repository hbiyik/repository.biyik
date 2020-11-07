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
import sublib

import re
import os


domain = "https://www.planetdp.org"
isotoquery = {"tr": u"Türkçe",
              "en": u"İngilizce",
              "es": u"İspanyolca",
              "de": u"Almanca",
              "fr": u"Fransızca",
              }


def norm(txt):
    txt = txt.replace(" ", "")
    txt = txt.lower()
    return txt


def imagecode(url):
    url = url.lower()
    if "ngilizce" in url:
        return "en"
    if "rk" in url:
        return "tr"
    if "spanyolca" in url:
        return "es"
    if "alman" in url:
        return "de"
    if "frans" in url:
        return "fr"
    return "tr"


class planetdp(sublib.service):

    def search(self):
        self.item.imdb = "tt0182576"
        query = {"title": self.item.imdb or self.item.title,
                 "year_date": "" if self.item.show else self.item.year,
                 "is_serial": int(self.item.show)
                 }
        page = self.request(domain + "/movie/search", query, referer=domain)
        if re.search('class="baba_main_right"', page):
            # direct page without search result
            self.scrapesubs(page)
            return
        for result in re.finditer("right2\">[\s\n]*?<a href=\"(.+?)\"><h4>(.+?)<\/h4><\/a>[\s\n]*?<h5>(.+?)<\/h5>", page, re.DOTALL):
            # TODO: take akas
            title = norm(result.group(2))
            year = re.search("\s([0-9]{4})\s", result.group(3))
            imdb = re.search("\s([0-9]{7})\s", result.group(3))
            if norm(self.item.title) == title:
                self.scrapesubs(self.request(domain + result.group(1), referer=domain))
                if self.item.imdb:
                    imdb = "tt" + re.search("\s([0-9]{7})\s", imdb)
                    if imdb == self.item.imdb:
                        break
                if self.item.year and not self.item.show:
                    year = int(year.group(1))
                    if year == self.item.year:
                        break

    def download(self, link):
        page = self.request(link, referer=domain)
        token = re.search('<input type="hidden" name="_token" value="(.*?)">', page)
        subid = re.search('rel\-id="(.*?)"', page)
        uniqk = re.search('rel\-tag="(.*?)"', page)

        if token and subid and uniqk:
            data = {
                    "_token": token.group(1),
                    "_method": "POST",
                    "subtitle_id": subid.group(1),
                    "uniquekey": uniqk.group(1),
                    "filepath": ""
                    }
            remfile = self.request(domain + "/subtitle/download", data=data, referer=link,
                                   method="POST", text=False)
            fname = remfile.headers["Content-Disposition"]
            fname = re.search('filename=(.+)', fname)
            fname = fname.group(1)
            fname = os.path.join(self.path, fname)
            with open(fname, "wb") as f:
                f.write(remfile.content)
            self.addfile(fname)

    def checkpriority(self, txt):
        # this is a very complicated and fuzzy string work
        if self.item.episode < 0 or not self.item.show:
            return False, 0
        ispack = 0
        packmatch = 0
        epmatch = 0
        skip = False
        sb = re.search("S\:(.+?)[-|,]B\:(.+)", txt)
        if sb:
            e = sb.group(2).strip().replace(" ", "").lower()
            s = sb.group(1).strip().replace(" ", "").lower()
            # verify season match first
            if s.isdigit() and self.item.season > 0 and \
                    not self.item.season == int(s):
                return True, 0
            ismultiple = False
            # B: 1,2,3,4 ...
            for m in e.split(","):
                if m.strip().isdigit():
                    ismultiple = True
                else:
                    ismultiple = False
                    break
            if ismultiple:
                # check if in range
                multiples = [int(x) for x in e.split(",")]
                if self.item.episode in multiples:
                    packmatch = 2
                else:
                    skip = True
            # B: 1~4
            if "~" in e:
                startend = e.split("~")
                # check if in range
                if len(startend) == 2 and \
                    startend[0].strip().isdigit() and \
                        startend[1].strip().isdigit():
                    if int(startend[0]) <= self.item.episode and \
                            int(startend[1]) >= self.item.episode:
                        packmatch = 2
                    else:
                        skip = True
                else:
                    ispack = 1
            # B: Paket meaning a package
            if "paket" in e:
                ispack = 1
            # B:1 or B:01
            if e.isdigit():
                if int(e) == self.item.episode:
                    epmatch = 3
                else:
                    skip = True
        return skip, ispack + epmatch + packmatch

    def scrapesubs(self, page):
        regstr = '<tr class=\"row.+?</tr>'
        for row in re.findall(regstr, page, re.DOTALL):
            index = 0
            link = None
            name = None
            iso = None
            priority = 0
            for column in re.findall("<td.+?>(.*?)</td>", row, re.DOTALL):
                skip = None
                index += 1
                if index == 1:
                    res = re.search('href="(.*?)".*?title="(.*?)"', column)
                    if not res:
                        break
                    link = domain + res.group(1)
                    name = res.group(2).replace(u"altyazı", "").strip()
                    release = re.search("<span>(.*?)</span>", column)
                    if release:
                        release = re.sub("<.*?>", "", release.group(1)).strip()
                        skip, priority = self.checkpriority(release)
                        name += " %s" % release
                    if skip:
                        name = None
                        break
                if index == 2:
                    res = re.search('alt="(.*?)"', column)
                    if res:
                        iso = imagecode(res.group(1))
                    else:
                        iso = "tr"
                if index in [5, 7]:
                    name = "%s | %s" % (name, re.sub('<.*?>', '', column).strip())
            if link and name and iso:
                sub = self.sub(name, iso)
                sub.download(link)
                self.priority = priority
                self.addsub(sub)
