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
import datetime
import time
from tinyxbmc import addon


def proxyisatty():
    return False


class proxydt(datetime.datetime):
    def __init__(self, *args, **kwargs):
        super(proxydt, self).__init__(*args, **kwargs)

    @staticmethod
    def strptime(date_string, fmt):
        return datetime.datetime(*(time.strptime(date_string, fmt)[0:6]))


def getconfig(prefix):
    setting = addon.kodisetting("plugin.program.vods-players")
    uname = setting.getstr("%s_uname" % prefix)
    source = setting.getstr("%s_source" % prefix)
    branch = setting.getstr("%s_branch" % prefix)
    bsource = setting.getstr("%s_branch_source" % prefix)
    commit = setting.getstr("%s_commit" % prefix)
    if source == "Latest Release":
        branch = None
    if commit.lower().strip() == "latest":
        commit = None
    if bsource == "Latest Commit":
        commit = None
    return uname, branch, commit
