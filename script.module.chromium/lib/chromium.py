'''
Created on Oct 31, 2021

@author: boogie
'''
import websocket
import json
import time
import os
import traceback
from urllib.request import urlopen
from urllib import parse
from libchromium import defs


class Browser:
    def __init__(self, useragent=None, maxtimeout=10, port=9222, idle=1):
        self.idle = idle
        self.maxtimeout = maxtimeout
        self.useragent = useragent
        self.id = 1000
        self.port = port
        self.nodecmds = []
        self.log = []
        self.ws = None
        self.lastmsgtime = 0
        websocket.setdefaulttimeout(self.idle)
        self.url = "http://127.0.0.1:%s" % self.port
        if not defs.DEBUG:
            self.closetabs()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.ws:
            self.close()

    def closetabs(self):
        # in case some weird pop ups infest the browser or due to some exception windows are left open
        tabs = json.loads(urlopen("%s/json/list" % self.url).read())
        for tab in tabs:
            # keep the 1 single chrome://newtab open so the browser wont be closed
            if tab["url"].startswith("chrome"):
                continue
            self.closetab(tab["id"])

    def closetab(self, tabid):
        return urlopen("%s/json/close/%s" % (self.url, tabid)).read()

    def validate(self, page):
        if "<title>Just a moment...</title>" in page:
            if "_cf_chl_opt" in page:
                print("Detected CF, sleeping 1 sec")
                time.sleep(1)
                return
        return page

    def open(self):
        d = json.loads(urlopen("%s/json/new" % self.url).read())
        self.tabid = d["id"]
        self.wsurl = d["webSocketDebuggerUrl"]
        self.connect()
        self.command("Page.enable")
        # self.command("Runtime.enable")
        self.command("Network.enable")
        if self.useragent:
            self.command("Network.setUserAgentOverride", userAgent=self.useragent)
        else:
            self.useragent = json.loads(urlopen("%s/json/version" % self.url).read())["User-Agent"]
        self.command("DOM.enable")

    def connect(self):
        if not self.ws or not self.ws.connected:
            self.ws = websocket.create_connection(self.wsurl, enable_multithread=True, timeout=self.idle)

    def command(self, method, **kwargs):
        self.id += 1
        if defs.DEBUG:
            print("Command (%s): %s, %s" % (self.id, method, kwargs))
        self.connect()
        self.ws.send(json.dumps({"id": self.id, "method": method, "params": kwargs}))
        return self.id

    def command_block(self, method, **kwargs):
        cmdid = self.command(method, **kwargs)
        message = self.wait_message(defs.CMD_TIMEOUT, cmdid)
        if message:
            return message if "result" in message else None

    def wait_message(self, timeout, msg_id=None, msg_method=None):
        startt = time.time()
        for message, ev_msg_id, ev_msg_method in self.itermessages():
            if (time.time() - startt) > timeout:
                break
            if (msg_id and msg_id == ev_msg_id):
                if defs.DEBUG:
                    print("Received msg_id: %s" % msg_id)
                return message
            if msg_method and msg_method == ev_msg_method:
                if defs.DEBUG:
                    print("Received msg_method: %s" % msg_method)
                return message

    def getmessage(self):
        self.connect()
        data = self.ws.recv()
        if defs.DEBUG:
            print(data[:400])
        return json.loads(data)

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
        cmd_cookies = self.command_block("Network.getCookies", urls=[url])
        if cmd_cookies:
            cookies = cmd_cookies["result"]["cookies"]

        return {"User-Agent": self.useragent,
                "cookie": "; ".join(["%s=%s" % (c["name"], parse.quote(c["value"])) for c in cookies])
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
        return self.command_block("Runtime.evaluate", expression=js)

    def jspost(self, addr, data="", headers=None):
        headers = headers or {}
        script = f"var xhr = new XMLHttpRequest();"
        script += f"xhr.open('POST', '{addr}', true);"
        for k, v in headers.items():
            script += f"xhr.setRequestHeader('{k}', '{v}');"
        script += "xhr.onload = function () { document.write(this.responseText);};"
        data = parse.urlencode(data)
        script += f"xhr.send('{data}');"
        self.evaljs(script)

    def navigate(self, url, referer=None, headers=None, wait=True, html=True):
        # self.ws.settimeout(self.maxtimeout)
        kwargs = {"url": url}
        if referer:
            kwargs["referrer"] = referer
        if headers:
            self.command("Network.setExtraHTTPHeaders", headers=headers)
        self.command("Page.navigate", **kwargs)
        if wait:
            self.waitloadevent()
        if html:
            return self.html(url)

    def waitloadevent(self):
        try:
            self.wait_message(self.maxtimeout, msg_method="Page.loadEventFired")
        except websocket.WebSocketTimeoutException:
            pass

    def html(self, url=None):
        startt = time.time()
        while True:
            cmd_getdoc = self.command_block("DOM.getDocument")
            if not cmd_getdoc:
                continue
            cmd_getouter = self.command_block("DOM.getOuterHTML",
                                              nodeId=cmd_getdoc["result"]["root"]["nodeId"])
            if not cmd_getouter:
                continue
            html = cmd_getouter["result"]["outerHTML"]
            try:
                html = self.validate(html)
            except Exception:
                print(traceback.format_exc())
                html = None
            if html:
                return html
            if (time.time() - startt) > self.maxtimeout:
                print("Timeout waiting %s" % url)
                break

    def getdownloads(self):
        return [os.path.join(defs.DOWNLOAD_PATH, x) for x in os.listdir(defs.DOWNLOAD_PATH)]

    def cleardownloads(self):
        for x in os.listdir(defs.DOWNLOAD_PATH):
            fpath = os.path.join(defs.DOWNLOAD_PATH, x)
            if os.path.isfile(fpath):
                os.remove(fpath)

    def iterdownload(self, timeout=defs.CMD_TIMEOUT):
        startt = time.time()
        for m, _mid, mmtd in self.itermessages():
            if (time.time() - startt) > timeout:
                break
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
        if not defs.DEBUG:
            self.closetab(self.tabid)
