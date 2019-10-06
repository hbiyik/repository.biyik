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

import urllib2
import re
import time
import json
import os
import zipfile
import StringIO
import shutil
import sys

import htmlement

import xbmc
import xbmcgui
import traceback

from distutils.version import LooseVersion

_cannotify = LooseVersion(xbmcgui.__version__) >= LooseVersion("2.14.0")

_dom = "github.com"
_ddir = xbmc.translatePath("special://userdata/addon_data/").decode("utf-8")


def _mkdir(*args):
    p = os.path.join(*args)
    if not os.path.exists(p):
        os.makedirs(p)
    return p


_ddir = _mkdir(_ddir, "script.module.ghub", "src")


def _page(u, chunk_size=8192):
    dp = xbmcgui.DialogProgress()
    dp.create("Github", u)
    response = urllib2.urlopen(u)
    total_size = response.info().getheader('Content-Length')
    if total_size:
        try:
            total_size = int(total_size.strip())
        except Exception:
            total_size = None
    if not total_size:
        dp.update(100)
        ret = response.read()
        dp.close()
        return ret
    else:
        bytes_so_far = 0
        data_so_far = ""
        while True:
            chunk = response.read(chunk_size)
            data_so_far += chunk
            bytes_so_far += len(chunk)
            if not chunk:
                break
            if total_size:
                percent = bytes_so_far * 100 / total_size
                dp.update(percent)
        dp.close()
        return data_so_far


def _getrels(uname, rname):
    page = htmlement.fromstring(_page("https://%s/%s/%s/tags" % (_dom, uname, rname)))
    rels = page.findall(".//div[@class='Box']/div/div/div/ul")
    allrels = []
    for rel in rels:
        links = rel.findall(".//a[@class='muted-link']")
        commit = links[0].get("href").split("/")[-1]
        zipu = links[1].get("href")
        zipu = "https://" + _dom + zipu
        allrels.append([commit, zipu])
    return allrels


def _getcommits(uname, rname, branch, commit):
    if not commit:
        page = htmlement.fromstring(_page("https://%s/%s/%s/commits/%s" % (_dom, uname, rname, branch)))
        comms = [x.get("value") for x in page.findall('.//clipboard-copy')]
    else:
        comms = [commit]
    allcoms = []
    for commit in comms:
        zipu = "https://codeload.%s/%s/%s/zip/%s" % (_dom,
                                                     uname,
                                                     rname,
                                                     commit
                                                     )
        allcoms.append([commit, zipu])
    return allcoms


def _updatezip(u, tdir, rname):
    print u
    for d in os.listdir(tdir):
        p = os.path.join(tdir, d)
        if os.path.isdir(p) and d.startswith(rname):
            shutil.rmtree(p)
    zp = zipfile.ZipFile(StringIO.StringIO(_page(u)))
    zp.extractall(tdir)


def _makepack(tdir, path, rname):
    sdir = None
    for d in os.listdir(tdir):
        sdir = os.path.join(tdir, d)
        if os.path.isdir(sdir) and d.startswith(rname):
            break
    if sdir and sdir not in sys.path:
        sys.path.append(os.path.join(sdir, *path))
        return sdir


def _silentcheck(mem, callback, *args, **kwargs):
    try:
        return callback(*args, **kwargs)
    except Exception, e:
        print traceback.format_exc()
        if not mem:
            raise e


def load(uname, rname, branch, commit=None, path = [], period=24):
    """
    Loads, caches, and arranges paths for a repo from github.
    This module, downloads a github repo to 
    userdata/addon_data/scirpt.module.gub/uname/package/branch/commit
    It also updates the package automatically in a given period (24h default)
    Note that this is not a package manager and does not do any dependency check

    Example:
        import ghub

        ghub.load("hbiyik", "script.module.tinyxbmc", "master", None, ["lib"])

        #now you can safely import this module
        import boogie

    Params:
        uname: github username
        rname: repository name 
        branch: github branch (ie master), if this parameter is None, latest tagged
            version is used.
        commit: [optional,None] commit of the specified branch, if None is specified
            latest commit is fetched, if brach is None, this parameter is dismissed
        path: [optional,[]] list of directories pointing to the root directory of source
            ie, if source is in lib/src folder path should be ["lib", "src"]
        period: [optional, 24] period in hours of how frequent the repo should be checked 
            for an update

    Returns:
        None

    """
    mem = None
    bdir = _mkdir(_ddir, uname)
    if not branch:
        bdir = _mkdir(bdir, "release")
    else:
        bdir = _mkdir(bdir, "branch", branch)
    memfile = os.path.join(bdir, rname + ".json")
    if os.path.exists(memfile):
        with open(memfile) as infile:
            mem = json.load(infile)
    if mem and time.time() - mem["ts"] < period * 60 * 60:
        return _makepack(bdir, path, rname)
    else:
        dialog = xbmcgui.Dialog()
        if _cannotify:
            dialog.notification("%s:%s:%s" % (rname, uname, branch), "Updating..")
        if branch:
            ref = _silentcheck(mem, _getcommits, uname, rname, branch, commit)
            if not ref:
                return _makepack(bdir, path, rname)
        else:
            ref = _silentcheck(mem, _getrels, uname, rname)
            if not ref:
                return _makepack(bdir, path, rname)
        latest = ref[0]
        if not mem or not latest[0] == mem["latest"]:
            _updatezip(latest[1], bdir, rname)
        data = {
                "ts": time.time(),
                "latest": latest[0]
                }
        with open(memfile, 'w') as outfile:
            json.dump(data, outfile)
        if not branch:
            branch = "release"
        if _cannotify:
            dialog.notification("%s:%s:%s" % (rname, uname, branch), latest[0][:7])
        return _makepack(bdir, path, rname)
