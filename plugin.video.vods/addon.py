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

_profile = False
_debugger = False

if _profile:
    import cProfile
    pr = cProfile.Profile()
    pr.enable()

import os
from tinyxbmc import addon
from containers import index

index.index()
if _profile:
    pr.disable()
    pr.dump_stats(os.path.join(addon.get_addondir(), "profile.dump"))
