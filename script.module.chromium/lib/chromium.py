'''
Created on Oct 31, 2021

@author: boogie
'''
import websocket
import json
import time
import re
import os
from six.moves.urllib.request import urlopen
from six.moves.urllib.parse import quote
from tinyxbmc import addon

latestchromium = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"

def isnotcf(page):
    if not re.search('form id="challenge-form"', page):
        return page


class Browser:
    def __init__(self, useragent=None, loadtimeout=1, maxtimeout=30, port=9222):
        self.maxtimeout = maxtimeout
        self.loadtimeout = loadtimeout
        self.debug = False
        if not useragent:
            useragent = latestchromium 
        self.useragent = useragent
        self.id = 1000
        self.port = port
        self.nodecmds = []
        self.log = []
        self.ws = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.ws:
            self.close()

    def open(self):
        self.url = "http://127.0.0.1:%s" % self.port
        d = json.loads(urlopen("%s/json/new" % self.url).read())
        self.tabid = d["id"]
        self.wsurl = d["webSocketDebuggerUrl"]
        self.connect()
        self.command("Page.enable")
        self.command("Runtime.enable")
        self.command("Network.enable")
        if self.useragent:
            self.command("Network.setUserAgentOverride", userAgent=self.useragent)
        else:
            self.useragent = json.loads(urlopen("%s/json/version" % self.url).read())["User-Agent"]
        self.command("DOM.enable")

    def connect(self):
        if not self.ws or not self.ws.connected:
            self.ws = websocket.create_connection(self.wsurl, enable_multithread=True)

    def command(self, method, **kwargs):
        self.id += 1
        if self.debug:
            print("Command (%s): %s, %s" % (self.id, method, kwargs))
        self.connect()
        self.ws.send(json.dumps({"id": self.id, "method": method, "params": kwargs}))
        return self.id

    def getmessage(self):
        try:
            self.connect()
            data = self.ws.recv()
            if self.debug:
                print(data[:200])
            return json.loads(data)
        except websocket.WebSocketTimeoutException:
            pass

    def itermessages(self):
        while True:
            message = self.getmessage()
            if not message:
                break
            self.log.append(message)
            msg_id = message.get("id")
            msg_method = message.get("method")
            yield message, msg_id, msg_method

    def getcfheaders(self, url):
        self.command("Network.getCookies", urls=[url])
        for m, mid, _ in self.itermessages():
            if mid == self.id:
                cookies = m["result"]["cookies"]
                break

        return {"User-Agent": self.useragent,
                "cookie": "; ".join(["%s=%s" % (c["name"], quote(c["value"])) for c in cookies])
                }

    def _get_elem_js(self, tag=None, name=None, eid=None, index=0):
        js = None
        if tag:
            js = 'document.getElementsByTagName("%s")' % tag
        elif name:
            js = 'document.getElementsByName("%s")' % name
        elif eid:
            js = 'document.getElementsById("%s")' % eid
        if js:
            js += "[%s]" % index
            return js

    def elem_setattr(self, attr, value, tag=None, name=None, eid=None, index=0):
        js = self._get_elem_js(tag, name, eid, index)
        if js:
            js += ".%s = %s" % (attr, value)
            return self.evaljs(js)

    def elem_call(self, method, tag=None, name=None, eid=None, index=0):
        js = self._get_elem_js(tag, name, eid, index)
        if js:
            js += ".%s()" % method
            return self.evaljs(js)

    def evaljs(self, js):
        comid = self.command("Runtime.evaluate", expression=js)
        for m, mid, mmtd in self.itermessages():
            if mid == comid:
                return m

    def html(self, validate=isnotcf):
        doc_comid = 0
        outer_comid = 0
        node = 0
        lock = False
        html = None
        hasslept = not self.loadtimeout
        startt = time.time()
        for message, msg_id, _msg_method in self.itermessages():
            if (time.time() - startt) > self.maxtimeout:
                break
            if not node and not lock:
                node = None
                doc_comid = self.command("DOM.getDocument")
                lock = True
                continue
            if msg_id == doc_comid:
                node = message["result"].get("root", {}).get("nodeId")
                outer_comid = self.command("DOM.getOuterHTML", nodeId=node)
                lock = False
                continue
            if outer_comid == msg_id:
                if not message.get("error"):
                    nhtml = message.get("result", {}).get("outerHTML")
                    if validate:
                        try:
                            isvalid = validate(nhtml)
                            if isvalid:
                                html = isvalid
                            else:
                                html = None
                        except Exception:
                            html = None
                    else:
                        html = nhtml
                    if html:
                        if hasslept:
                            break
                        else:
                            time.sleep(self.loadtimeout)
                            hasslept = True
                node = None
                doc_comid = self.command("DOM.getDocument")
                lock = True
        return html

    def navigate(self, url, referer=None, validate=isnotcf, headers=None):
        self.ws.settimeout(self.maxtimeout)
        kwargs = {"url": url}
        if referer:
            kwargs["referer"] = referer
        if headers:
            self.command("Network.setExtraHTTPHeaders", headers=headers)
        self.command("Page.navigate", **kwargs)
        return self.html(validate)

    def getdownloads(self):
        path = os.path.join(addon.get_addondir("script.module.chromium"), "downloads")
        return [os.path.join(path, x) for x in os.listdir(path)]

    def iterdownload(self):
        for m, _mid, mmtd in self.itermessages():
            if mmtd == "Page.downloadProgress":
                state = m.get("params", {}).get("state")
                if state == "inProgress":
                    if m["params"]["totalBytes"] == 0:
                        yield 0
                    else:
                        yield m["params"]["receivedBytes"] / m["params"]["totalBytes"]
                elif state == "completed":
                    yield 1
                    break

    def close(self):
        self.ws.close()
        urlopen("%s/json/close/%s" % (self.url, self.tabid)).read()
