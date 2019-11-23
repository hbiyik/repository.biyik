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
import cookielib
import os
import time
import re
import urllib
import urlparse
import copy
from datetime import datetime, timedelta
from email.utils import parsedate, formatdate
import calendar


from cachecontrol import CacheControlAdapter
from cachecontrol.heuristics import BaseHeuristic
from cachecontrol.caches import HayCache as Cache

from tinyxbmc import addon
from tinyxbmc import tools
from tinyxbmc import const

__profile = addon.get_commondir()
__cache = Cache(const.HTTPCACHEHAY)
__cookie = cookielib.LWPCookieJar(filename=os.path.join(__profile, const.COOKIEFILE))
try:
    __cookie.load()
except Exception:
    pass

sessions = {}


def getsession(timeframe):
    if timeframe in sessions:
        return sessions[timeframe]
    else:
        sess = requests.Session()
        sess.cookies = __cookie
        if timeframe == 0:
            sess.mount("http://", CacheControlAdapter(cache=__cache))
            sess.mount("https://", CacheControlAdapter(cache=__cache))
        else:
            sess.mount("http://", CacheControlAdapter(cache=__cache, heuristic=timecache(timeframe)))
            sess.mount("https://", CacheControlAdapter(cache=__cache, heuristic=timecache(timeframe)))
        sessions[timeframe] = sess
        return sess


def tokodiurl(url, domain=None, headers=None):
    if not headers:
        headers = {}
    if domain:
        domain = urlparse.urlparse(domain).netloc
    else:
        domain = urlparse.urlparse(url).netloc
    cookiestr = ""
    for cookie in __cookie:
        if cookie.domain and domain and domain in cookie.domain:
            cookiestr += ";%s=%s" % (cookie.name, cookie.value)
    if not cookiestr == "":
        headers["Cookie"] = headers.get("cookie", headers.get("Cookie", "")) + cookiestr
    if url.startswith("http://") or url.startswith("https://"):
        url += "|" + urllib.urlencode(headers)
    return url


def fromkodiurl(url):
    parts = url.split("|")
    url = parts[0]
    if len(parts) == 2:
        headers = dict(urlparse.parse_qsl(parts[1]))
    else:
        headers = None
    return url, headers


def http(url, params=None, data=None, headers=None, timeout=5, json=None, method="GET",
         referer=None, useragent=None, encoding=None, verify=None, proxies=None, cache=0, text=True):
    ret = None
    if url.startswith("//"):
        url = "http:%s" % url
    if not headers:
        headers = {}
    if useragent:
        headers["User-Agent"] = useragent
    if referer:
        headers["Referer"] = referer
    kwargs = {"params": params,
              "data": data,
              "headers": headers,
              "timeout": timeout,
              "json": json,
              "verify": verify,
              "proxies": proxies
              }
    response = getsession(cache).request(method, url, **kwargs)
    response = cloudflare(response, **kwargs)
    if not text:
        return response
    if method == "HEAD":
        return response
    if json:
        ret = response.json()
    else:
        if encoding:
            text = response.content.decode(encoding)
        else:
            text = response.text
        text = tools.unescapehtml(text)
        ret = unicode(text)
    getsession(cache).cookies.save(ignore_discard=True)
    return ret


def cloudflare(response, **kwargs):
    def __extract_js(body):
        js = re.search(r"(var s,t,o,p,b,r,e,a,k,i,n,g,f,.+?;)", body).group(1)
        js += re.search(r";(.+?)\s?\+\s?t\.length", body).group(1)
        js = re.sub(r'a\.value\s?\=\s?\+', '', js)
        return js + ";"

    if (response.status_code == 503 and "cloudflare" in response.headers.get("Server")
            and b"jschl_vc" in response.content and b"jschl_answer" in response.content):
        import js2py
        body = response.text
        parsed_url = urlparse.urlparse(response.url)
        domain = parsed_url.netloc
        submit_url = "%s://%s/cdn-cgi/l/chk_jschl" % (parsed_url.scheme, domain)
        cfkwargs = copy.deepcopy(kwargs)
        for key in ["headers", "params"]:
            if not isinstance(cfkwargs[key], dict):
                cfkwargs[key] = {}
        cfkwargs["headers"]["Referer"] = response.url
        cfkwargs["params"]["jschl_vc"] = re.search(r'name="jschl_vc" value="(\w+)"', body).group(1)
        cfkwargs["params"]["pass"] = re.search(r'name="pass" value="(.+?)"', body).group(1)
        js = __extract_js(body)
        jseval = float(js2py.eval_js(js))
        cfkwargs["params"]["jschl_answer"] = str(jseval + len(domain))
        method = response.request.method
        cfkwargs["allow_redirects"] = False
        t = 5
        from tinyxbmc import gui
        gui.notify("CloudFlare", "Waiting %d seconds" % t, False)
        time.sleep(t)
        redirect = getsession(0)(method, submit_url, **cfkwargs)
        return getsession(0).request(method, redirect.headers["Location"], **kwargs)
    return response


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
