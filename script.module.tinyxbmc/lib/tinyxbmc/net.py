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
import time
import re
import six
import traceback
from six.moves.urllib import parse
from six.moves import http_cookiejar
from six.moves import input
import copy
from datetime import datetime, timedelta
from email.utils import parsedate, formatdate
import calendar


import ghub
from cachecontrol import CacheControlAdapter
from hyper.contrib import HTTP20Adapter

from cachecontrol.heuristics import BaseHeuristic
from cachecontrol.caches import HayCache as Cache

from tinyxbmc import addon
from tinyxbmc import tools
from tinyxbmc import const
from tinyxbmc.distversion import LooseVersion

__profile = addon.get_commondir()
__cache = Cache(const.HTTPCACHEHAY)

sessions = {}
http2adapter = HTTP20Adapter()


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
        if seskey == "http2":
            sess.mount("http://", http2adapter)
            sess.mount("https://", http2adapter)
        elif seskey is None:
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
    if url.startswith("http://") or url.startswith("https://"):
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
         referer=None, useragent=None, encoding=None, verify=None, stream=None, proxies=None, cache=10, text=True, http2=False):
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
    if http2:
        session = getsession("http2")
    else:
        session = getsession(cache)
    response = session.request(method, url, **kwargs)
    response = cloudflare(session, response, None, **kwargs)
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
        ret = six.text_type(tools.unescapehtml(text))
    return ret


def cloudflare(session, response, previous, **kwargs):
    def __extract_js(body):
        js = re.search(r"(var s,t,o,p,b,r,e,a,k,i,n,g,f,.+?;)", body).group(1)
        js += re.search(r";(.+?)\s?\+\s?t\.length", body).group(1)
        js = re.sub(r'a\.value.+', '', js)
        return js + ";"

    def __redirect_clf(redirect, previous, **kwargs):
        redirect_url = redirect.headers.get("Location")
        if redirect_url is None:
            return cloudflare(redirect, previous, **kwargs)
        elif redirect_url.startswith("/"):
            redirect_url = "%s://%s%s" % (parsed_url.scheme, domain, redirect_url)
        kwargs["method"] = method
        kwargs["text"] = False
        return http(redirect_url, **kwargs)

    if (response.status_code == 503 and "cloudflare" in response.headers.get("Server") and
            b"jschl_vc" in response.content and b"jschl_answer" in response.content):
        if previous == "js":
            return response
        else:
            previous = "js"
        import js2py
        body = response.text
        parsed_url = parse.urlparse(response.url)
        domain = parsed_url.netloc
        action = re.search("action=(?:\"|')(.+?)(?:\"|')", body)
        submit_url = "%s://%s%s" % (parsed_url.scheme, domain, action.group(1))
        cfkwargs = copy.deepcopy(kwargs)
        for key in ["headers", "data"]:
            if not isinstance(cfkwargs[key], dict):
                cfkwargs[key] = {}
        cfkwargs["headers"]["Referer"] = response.url
        cfkwargs["data"]["jschl_vc"] = re.search(r'name="jschl_vc" value="(\w+)"', body).group(1)
        cfkwargs["data"]["pass"] = re.search(r'name="pass" value="(.+?)"', body).group(1)
        jsanswer = str(float(js2py.eval_js(__extract_js(body))) + len(domain))
        cfkwargs["data"]["jschl_answer"] = jsanswer
        method = response.request.method
        # cfkwargs["allow_redirects"] = False
        t = 5
        from tinyxbmc import gui
        gui.notify("CloudFlare", "Waiting %d seconds" % t, False)
        time.sleep(t)
        return cloudflare(session, session.request("POST", submit_url, **cfkwargs), "js", **kwargs)

    elif response.status_code == 403 and "cloudflare" in response.headers.get("Server"):
        if previous == "cc":
            return response
        body = tools.unescapehtml(response.text)
        formaddr = re.search('<form.+?id="challenge-form".+?action="(.+?)"', body)
        if formaddr:
            from tinyxbmc import recaptcha
            r = re.search('input type="hidden" name="r" value="(.*?)"', body).group(1)
            page_url = response.url
            method = response.request.method
            parsed_url = parse.urlparse(page_url)
            domain = parsed_url.netloc
            sitekey = re.search('data-sitekey="(.*?)"', body).group(1)
            ua = response.request.headers["user-agent"]
            headers = {'Referer': page_url, "User-agent": ua, "Accept-Language": tools.language()}
            resp = session.request("GET", 'http://www.google.com/recaptcha/api/fallback?k=%s' % sitekey,
                                   headers=headers)
            html = tools.unescapehtml(resp.text)
            token = ''
            iteration = 0
            while True:
                payload = re.findall('"(/recaptcha/api2/payload[^"]+)', html)
                iteration += 1
                message = re.findall('<label[^>]+class="fbc-imageselect-message-text"[^>]*>(.*?)</label>', html)
                if not message:
                    message = re.findall('<div[^>]+class="fbc-imageselect-message-error">(.*?)</div>', html)
                if not message:
                    token = re.findall('div class="fbc-verification-token"><textarea.+?>(.*?)<\/textarea>', html)[0]
                    if token:
                        addon.log('Captcha Success: %s' % token)
                    else:
                        addon.log('Captcha Failed')
                    break
                else:
                    message = tools.strip(message[0], True)
                    payload = payload[0]
                cval = re.findall('name="c"\s+value="([^"]+)', html)[0]
                captcha_imgurl = 'https://www.google.com%s' % (payload.replace('&amp;', '&'))
                message = re.sub('</?strong>', '', message)
                if tools.isstub():
                    addon.log(captcha_imgurl)
                    addon.log(message)
                    addon.log(iteration)
                    addon.log(page_url)
                    captcha_response = [int(x) for x in input("").split()]
                else:
                    oSolver = recaptcha.cInputWindow(captcha=captcha_imgurl, msg=message, iteration=iteration, sitemsg=page_url)
                    captcha_response = oSolver.get()
                if not captcha_response:
                    break
                postdata = {"c": str(cval), "response": []}
                for captcha in captcha_response:
                    postdata["response"].append(str(captcha))
                headers = {'Referer': resp.url, "User-agent": ua}
                resp = session.request("POST", 'http://www.google.com/recaptcha/api/fallback?k=%s' % sitekey,
                                       headers=headers, data=postdata)
                html = resp.text
            if token == "":
                return response
            submit_url = "%s://%s%s" % (parsed_url.scheme, domain, formaddr.group(1))
            data = {"r": r, "g-recaptcha-response": token}
            headers = {"Referer": page_url, "User-agent": ua}
            return cloudflare(session, session.request("POST", submit_url, data=data, headers=headers), "cc", **kwargs)
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


