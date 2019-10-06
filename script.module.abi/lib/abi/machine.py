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
import sys
import re
import defs
import xbmc

from abi import utils


class factory(object):
    def __init__(self, module=None):
        self.os = self.detect_os()
        utils.module = module
        utils.log("Detected OS : %s" % self.os)
        self.toolchains = self.detect_tc()
        self.architecture = self.detect_ar()
        utils.log("Detected Architecture : %s" % self.architecture)
        self.python = self.detect_py()
        utils.log("Detected Python Interpreter : %s" % self.python)
        self.module = module

    def detect_os(self):
        system = platform.system().lower()
        if "windows" in system or xbmc.getCondVisibility('system.platform.windows'):
            return defs.OS_WIN
        if "linux" in system or xbmc.getCondVisibility('system.platform.linux'):
            if xbmc.getCondVisibility('system.platform.android'):
                return defs.OS_AND
            return defs.OS_LIN
        '''
        xbmc.getCondVisibility('system.platform.osx')
        xbmc.getCondVisibility('system.platform.atv2')
        xbmc.getCondVisibility('system.platform.ios')
        to-do : detect android and ios
        '''

    def detect_ar(self):
        ar = platform.architecture()[0].lower()
        mach = platform.machine().lower()
        if ar == "32bit":
            if "armv7l" in mach:
                return defs.AR_AR7
            return defs.AR_X86
        if ar == "64bit":
            return defs.AR_X64
        # to-do: detect arms

    def detect_py(self):
        ucs2 = sys.maxunicode <= 65535
        version = platform.python_version()
        if version.startswith("2.7."):
            if ucs2:
                return defs.PY_CP27M
            else:
                return defs.PY_CP27MU
        if version.startswith("2.6."):
            if ucs2:
                return defs.PY_CP26M
            else:
                return defs.PY_CP26MU

    def detect_tc(self):
        tc = None
        if self.os == defs.OS_WIN:
            tcs = ["winabi"]
            msc = re.search("MSC v\.([0-9]{4})", sys.version)
            if msc:
                msc = int(msc.group(1))
                msc = defs.msc_info[msc][1]
                tc = "vc%d" % msc
            if tc:
                tcs.insert(0, tc)
            return tcs
        if self.os == defs.OS_LIN:
            # to do: define many as per PEP513
            return ["pep513"]
        if self.os == defs.OS_AND:
            # to do: dont know much about android ndk
            return ["ndk"]
        raise OSError("Toolchain %s:%s is not supported" % (defs.os, sys.version))
