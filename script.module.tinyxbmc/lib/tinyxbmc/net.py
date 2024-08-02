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
import six
import calendar
from six.moves.urllib import parse
from six.moves import http_cookiejar
from datetime import datetime, timedelta
from email.utils import parsedate, formatdate

from cachecontrol import CacheControlAdapter

from cachecontrol.heuristics import BaseHeuristic
from cachecontrol.caches import HayCache as Cache

from tinyxbmc import addon
from tinyxbmc import const

if six.PY3:
    import html
else:
    from six.moves import html_parser
    html = html_parser.HTMLParser()

if addon.has_addon("plugin.program.aceengine"):
    addon.depend_addon("plugin.program.aceengine")
    import aceengine
else:
    aceengine = None

__profile = addon.get_commondir()
__cache = Cache(const.HTTPCACHEHAY)

sessions = {}


def loadcookies():
    cpath = os.path.join(__profile, const.COOKIEFILE)
    cookie = http_cookiejar.LWPCookieJar(filename=cpath)
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


def tokodiurl(url, domain=None, headers=None, pushverify=None, pushua=None):
    if not headers:
        headers = {}
    if domain:
        domain = parse.urlparse(domain).netloc
    else:
        domain = parse.urlparse(url).netloc
    if "|" in url:
        _, oldheaders = fromkodiurl(url)
        oldheaders.update(headers)
        headers = oldheaders
    cookiestr = ""
    for cookie in cookicachelist:
        if domain in cookie.domain:
            cookiestr += ";%s=%s" % (cookie.name, cookie.value)
    if cookiestr:
        headers["Cookie"] = headers.get("cookie", headers.get("Cookie", "")) + cookiestr
    if headers is None:
        headers = {"User-agent": const.USERAGENT}
    headerkeys = [x.lower() for x in headers.keys()]
    if pushua is not None and "user-agent" not in headerkeys:
        headers["User-agent"] = const.USERAGENT
    if pushverify is not None and "verifypeer" not in headerkeys:
        headers["verifypeer"] = pushverify
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
    if not headers:
        headers = {}
    if useragent:
        headers["User-Agent"] = useragent
    if referer:
        headers["Referer"] = referer
    if "user-agent" not in [x.lower() for x in headers.keys()]:
        headers["User-Agent"] = const.USERAGENT
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
        ret = six.text_type(html.unescape(text))
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
