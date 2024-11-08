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
import service
from sublib import utils

REMOTE_DBG = False

if REMOTE_DBG:
    import sys
    pdevpath = "/home/boogie/.p2/pool/plugins/org.python.pydev.core_9.3.0.202203051235/pysrc/"
    sys.path.append(pdevpath)
    import pydevd  # @UnresolvedImport
    pydevd.settrace(REMOTE_DBG, stdoutToServer=True, stderrToServer=True, suspend=False)

service.turkcealtyazi(utils.mozilla)
