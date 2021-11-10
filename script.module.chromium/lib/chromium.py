'''
Created on Oct 31, 2021

@author: boogie
'''
import websocket
import json
import traceback
from six.moves.urllib.request import urlopen
from six.moves.urllib.parse import quote


class Browser:
    def __init__(self, useragent=None, loadtimeout=5, maxtimeout=15, port=9222):
        self.maxtimeout = maxtimeout
        self.loadtimeout = loadtimeout
        self.debug = False
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

    def getmessage(self):
        try:
            self.connect()
            data = self.ws.recv()
            if self.debug:
                print(data[:100])
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

    def navigate(self, url, referer=None, validate=None):
        node = None
        html = None
        self.ws.settimeout(self.maxtimeout)
        kwargs = {"url": url}
        if referer:
            kwargs["referer"] = referer
        self.command("Page.navigate", **kwargs)
        for message, msg_id, msg_method in self.itermessages():
            if msg_id:
                nhtml = message.get("result", {}).get("outerHTML")
                if nhtml and not nhtml == html:
                    if validate:
                        try:
                            isvalid = validate(nhtml)
                            if isvalid:
                                return isvalid
                        except Exception:
                            print(traceback.format_exc())
                    else:
                        html = nhtml
                        if not self.ws.gettimeout() == self.loadtimeout:
                            self.ws.settimeout(self.loadtimeout)
            if msg_id in self.nodecmds:
                self.nodecmds.remove(msg_id)
                nodeid = message["result"].get("root", {}).get("nodeId")
                if nodeid:
                    node = nodeid
                self.command("DOM.getOuterHTML", nodeId=node)
            if msg_method == "DOM.documentUpdated":
                self.command("DOM.getDocument")
                self.nodecmds.append(self.id)
        return html

    def close(self):
        self.ws.close()
        urlopen("%s/json/close/%s" % (self.url, self.tabid)).read()
