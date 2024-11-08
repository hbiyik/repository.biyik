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
import htmlement
import shutil
from chromium import Browser
from tinyxbmc.const import DB_TOKEN

import re
import os


REMOTE_DBG = False

if REMOTE_DBG:
    import sys
    pdevpath = "/home/boogie/.p2/pool/plugins/org.python.pydev.core_8.3.0.202104101217/pysrc/"
    sys.path.append(pdevpath)
    import pydevd  # @UnresolvedImport
    pydevd.settrace(stdoutToServer=True, stderrToServer=True, suspend=False)


def isvalid(page):
    if u"Türkçe Altyazı © 2007 - 2021" in page:
        return page


domain = "https://turkcealtyazi.org"

quals = {
         "1": 5,  # good quality
         "2": 4,  # enough quality
         "3": 0,  # bad quality
         "4": 2,  # not rated yet
         "5": 1,  # waiting for source
         "6": 3,  # archived
         }


def norm(txt):
    txt = txt.replace(" ", "")
    txt = txt.lower()
    return txt


def striphtml(txt):
    txt = re.sub("<.*?>", "", txt)
    txt = re.sub("\t", "", txt)
    txt = re.sub("\n", "", txt)
    txt = txt.replace("  ", " ")
    return txt


def elementsrc(element, exclude=[]):
    if element is None:
        return ""
    if element in exclude:
        return ""
    text = element.text or ''
    for subelement in element:
        text += elementsrc(subelement, exclude)
    text += element.tail or ''
    return striphtml(text)


class turkcealtyazi(sublib.service):
    bropboxoken = DB_TOKEN

    def oninit(self):
        self.loadtimeout = 3

    def search(self):
        self.found = False
        self.ignoreyear = False
        if self.item.imdb:
            self.find(self.item.imdb)
        if not self.num() and not self.item.show and self.item.year:
            self.find("%s %s" % (self.item.title, self.item.year))
        if not self.num():
            self.ignoreyear = True
            self.find(self.item.title)

    def checkpriority(self, txt):
        # this is a very complicated and fuzzy string work
        txt = txt.lower().replace(" ", "")
        cd = re.search("([0-9])cd", txt)
        # less the number of cds higher the priority
        if cd:
            return False, - int(cd.group(1))
        # rest is for episodes, if movie then return lowest prio.
        if self.item.episode < 0 or not self.item.show:
            return False, -100
        ispack = 0
        packmatch = 0
        epmatch = 0
        skip = False
        se = re.search("s(.+?)\|e(.+)", txt)
        if not se:
            se = re.search("s(.+?)(paket)", txt)
        if se:
            e = se.group(2)
            s = se.group(1)
            # verify season match first
            if s.isdigit() and self.item.season > 0 and \
                    not self.item.season == int(s):
                return True, 0
            ismultiple = False
            # e: 1,2,3,4 ...
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
            # e: 1~4
            if "~" in e:
                startend = e.split("~")
                # check if in range
                if len(startend) == 2 and \
                    startend[0].strip().isdigit() and \
                        startend[1].strip().isdigit():
                    if int(startend[0]) < self.item.episode and \
                            int(startend[1]) > self.item.episode:
                        packmatch = 2
                    else:
                        skip = True
                else:
                    ispack = 1
            # e: Paket meaning a package
            if e == "paket":
                ispack = 1
            # e:1 or e:01
            if e.isdigit():
                if int(e) == self.item.episode:
                    epmatch = 3
                else:
                    skip = True
        return skip, ispack + epmatch + packmatch

    def scraperesults(self, page, tree):
        for row in tree.findall(".//div[@class='nblock']/div/div[2]"):
            a = row.find(".//a")
            if a is None:
                continue
            link = a.get("href")
            name = a.get("title")
            if not name:
                continue
            years = row.findall(".//span")
            if len(years) > 1:
                ryear = re.search("([0-9]{4})", years[1].text)
                if ryear:
                    year = int(ryear.group(1))
            if len(years) <= 1 or not ryear:
                year = "-1"
            if norm(name) == norm(self.item.title) and \
                (self.item.show or
                    (self.ignoreyear or self.item.year is None or self.item.year == year)):
                self.found = True
                with Browser() as browser:
                    p = browser.navigate(domain + link, referer=domain)
                self.scrapepage(htmlement.fromstring(p))
                break
        if not self.found:
            pages = tree.findall(".//div[@class='pagin']/a")
            for page in pages:
                if "sonra" in page.text.lower():
                    if self.found:
                        break
                    with Browser() as browser:
                        npage = browser.navigate(domain + page.get("href"), referer=domain)
                    self.scraperesults(npage, htmlement.fromstring(npage))

    def scrapepage(self, tree):
        subs = tree.findall(".//div[@id='altyazilar']/div/div")
        for s in subs:
            desc = s.find(".//div[@class='ripdiv']")
            xname = s.find(".//div[@class='fl']/a")
            alcd = s.find(".//div[@class='alcd']")
            if xname is None:
                continue
            if alcd is None:
                continue
            if desc is None:
                continue
            alcd = elementsrc(alcd)
            name = xname.get("title")
            link = xname.get("href")
            desc = elementsrc(desc)
            skip, priority = self.checkpriority(alcd)
            if skip:
                continue
            tran = elementsrc(s.find(".//div[@class='alcevirmen']/a"))
            iso = "tr"
            qualrate = "4"
            aldil = s.find(".//div[@class='aldil']/span")
            if aldil is not None:
                cls = aldil.get("class")
                riso = re.search('flag([a-z]{2})', cls)
                if riso is not None:
                    iso = riso.group(1)
            qual = s.find(".//div[@class='fl']/span")
            if qual is not None:
                qual = qual.get("class")
                if isinstance(qual, str):
                    qual = qual.replace("kal", "")
                    if qual.isdigit():
                        qualrate = qual
            namestr = "%s, %s, %s, %s" % (name, alcd, desc, tran)
            sub = self.sub(namestr, iso)
            sub.download(domain + link)
            sub.priority = priority
            if qual:
                sub.rating = quals[qualrate]
            self.addsub(sub)

    def find(self, query):
        with Browser() as browser:
            browser.navigate(domain)
            page = browser.navigate(domain + "/find.php?cat=sub&find=" + query, referer=domain)
        tree = htmlement.fromstring(page)
        title = tree.find(".//title")
        if "arama" in title.text.lower():
            self.scraperesults(page, tree)
        else:
            self.scrapepage(tree)

    def download(self, link):
        with Browser() as browser:
            browser.navigate(domain)
            browser.navigate(link)
            browser.cleardownloads()
            browser.elem_call("submit", tag="form", index=3)
            list(browser.iterdownload())
            subtitle = browser.getdownloads()[0]
            shutil.move(subtitle, self.path)
            fname = os.path.join(self.path, os.path.basename(subtitle))
            self.addfile(fname)
