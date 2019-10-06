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
from vods import linkplayerextension

from libplayer import proxydt
from libplayer import proxyisatty
from libplayer import getconfig

import ghub
import sys
import datetime
import urllib


class ydl(linkplayerextension):
    title = "Youtube DL Link Extension"

    def init(self):
        sys.stderr.isatty = proxyisatty
        datetime.datetime = proxydt
        uname, branch, commit = getconfig("ydl")
        ghub.load(uname, "youtube-dl", branch, commit)
        import youtube_dl as ydl
        self.ydl = ydl
        self.ies = ydl.extractor.gen_extractors()

    def getresults(self, result):
        headers = result.get("http_headers", {})
        headers["Referer"] = result.get("webpage_url", "")
        suffix = "|" + urllib.urlencode(headers)
        for k in ('entries', "requested_formats"):
            if k in result:
                # Can be a playlist or a list of videos
                for res in result[k]:
                    if "url" in res:
                        yield res["url"] + suffix
        if "url" in result:
            # Just a video
            yield result["url"] + suffix

    def geturls(self, link):
        if "youtube" in link or "youtu.be" in link:
            yield
        supported = False
        for ie in self.ies:
            if ie.suitable(link) and ie.IE_NAME != 'generic':
                supported = True
                break
        if not supported:
            yield
        ytb = self.ydl.YoutubeDL({'format': 'bestvideo+bestaudio/best',
                                  "quiet": True,
                                  "nocheckcertificate": True})
        ytb._ies = [ie]
        with ytb:
            result = ytb.extract_info(str(link), download=False)

        for url in self.getresults(result):
            yield url
