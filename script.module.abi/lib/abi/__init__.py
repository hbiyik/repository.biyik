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
import platform
import re
import sys
import os
import imp
import ctypes
import itertools
import xbmcvfs
import xbmc
import xbmcaddon

from abi import defs
from abi import utils
from abi import machine as mach


def load(addon, module, modulefile=None, ignore_py=False, ctype=False):
    machine = mach.factory(module)
    utils.module = module
    # get __addon root dir
    addon_path = xbmcaddon.Addon(addon).getAddonInfo("path").decode("utf-8")

    pysuffix = "_%s" % machine.python
    if ignore_py:
        pysuffix = ""

    # get binary directory
    for tc in machine.toolchains:
        machinepath = "%s@%s-%s%s" % (machine.os, tc, machine.architecture, pysuffix)
        base_path = os.path.join(addon_path, "bin", machinepath)
        utils.log("Searching module toolchain directory %s" % machinepath)
        if os.path.exists(base_path):
            break
    if not os.path.exists(base_path):
        msg = "Binary module is not compiled for %s" % machinepath
        utils.log(msg)
        raise ImportError(msg)
        return
    # find the module file
    if not modulefile:
        prefixes = ["", "lib"]
        suffixes = [
                    "",
                    "%s%s" % (sys.version_info[0], sys.version_info[1]),
                    "%s.%s" % (sys.version_info[0], sys.version_info[1]),
                    ]
        exts = ["pyd", "so", "dll"]
        for pre, suf, ext in itertools.product(prefixes, suffixes, exts):
            modulefile = "%s%s%s.%s" % (pre, module, suf, ext)
            base_mpath = os.path.join(base_path, modulefile)
            if os.path.exists(base_mpath):
                break
    else:
        base_mpath = os.path.join(base_path, modulefile)
    if os.path.exists(base_mpath):
        utils.log("Found module base file in path : %s" % base_mpath)
    else:
        msg = "Binary module can not be found in path %s" % base_mpath
        utils.log(msg)
        raise ImportError(msg)
        return
    # some oses do not allow importing shared files from certain directories ie: android
    # try to load from list of of directories, if there is no access right for python inter-
    # preter, use xbmcvfs to create a copy of the module in the directory that has execution
    # rights, ie: xbmc.translatePath('special://xbmc') must have execution rights since main
    # kodi binary is executed from.
    dirs = [
            base_path,
            xbmc.translatePath('special://temp').decode("utf-8"),
            "/data/data/org.xbmc.kodi/lib/",
            xbmc.translatePath('special://xbmc').decode("utf-8"),
            ]
    pname = "%s.%s.%s.db" % (machinepath, addon, modulefile)
    iscached = utils.getpath(pname)
    if iscached:
        dirs.insert(0, iscached)
    base_size = xbmcvfs.Stat(base_mpath).st_size()
    mdll = None
    ddll = None
    for d in dirs:
        utils.log("Trying to import %s from %s " % (modulefile, d))
        if not os.path.exists(d):
            utils.log("Import Directory not found skipping %s" % d)
            continue
        try:
            mpath = os.path.join(d, modulefile)
            if mpath.endswith("\\%s" % modulefile) and not mpath.endswith("\\\\%s" % modulefile):
                # workaround for windows paths
                mpath = mpath.replace("\\", "\\\\")
            if not d == base_path:
                msize = xbmcvfs.Stat(mpath).st_size()
                if os.path.exists(mpath) and not msize == base_size:
                    utils.log("Found old module. Deleting: %s, size: %s basesize: %s" % (mpath,
                                                                                    msize,
                                                                                    base_size))
                    xbmcvfs.delete(mpath)
                if not os.path.exists(mpath):
                    utils.log("Copying library %s to %s" % (modulefile, d))
                    xbmcvfs.copy(base_mpath, mpath)
            if not defs.OS_WIN == machine.os or ctype:
                mdll = ctypes.CDLL(mpath)
            if not ctype:
                ddll = imp.load_dynamic(module, mpath)
            utils.log("Successfully loaded dynamic library '%s' from '%s' is successful" % (modulefile, d))
            utils.log("Storing load path to '%s'" % pname)
            utils.setpath(d, pname)
            break
        except OSError, e:
            utils.log(repr(e))
            utils.log("%s os does not allow loading dynamic objects from %s" % (machine.os, d))
            if not d == base_path:
                utils.log("Deleting residues %s from %s" % (modulefile, d))
                xbmcvfs.delete(mpath)
    if not (mdll or ddll):
        raise OSError("%s os can not load dynamic libraries from : %s" % (machine.os, str(dirs)))
        utils.log("%s platform can not load dynamic libraries from : %s" % str(dirs))
        return
    if ctype:
        return mdll
    else:
        return ddll
