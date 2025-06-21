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
import requests
import os
import calendar
import html
from urllib import parse
from http import cookiejar
from datetime import datetime, timedelta
from email.utils import parsedate, formatdate

from cachecontrol import CacheControlAdapter

from cachecontrol.heuristics import BaseHeuristic
from cachecontrol.caches import HayCache as Cache

from tinyxbmc import addon
from tinyxbmc import const

__profile = addon.get_commondir()
__cache = Cache(const.HTTPCACHEHAY)

sessions = {}


def loadcookies():
    cpath = os.path.join(__profile, const.COOKIEFILE)
    cookie = cookiejar.LWPCookieJar(filename=cpath)
    try:
        if not os.path.exists(cpath):
            cookie.save()
        cookie.load()
    except Exception:
        pass
    return cookie

# caching cookies may cause issues when http method is called from container.download
# and module.http, since they will use different cookijars, therefore always
# container.download method to have a cookie managed session


cookicache = loadcookies()
cookicachelist = list(cookicache)


def getsession(seskey):
    if seskey in sessions:
        return sessions[seskey]
    else:
        sess = requests.Session()
        sess.cookies = cookicache
        if seskey is None:
            seskey = -1
        elif seskey == 0:
            sess.mount("http://", CacheControlAdapter(cache=__cache))
            sess.mount("https://", CacheControlAdapter(cache=__cache))
        else:
            pass
            sess.mount("http://", CacheControlAdapter(cache=__cache,
                                                      heuristic=timecache(seskey),
                                                      cacheable_methods=("GET", "POST")))
            sess.mount("https://", CacheControlAdapter(cache=__cache,
                                                       heuristic=timecache(seskey),
                                                       cacheable_methods=("GET", "POST")))
        sessions[seskey] = sess
        return sess


def makeheader(url=None, headers=None, referer=None, useragent=None, pushnoverify=False, pushua=False, pushcookie=False):
    newheaders = {}
    isurl_remote = url and url.startswith("http://") or url.startswith("https://")
    useragent = useragent or const.USERAGENT

    # lowercase for easier parsing
    if headers:
        for k, v in headers.items():
            newheaders[k.lower()] = v

    # get existing kodiurl headers
    if url and "|" in url:
        _, oldheaders = fromkodiurl(url)
        for k, v in oldheaders.items():
            newheaders[k.lower()] = v

    if not isurl_remote:
        return newheaders

    # push cookies
    if url and pushcookie:
        domain = parse.urlparse(url).netloc
        if not domain == "":
            cookiestr = newheaders.get("cookies", "")
            for cookie in cookicachelist:
                if domain in cookie.domain:
                    cookiestr += ";%s=%s" % (cookie.name, cookie.value)
            newheaders["cookies"] = cookiestr

    # push user agent
    if pushua and "user-agent" not in newheaders:
        newheaders["user-agent"] = useragent

    # push verify peer
    if pushnoverify and "verifypeer" not in newheaders:
        newheaders["verifypeer"] = "false"

    if referer and "referer" not in newheaders:
        newheaders["referer"] = referer

    return newheaders


def tokodiurl(url, headers=None, pushnoverify=True, pushua=True, pushcookie=True, useragent=None):
    headers = makeheader(url, headers=headers, useragent=useragent,
                         pushnoverify=pushnoverify, pushua=pushua, pushcookie=pushcookie)
    strheaders = parse.urlencode(headers)
    if strheaders:
        url += "|" + parse.urlencode(headers)
    return url


def fromkodiurl(url):
    parts = url.split("|")
    url = parts[0]
    if len(parts) == 2:
        headers = dict(parse.parse_qsl(parts[1]))
    else:
        headers = None
    return url, headers


def http(url, params=None, data=None, headers=None, timeout=5, json=None, method="GET",
         referer=None, useragent=None, encoding=None, verify=None, stream=None, proxies=None, cache=10, text=True):
    ret = None
    if url.startswith("//"):
        url = "http:%s" % url
    headers = makeheader(url, headers=headers, referer=referer, useragent=useragent,
                         pushua=True, pushcookie=False, pushnoverify=False)
    kwargs = {"params": params,
              "data": data,
              "headers": headers,
              "timeout": timeout,
              "json": json,
              "verify": verify,
              "stream": stream,
              "proxies": proxies
              }
    session = getsession(cache)
    response = session.request(method, url, **kwargs)
    try:
        session.cookies.save(ignore_discard=True)
    except Exception:
        pass
    if not text:
        return response
    if method == "HEAD":
        return response
    if json is not None:
        ret = response.json()
    else:
        if encoding:
            text = response.content.decode(encoding)
        else:
            text = response.text
        ret = str(html.unescape(text))
    return ret


class timecache(BaseHeuristic):

    def __init__(self, timeframe):
        self.timeframe = timeframe

    def update_headers(self, response):
        date = parsedate(response.headers['date'])
        expires = datetime(*date[:6]) + timedelta(minutes=self.timeframe)
        return {
            'expires': formatdate(calendar.timegm(expires.timetuple())),
            'cache-control': 'public',
        }

    def warning(self, response):
        msg = 'Automatically cached! Response is Stale.'
        return '110 - "%s"' % msg


def absurl(url, fromurl):
    if url.startswith("https://") or url.startswith("http://"):
        return url
    else:
        up = parse.urlparse(fromurl)
        if url.startswith("//"):
            return "%s:%s" % (up.scheme, url)
        elif url.startswith("/"):
            return "%s://%s%s" % (up.scheme, up.netloc, url)
        else:
            if up.path == "/" or up.path == "":
                return "%s://%s/%s" % (up.scheme, up.netloc, url)
            else:
                return "%s://%s%s/%s" % (up.scheme, up.netloc, up.path, url)
