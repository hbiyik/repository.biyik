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
import xbmc
import os

_tdir = xbmc.translatePath("special://userdata/addon_data/script.module.abi").decode("utf-8")
if not os.path.exists(_tdir):
    os.makedirs(_tdir)

module = None


def setpath(path, fname):
    with open(os.path.join(_tdir, fname), "w") as f:
        f.write(path)


def getpath(fname):
    p = os.path.join(_tdir, fname)
    if os.path.exists(p):
        with open(p) as f:
            return f.read()


def log(txt, lvl=0):
    xbmc.log("| script.module.abi | %s | %s" % (module, txt))
