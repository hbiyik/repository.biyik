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
from http.cookiejar import Cookie

from tinyxbmc import gui
from tinyxbmc import hay
from tinyxbmc import const

PORT = 8191
TIMEOUT = 60 * 1000


def proxyget(url):
    headers = {"Content-Type": "application/json"}
    data = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": TIMEOUT
    }
    return requests.post(f"http://localhost:{PORT}/v1",
                         headers=headers, json=data).json()


def getuseragent(default):
    try:
        js = proxyget(f"http://localhost:{PORT}/v1")
    except Exception:
        return default
    return js.get("solution", {}).get("userAgent") or default


def cookies(resp):
    if not resp.status_code == 403:
        return
    if not resp.headers.get("server") == "cloudflare":
        return
    if not resp.headers.get("cf-mitigated") == "challenge":
        return
    gui.notify("Cloudflare", f"{resp.request.url} solving challange", sound=False)
    answer = proxyget(resp.request.url)
    gui.notify("Cloudflare", f"{resp.request.url} {answer['status']} {answer['message']}", sound=False)
    cookies = []
    for cookie in answer.get("solution", {}).get("cookies", []):
        cookies.append(Cookie(0, cookie["name"], cookie["value"],
                              None, False,
                              cookie["domain"], True, cookie["domain"].startswith("."),
                              cookie["path"], True,
                              cookie.get("secure", False),
                              cookie.get("expiry"),
                              False, None, None, {}))
    return cookies


with hay.stack(const.FLAREHAY) as stack:
    USERAGENT = stack.find("useragent").data
    if not USERAGENT:
        USERAGENT = const.FALLBACK_USERAGENT
