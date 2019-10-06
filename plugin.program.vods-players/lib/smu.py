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
from tinyxbmc import tools
from tinyxbmc import hay
from tinyxbmc import gui

from vods import linkplayerextension

from libplayer import getconfig

import ghub
import os
import re
import shutil
import traceback
import json


def patchsmu(smudir):
    # a very dirty hack to make smu work portable, not happy with this :(
    def getstr(content):
        r = re.search("<settings>(.*?)</settings>", content, re.DOTALL)
        if r:
            return r.group(1)
        else:
            return ""

    with hay.stack("smupatch") as smuhay:
        smupatch = smuhay.find("smupatch").data
        with open(os.path.join(smudir, "..", "script.module.resolveurl.json")) as vf:
            versioncommit = json.load(vf)
        versioncommit = versioncommit.get("latest")
        try:
            xmlstat = os.path.getsize(os.path.join(smudir, "settings.xml"))
        except Exception:
            xmlstat = None
        pldir = addon.get_addon("plugin.program.vods-players").getAddonInfo("path")
        if not smupatch.get("versioncommit") == versioncommit: 
            # first remove xbmcaddon referenced to script.module.urlresolver
            files = [
                (["lib", "resolveurl", "lib", "log_utils.py"], 1),
                (["lib", "resolveurl", "lib", "kodi.py"], 1),
                (["lib", "resolveurl", "common.py"], 2),
                ]
            for fpaths, patchtype in files:
                fpath = os.path.join(smudir, *fpaths)
                with open(fpath, "r") as f:
                    contents = f.read()
                if patchtype == 1:
                    pattern = "script\.module\.resolveurl"
                    sub = "plugin.program.vods-players"
                elif patchtype == 2:
                    pattern = "settings_file \= os\.path\.join\(addon_path, 'resources', 'settings.xml'\)"
                    sub = "settings_file = os.path.join(os.path.dirname(__file__), '..', '..', 'settings.xml')"
                if re.search(pattern, contents):
                    with open(fpath, "w") as f:
                        f.write(re.sub(pattern, sub, contents))

            # synchronize resources folder with xbmcvfs in case of permission problem
            for root, folders, files in os.walk(os.path.join(smudir, "resources")):
                relfolder = os.path.relpath(root, smudir)
                for folder in folders:
                    tools.mkdirs(os.path.join(pldir, relfolder, folder))
                for f in files:
                    sfile = os.path.join(smudir, relfolder, f)
                    tfile = os.path.join(pldir, relfolder, f)
                    with tools.File(sfile) as sfileo:
                        with tools.File(tfile, "w") as tfileo:
                            tfileo.write(sfileo.read())
            smupatch["versioncommit"] = versioncommit
            smuhay.throw("smupatch", smupatch)
            tools.builtin("UpdateLocalAddons()")
            gui.ok("URL Resolvers", "SMU has just been updated",
                   "some changes will be active on kodi restart")

        if not smupatch.get("xmlstat") == xmlstat:
            # merge smu settings.xml with current settings.xml
            smuxmlp = os.path.join(smudir, "settings.xml")
            plxmlop = os.path.join(pldir, "resources", "settings_orig.xml")
            plxmlp = os.path.join(pldir, "resources", "settings.xml")
            smupatch["xmlstat"] = xmlstat
            smuhay.throw("smupatch", smupatch)
            with tools.File(smuxmlp, "r") as smuxml:
                with tools.File(plxmlop, "r") as plxmlo:
                    with tools.File(plxmlp, "w") as plxml:
                        try:
                            plxml.write('<?xml version="1.0" ?><settings>%s%s</settings>' %
                                        (getstr(plxmlo.read()), getstr(smuxml.read())))
                        except Exception:
                            print traceback.format_exc()
                            shutil.copyfile(plxmlop, plxmlp)


class smu(linkplayerextension):
    builtin = "PlayMedia(%s)"

    def init(self):
        uname, branch, commit = getconfig("smu")
        ghub.load("bstrdsmkr", "script.module.cryptopy", "master", None, ["lib"])
        patchsmu(ghub.load(uname, "script.module.resolveurl", branch, commit, ["lib"]))
        from resolveurl import hmf
        self.hmf = hmf.HostedMediaFile

    def geturls(self, link):
        hmf = self.hmf(link, include_universal=False)
        ret = hmf.resolve()
        yield ret
