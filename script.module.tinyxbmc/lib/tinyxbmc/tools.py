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
import traceback
import re
import xbmc
import xbmcvfs
import os
import datetime
import time

from xml.dom import minidom


def safeiter(iterable):
    if hasattr(iterable, "next"):
        while True:
            try:
                yield iterable.next()
            except StopIteration:
                break
            except Exception:
                print traceback.format_exc()


def dynamicret(iterable):
    for ret in iterable:
        if isinstance(ret, (str, unicode)):
            yield ret, {}, {}
        elif isinstance(ret, (tuple, list)):
            lsize = len(ret)
            if lsize == 1:
                yield ret[0], {}, {}
            if lsize == 2:
                yield ret[0], ret[1], {}
            if lsize == 3:
                yield ret
        else:
            yield None, None, None


def strip(txt, tags=False):
    if tags:
        txt = re.sub('<[^<]+?>', '', txt)
    txt = re.sub("(\t|\n)", " ", txt)
    txt = re.sub("\s+", " ", txt)
    return txt.strip()


def readdom(xname):
    try:
        f = open(xname, "r")
        data = f.read()
        f.close()
        '''ignore whitespace before '<' character. some android versions
        suspected to put chars in front of xmls'''
        c = 0
        for c in range(len(data)):
            if data[c] == "<":
                break
        return minidom.parseString(data[c:])
    except Exception:
        return


def unescapehtml(string):
    entity_re = re.compile("&(#?)(\d{1,5}|\w{1,8});")

    def substitute_entity(match):
        from htmlentitydefs import name2codepoint as n2cp
        ent = match.group(2)
        if match.group(1) == "#":
            try:
                return unichr(int(ent))
            except Exception:
                return ent
        else:
            cp = n2cp.get(ent)

            if cp:
                return unichr(cp)
            else:
                return match.group()

    return entity_re.subn(substitute_entity, string)[0]


def getskinview(typ="video"):
    xmls = {"video": "MyVideoNav.xml",
            "audio": "MyMusicNav.xml",
            "image": "MyPics.xml"
            }
    _skindir = xbmc.translatePath('special://skin/').decode("utf-8")
    res = readdom(os.path.join(_skindir, "addon.xml"))
    drc = res.getElementsByTagName("res")[0].getAttribute("folder")
    res.unlink()
    navxml = os.path.join(_skindir, drc, xmls[typ])
    res = readdom(navxml)
    views = res.getElementsByTagName("views")[0].lastChild.data.split(",")
    res.unlink()
    for view in views:
        label = xbmc.getInfoLabel("Control.GetLabel(%s)" % view)
        if not (label == '' or label is None):
            break
    return int(view)


def relpath(path, *paths):
    if not os.path.isdir(path):
        path = os.path.dirname(os.path.realpath(path))
    else:
        path = os.path.realpath(path)
    return os.path.realpath(os.path.join(path, *paths))


def elementsrc(element, exclude=[]):
    if element in exclude:
        return ""
    text = element.text or ''
    for subelement in element:
        text += elementsrc(subelement, exclude)
    text += element.tail or ''
    return text


class File(object):
    def __init__(self, p, m="r"):
        self.f = xbmcvfs.File(p.encode("utf-8"), m)

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def __del__(self, *args, **kwargs):
        self.close()

    def read(self, *args, **kwargs):
        return self.f.read(*args, **kwargs)

    def readBytes(self, *args, **kwargs):
        return self.f.readBytes(*args, **kwargs)

    def seek(self, *args, **kwargs):
        return self.f.seek(*args, **kwargs)

    def size(self, *args, **kwargs):
        return self.f.size(*args, **kwargs)

    def write(self, *args, **kwargs):
        return self.f.write(*args, **kwargs)

    def close(self, *args, **kwargs):
        return self.f.close(*args, **kwargs)


class Stat(object):
    def __init__(self, p):
        self.s = xbmcvfs.Stat(p.encode("utf-8"))

    def st_atime(self, *args, **kwargs):
        return self.s.st_atime(*args, **kwargs)

    def st_ctime(self, *args, **kwargs):
        return self.s.st_ctime(self, *args, **kwargs)

    def st_dev(self, *args, **kwargs):
        return self.s.st_dev(self, *args, **kwargs)

    def st_gid(self, *args, **kwargs):
        return self.s.st_gid(self, *args, **kwargs)

    def st_ino(self, *args, **kwargs):
        return self.s.st_ino(self, *args, **kwargs)

    def st_mode(self, *args, **kwargs):
        return self.s.st_mode(self, *args, **kwargs)

    def st_mtime(self, *args, **kwargs):
        return self.s.st_mtime(self, *args, **kwargs)

    def st_nlink(self, *args, **kwargs):
        return self.s.st_nlink(self, *args, **kwargs)

    def st_size(self, *args, **kwargs):
        return self.s.st_size(self, *args, **kwargs)

    def st_uid(self, *args, **kwargs):
        return self.s.st_uid(self, *args, **kwargs)


def mkdirs(path):
    xbmcvfs.mkdirs(path.encode("utf-8"))


def builtin(function, wait=False):
    return xbmc.executebuiltin(function, wait)


def kodiversion():
    return int(xbmc.getInfoLabel('System.BuildVersion')[:2])


class tz_local(datetime.tzinfo):
    _unixEpochOrdinal = datetime.datetime.utcfromtimestamp(0).toordinal()

    def dst(self, dt):
        return datetime.timedelta(0)

    def utcoffset(self, dt):
        t = (dt.toordinal() - self._unixEpochOrdinal)*86400 + dt.hour*3600 + dt.minute*60 + dt.second + time.timezone
        utc = datetime.datetime(*time.gmtime(t)[:6])
        local = datetime.datetime(*time.localtime(t)[:6])
        return local - utc


class tz_utc(datetime.tzinfo):
    _unixEpochOrdinal = datetime.datetime.utcfromtimestamp(0).toordinal()

    def dst(self, dt):
        return datetime.timedelta(0)

    def utcoffset(self, dt):
        return self.dst(dt)


def isstub():
    return hasattr(xbmc, "__kodistubs__") and xbmc.__kodistubs__


def language(_format=xbmc.ISO_639_1, region=False):
    try:
        return xbmc.getLanguage(_format, region)
    except Exception:
        return xbmc.getLanguage()
