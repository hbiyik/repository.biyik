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
import datetime
import vods
import htmlement
import json

from tinyxbmc.net import kodiurl


class motorsports(vods.showextension):
    title = u"Motorsports.tv"
    domain = "https://eu.motorsport.tv"
    uselinkplayers = False
    useaddonplayers = False

    def getcategories(self):
        self.additem("Racing Series", ("racing", "racingList", "racingSeries"))
        self.additem("Programs", ("program", "programList", "program"))
        self.additem("Live", ("livestream", None, None))

    def getshows(self, cat, keyw=None):
        if cat:
            cat, sub1, sub2 = cat
            if cat == "livestream":
                self.additem("Live Now", ("/livestream", {}, "livenow"), {}, {})
                self.additem("Live Upcoming", ("/livestream", {}, "upcoming"), {}, {})
            else:
                js = self.getjson(self.domain + "/" + cat)
                for itemid, item in js[sub1]["response"]["entities"][sub2].iteritems():
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

    def getjson(self, uri):
        page = self.download(uri)
        return json.loads(re.search("window\.APP_STATE\=(.+?)<\/script>", page).group(1))

    def epiimg(self, episode):
        if "images" in episode and "retina" in episode["images"]:
            return episode["images"]["retina"]
        elif "contentImages" in episode and "retina" in episode["contentImages"]:
            return episode["contentImages"]["retina"]
        elif "coverImages" in episode and "retina" in episode["coverImages"]:
            return episode["coverImages"]["retina"]
        else:
            return""

    def epilink(self, episode):
        if "link" in episode:
            return True, episode["link"]
        elif "videoFile" in episode:
            links = []
            suburl = episode["videoFile"]["path"]
            if suburl.startswith("http://") or suburl.startswith("https://"):
                links.append(kodiurl(suburl, headers={"Referer": self.domain}))
            else:
                url = "%s/%s/playlist.m3u8" % (episode["videoBaseUrl"],
                                               suburl)
                links.append(kodiurl(url, headers={"Referer": self.domain}))
                url = "%s/%s/playlist.m3u8" % (episode["videoBaseUrlUnsecure"],
                                               suburl)
                links.append(kodiurl(url, headers={"Referer": self.domain}))
            return False, links

    def epidate(self, episode):
        key = "date"
        if episode.get("episodeDate"):
            key = "episodeDate"
        dt = episode.get(key)
        if not dt:
            return datetime.datetime(1970, 1, 1)
        if isinstance(dt, (int, float)):
            return datetime.datetime.fromtimestamp(float(dt)/1000)
        else:
            return datetime.datetime.strptime(episode[key][:-6], "%Y-%m-%dT%H:%M:%S")

    def getepisodes(self, show=None, sea=None):
        if show is None:
            uri = ""
            cat = None
            art = {}
        else:
            uri, art, cat = show
        js = self.getjson(self.domain + uri)

        if cat == "racing":
            episodes = [x[1] for x in js["racingItem"]["response"]["entities"]["episode"].iteritems()]
        elif cat == "program":
            episodes = []
            for carousel in js["programItem"]["response"]["carousels"]:
                episodes.extend(carousel["episodes"])
        elif cat in ["upcomin", "livenow"]:
            episodes = js["livestreamSchedule"]["data"]
        else:
            episodes = []
            for data in js["home"]["data"]:
                if data["title"] in ["liveNow", "recentlyAdded"]:
                    episodes.extend(data["slides"])
        # fix date formatting and convert to datetime objects
        for episode in episodes:
            episode["date"] = self.epidate(episode)

        for episode in sorted(episodes, key=lambda i: i["date"], reverse=True):
            titles = []
            if episode.get("livestream") or episode.get("type") == "livestream":
                if episode.get("livestreamRecordingStatus") == "STATUS_RECORD_NOT_STARTED":
                    if cat == "upcoming":
                        titles.append("[UPCOMING]")
                    else:
                        continue
                titles.append("[LIVE]")
                titles.append("[%s]" % episode["program"]["title"])

            epiart = art.copy()
            epiart["icon"] = epiart["thumb"] = epiart["poster"] = self.epiimg(episode)
            try:
                titles.append(episode["date"].strftime("%d.%m.%Y %H:%M"))
            except Exception:
                pass
            if episode.get("subtitle"):
                titles.append(episode["subtitle"])
            titles.append(episode[u"title"])
            self.additem(" - ".join(titles), self.epilink(episode), None, epiart)

    def geturls(self, url):
        resolve, url = url
        if not resolve:
            for u in url:
                yield u
        if resolve:
            url = self.domain + url
            tree = htmlement.fromstring(self.download(url))
            video = tree.find(".//video/source")
            if video is not None:
                yield kodiurl(video.get("src"), headers={"Referer": url})
