'''
Created on Oct 31, 2021

@author: boogie
'''
import websocket
import json
import time
from requests.cookies import create_cookie
from six.moves.urllib.request import urlopen
from six.moves.http_cookiejar import http2time
# ua = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:93.0) Gecko/20100101 Firefox/93.0"


class Tab:
    def __init__(self, timeout=30, port=9222):
        self.timeout = timeout
        self.id = 1000
        self.port = port
        self.open()

    def open(self):
        self.url = "http://127.0.0.1:%s" % self.port
        d = json.loads(urlopen("%s/json/new" % self.url).read())
        self.tabid = d["id"]
        self.wsurl = d["webSocketDebuggerUrl"]
        self.ws = websocket.create_connection(self.wsurl, enable_multithread=True)
        self.cookie = None
        self.useragent = None

    def command(self, method, **kwargs):
        self.id += 1
        self.ws.send(json.dumps({"id": self.id, "method": method, "params": kwargs}))

    def waittoken(self):
        startt = time.time()
        while (time.time() - startt) < self.timeout:
            message_json = self.ws.recv()
            message = json.loads(message_json)
            if not self.useragent:
                useragent = message.get("params", {}).get("headers", {}).get("User-Agent") or \
                    message.get("params", {}).get("request", {}).get("headers", {}).get("User-Agent")
                if useragent:
                    self.useragent = useragent
            cookie = message.get("params", {}).get("headers", {}).get("set-cookie")
            if cookie and "cf_clearance=" in cookie:
                result = {}
                for item in cookie.split(';'):
                    item = item.strip()
                    if not item:
                        continue
                    if '=' not in item:
                        result[item] = True
                        continue
                    name, value = item.split('=', 1)
                    result[name] = value
                result["value"] = result.pop("cf_clearance")
                result["expires"] = http2time(result["expires"])
                self.cookie = create_cookie("cf_clearance", result)
            else:
                cookies = message.get("params", {}).get("associatedCookies", [])
                if cookies:
                    for cookie in cookies:
                        name = cookie["cookie"].pop("name")
                        if name == "cf_clearance":
                            self.cookie = create_cookie(name, cookie["cookie"])
            if self.cookie:
                break

    def close(self):
        self.ws.close()
        urlopen("%s/json/close/%s" % (self.url, self.tabid)).read()


def bypass(url, useragent=None):
    tab = Tab()
    tab.command("Network.enable")
    if useragent:
        tab.command("Network.setUserAgentOverride", userAgent=useragent)
    tab.command("Page.navigate", url=url)
    tab.waittoken()
    tab.close()
    return tab
