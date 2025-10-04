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

from tinyxbmc import addon
from tinyxbmc import const
from tinyxbmc import mediaurl

from vods import addonplayerextension
from urllib import parse


class youtube(addonplayerextension):
    dropboxtoken = const.DB_TOKEN

    def geturls(self, link, headers=None):
        if not addon.has_addon('plugin.video.youtube'):
            return
        up = parse.urlparse(link)
        dom = up.netloc.lower()
        if dom == "youtube.com" or dom.startswith("www.youtube.com"):
            if up.path.startswith("/embed/"):
                vid = up.path.split("/")[2]
            else:
                vid = parse.parse_qs(up.query)["v"][0]
        elif dom in ["youtu.be", "www.youtu.be"]:
            vid = up.path[1:]
        else:
            return
        yield mediaurl.AddonUrl("plugin.video.youtube", path="play/", query={"video_id": vid})


class dailymotion(addonplayerextension):
    dropboxtoken = const.DB_TOKEN

    def geturls(self, link, headers=None):
        if not addon.has_addon('plugin.video.dailymotion'):
            return
        up = parse.urlparse(link)
        dom = up.netloc.lower()
        if "dailymotion.com" not in dom:
            return
        vid = up.path.split("/")[-1]
        yield mediaurl.AddonUrl("plugin.video.dailymotion", url=vid, mode="playLiveVideo")