class hlsurl(const.URL):
    manifest = "hls"
    HASISA = addon.has_addon(const.INPUTSTREAMADDON)

    def __init__(self, url, headers=None, adaptive=True):
        self.url = url
        self.headers = headers or {}
        self.adaptive = adaptive
        dict.__init__(self,
                      manifest=self.manifest,
                      url=self.url,
                      headers=self.headers,
                      adaptive=self.adaptive)

    @property
    def inputstream(self):
        if self.HASISA and self.adaptive:
            return const.INPUTSTREAMADDON
        return None

    @property
    def kodiurl(self):
        return tokodiurl(self.url, headers=self.headers)


class mpdurl(const.URL):
    manifest = "mpd"
    HASISA = addon.has_addon(const.INPUTSTREAMADDON)
    HASWV = False
    CDMVER = None
    if HASISA:
        try:
            ishelper = ghub.load("emilsvennesson", "script.module.inputstreamhelper", "master", period=24 * 7, path=["lib"])
            fname = os.path.join(ishelper, "lib", "inputstreamhelper", "kodiutils.py")
            with open(fname) as f:
                src = f.read()
            src = re.sub("script\.module\.inputstreamhelper", "script.module.tinyxbmc", src)
            with open(fname, "w") as f:
                f.write(src)
            import inputstreamhelper
            inputstreamhelper.ok_dialog = lambda *args, **kwargs: None
            inputstreamhelper.widevine_eula = lambda *args, **kwargs: None
            helper = inputstreamhelper.Helper(manifest)
            HASWV = inputstreamhelper.has_widevinecdm()
            canwv = helper._supports_widevine()
            if not canwv:
                addon.log("MPD: Widewine is not supported by platform")
            if not HASWV and canwv:
                helper.install_widevine()
                HASWV = True
        except Exception as e:
            print(traceback.format_exc())
    else:
        addon.log("MPD: Inputstream.adaptive is not installed")

    if HASWV:
        from inputstreamhelper import widevinecdm_path
        CDMVER = LooseVersion(helper._get_lib_version(widevinecdm_path()))
        addon.log("MPD: Widewine is enabled with CDM version %s" % CDMVER)

    def __init__(self, url, headers=None, lurl=None, lheaders=None, lbody="R{SSM}", lresponse="", mincdm=None):
        self.license = "com.widevine.alpha"
        if isinstance(mincdm, six.string_types):
            self.mincdm = LooseVersion(mincdm)
        else:
            self.mincdm = None
        self.url = url
        self.lurl = lurl
        self.headers = headers or {}
        self.lheaders = lheaders or {}
        self.lbody = lbody
        self.lresponse = lresponse
        dict.__init__(self,
                      manifest=self.manifest,
                      url=self.url,
                      headers=self.headers,
                      lurl=self.lurl,
                      lheaders=self.lheaders,
                      lbody=self.lbody,
                      lresponse=self.lresponse,
                      mincdm=self.mincdm)

    @property
    def inputstream(self):
        inputstream = None
        if self.lurl:
            if self.HASWV:
                if self.mincdm:
                    if self.mincdm <= self.CDMVER:
                        inputstream = const.INPUTSTREAMADDON
                    else:
                        addon.log("MPD: Available CDM version (%s) is not >= minimum required (%s): %s" % (self.CDMVER,
                                                                                                           self.mincdm,
                                                                                                           self.url))
                else:
                    inputstream = const.INPUTSTREAMADDON
            else:
                addon.log("MPD: DASH stream requires drm but widewine is not available: %s" % (self.url))
        elif self.HASISA:
            inputstream = const.INPUTSTREAMADDON
        return inputstream

    @property
    def kodiurl(self):
        return tokodiurl(self.url, headers=self.headers)

    @property
    def kodilurl(self):
        if self.lurl:
            lurl = tokodiurl(self.lurl, headers=self.lheaders)
            if "|" not in lurl:
                return lurl + "|"
            return "%s|%s|%s" % (lurl, self.lbody, self.lresponse)


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


def urlfromdict(url):
    if isinstance(url, dict):
        manifest = url.pop("manifest")
        if manifest == hlsurl.manifest:
            return hlsurl(**url)
        elif manifest == mpdurl.manifest:
            return mpdurl(**url)
    else:
        return url
