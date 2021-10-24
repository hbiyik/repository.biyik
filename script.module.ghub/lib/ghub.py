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

import time
import json
import os
import zipfile
import shutil
import sys
import htmlement
from six.moves.urllib import request
from six import PY2
import xbmc
import traceback


if PY2:
    from StringIO import StringIO as io
else:
    from io import BytesIO as io


_dom = "github.com"

if PY2:
    _ddir = xbmc.translatePath("special://userdata/addon_data/").decode("utf-8")
else:
    _ddir = xbmc.translatePath("special://userdata/addon_data/")


def _mkdir(*args):
    p = os.path.join(*args)
    if not os.path.exists(p):
        os.makedirs(p)
    return p


_ddir = _mkdir(_ddir, "script.module.ghub", "src")


def _page(u):
    response = request.urlopen(u)
    return response.read()


def _getrels(uname, rname):
    page = htmlement.fromstring(_page("https://%s/%s/%s/tags" % (_dom, uname, rname)))
    rels = page.findall(".//div[@class='Box']/div/div/div/.//ul")
    allrels = []
    for rel in rels:
        commit = None
        zipu = None
        for a in rel.findall(".//a"):
            href = a.get("href")
            if href and href.endswith(".zip"):
                zipu = "https://" + _dom + href
            if href and "/commit/" in href:
                commit = href.split("/")[-1]
        if zipu and commit:
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
    for d in os.listdir(tdir):
        p = os.path.join(tdir, d)
        if os.path.isdir(p) and d.startswith(rname):
            shutil.rmtree(p)
    zp = zipfile.ZipFile(io(_page(u)))
    zp.extractall(tdir)


def _load(uname, rname, branch, commit, path, period):
    mem = None
    bdir = _mkdir(_ddir, uname)

    # load memory file
    if branch:
        bdir = _mkdir(bdir, "branch", branch)
    else:
        bdir = _mkdir(bdir, "release")
    memfile = os.path.join(bdir, rname + ".json")
    if os.path.exists(memfile):
        with open(memfile) as infile:
            mem = json.load(infile)

    # check if we need to update
    if mem and time.time() - mem["ts"] < period * 60 * 60:
        print("GITHUB: INFO: Using Existing, no need to check: %s Repo:%s Branch:%s Commit: %s" % (uname, rname, branch, commit))
        return bdir
    else:
        # get latest commits
        try:
            if branch:
                ref = _getcommits(uname, rname, branch, commit)
            else:
                ref = _getrels(uname, rname)
        except Exception:
            print("GITHUB: WARNING: Can not get latest meta: User:%s Repo:%s Branch:%s Commit: %s" % (uname, rname, branch, commit))
            print(traceback.format_exc())
            return

        # download new package, extract and update the memory file
        lcommit, zipu = ref[0]
        if not mem or not lcommit == mem["latest"]:
            print("GITHUB: INFO: Updating to commit %s->%s for %s Repo:%s Branch:%s Commit: %s" % (lcommit, zipu,
                                                                                                   uname, rname, branch, commit))
            _updatezip(zipu, bdir, rname)
            data = {"ts": time.time(),
                    "latest": lcommit
                    }
            with open(memfile, 'w') as outfile:
                json.dump(data, outfile)
        return bdir


def load(uname, rname, branch, commit=None, path=None, period=24):
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
    if not path:
        path = []
    bdir = _load(uname, rname, branch, commit, path, period)
    # prepare the path
    if bdir:
        sdir = None
        for d in os.listdir(bdir):
            sdir = os.path.join(bdir, d)
            if os.path.isdir(sdir) and d.startswith(rname):
                break
        if sdir and sdir not in sys.path:
            sys.path.append(os.path.join(sdir, *path))
        return sdir
