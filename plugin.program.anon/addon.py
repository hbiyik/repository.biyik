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
import platform
import sys
import xbmc
import json


from tinyxbmc import container
from tinyxbmc import gui
from tinyxbmc import net
from tinyxbmc import addon

from anon import defs
from stem.control import Controller
from anon.platforms import Base


class viewer(gui.form):
    def init(self, value):
        self.txt = self.text(value, height=960)


def getinputpw(txt):
    conf, ret = gui.keyboard("", txt, True)
    if conf:
        return ret
    else:
        return ""


class navi(container.container):

    def init(self):
        self.platform = self.machine()
        if not isinstance(self.platform, Base):
            gui.ok("ANON", "%s platfrom is not supported" % self.platform)
            sys.exit()

    def checkreq(self):
        warning = None
        for warning in self.platform.missing_reqs():
            gui.error("ANON", warning)
            gui.ok("ANON", warning)
        return warning

    def start(self):
        if self.checkreq() is None:
            steps = ((self.platform.start_tor, (), "TOR can't start"),
                     (self.platform.set_dns, ("127.0.0.1",), "DNS can't be anonymized"),
                     (self.platform.start_ovpn, (), "OPENVPN can't start"),
                     (self.platform.anonymize, (), "TCP/UDP can't be anonimized")
                     )
            self._stop(True)
            for step, args, msg in steps:
                try:
                    ret = step(*args)
                except Exception, e:
                    gui.ok("ANON", "ERROR: %s" % str(e))
                    self._stop(True)
                    return
                if not ret:
                    self._stop(True)
                    gui.error("ANON", msg, True)
                    return
            gui.notify("ANON", "Anonimization started successfully !", True)
        container.refresh()

    def _stop(self, silent=False):
        steps = ((self.platform.set_dns,
                  (self.platform.getsetting("default_dns_server"),),
                  "Error during setting DNS"),
                 (self.platform.reset, (), "Error during clearing TCP/UDP routing"),
                 (self.platform.stop_tor, (), "TOR can't be stooped"),
                 (self.platform.stop_ovpn, (), "OPENVPN can't be stopped")
                 )
        for step, args, msg in steps:
            try:
                ret = step(*args)
            except Exception, e:
                gui.ok("ANON", "ERROR: %s" % str(e))
                return
            if not ret:
                gui.error("ANON", msg, True)
                return
        if not silent:
            gui.notify("ANON", "Anonimization stopped successfully !", True)

    def stop(self):
        if self.checkreq() is None:
            self._stop()
        container.refresh()
    def index(self):
        self.item("Settings", method="settings").dir()

        vconnected = "[COLOR red]Disconnected[/COLOR]"
        for _ in self.platform.findpids("openvpn"):
            vconnected = "[COLOR green]Connected[/COLOR]"
            break
        self.item("VPN Status: %s" % vconnected).call()

        try:
            controller = Controller.from_port(port=int(self.platform.getsetting("tor_control_port")))
            if controller and controller.is_alive():
                tconnected = "[COLOR green]Connected[/COLOR]"
                controller.close()
            else:
                raise Exception
        except Exception:
            tconnected = "[COLOR red]Disconnected[/COLOR]"
        self.item("Tor Status: %s" % tconnected).call()

        self.item("Statistics", method="statistics").dir()
        self.item("Stop", method="stop").call()
        self.item("(Re)Start", method="start").call()

    def statistics(self):
        self.item("Platform: %s" % self.platform.machineid)
        self.autoupdate = 5
        if not self.checkreq():
            for k, v in self.platform.stats().iteritems():
                self.item("%s: %s" % (k.replace("_", " ").title(), v)).call()

    def select(self, key, isall):
        if isall:
            self.platform.setsetting(key, range(len(defs.tor_countries)))
        else:
            self.platform.setsetting(key, [])
        container.refresh()

    def settings(self):
        title = "View OVPN Config File"
        if self.platform.getsetting("openvpn_config") == "?":
            title = "[COLOR red]%s[/COLOR]" % title
        self.item(title, method="viewcfg").call()
        self.item("Browse OVPN Config File", method="setvpnconfig").call()
        cntx = {self.item("No Specific Exit Node", method="setcfg"): ["tor_use_specific_exit_node", "-", False, False],
                self.item("Autoselect Exit In a Country", method="select_best_exit"): [],
                self.item("Autoselect Exit In the World", method="select_best_exit"): [False]
                }
        force_exit = self.settingitem("tor_use_specific_exit_node", cntx)

        select_all = self.item("Select All", method="select")
        select_none = self.item("Select None", method="select")
        limit_tor_nodes = self.item("Limit Location of All Tor Nodes to: %s Countriess" % len(self.platform.getsetting("tor_limit_nodes_to")),
                                    method="selectcountry")
        limit_tor_nodes.context(select_all, False, "tor_limit_nodes_to", True)
        limit_tor_nodes.context(select_none, False, "tor_limit_nodes_to", False)
        limit_tor_nodes.call("tor_limit_nodes_to")
        if force_exit == "-":
            limit_tor_exit_nodes = self.item("Limit Location of Tor Exit Nodes to: %s Countries" % len(self.platform.getsetting("tor_limit_exit_nodes_to")),
                                             method="selectcountry")
            limit_tor_exit_nodes.context(select_all, True, "tor_limit_exit_nodes_to", True)
            limit_tor_exit_nodes.context(select_none, True, "tor_limit_exit_nodes_to", False)
            limit_tor_exit_nodes.dir("tor_limit_exit_nodes_to")
        else:
            self.settingitem("tor_circuit_timeout_in_minutes")

        for key in self.platform.cfg:
            if key not in ["openvpn_config", "tor_limit_nodes_to", "tor_limit_exit_nodes_to", "tor_use_specific_exit_node"]:
                self.settingitem(key)

    def select_best_exit(self, showgui=True):
        if showgui:
            ctry = gui.select("Select Country", defs.tor_countries)
            if ctry >= 0:
                ctry = defs.tor_countries[ctry]
                nodes = json.loads(self.download("https://onionoo.torproject.org/details?search=flag:exit country:%s" % ctry))
                if not len(nodes["relays"]):
                    gui.ok(ctry, "Can't find any exit nodes in %s" % ctry)
                    return
        else:
            nodes = json.loads(self.download("https://onionoo.torproject.org/details?search=flag:exit"))
        relay = sorted(nodes["relays"], key=lambda i: i.get("exit_probability", 0), reverse=True)[0]
        guistr = "%s\n%s: %s \n%s: %s Mbps\n%s" % (relay["fingerprint"],
                                                   relay.get("nickname", ""),
                                                   relay.get("as_name", ""),
                                                   relay.get("country_name", ""),
                                                   int(relay.get("observed_bandwidth", 0) / 1000000),
                                                   " ".join(relay.get("exit_addresses", []))
                                                   )
        container.refresh()

        gui.ok("Exit Node Selected", guistr)
        self.setcfg("tor_use_specific_exit_node", relay["fingerprint"], False, False)

    def settingitem(self, key, cntx=None):
        old = self.platform.getsetting(key)
        title = key.replace("_", " ").title()
        if old == "?":
            title = "[COLOR red]%s[/COLOR]" % title
        ispw = "password" in key
        if ispw:
            old = "*" * len(old)
        item = self.item("%s : %s" % (title, old), method="setcfg")
        if cntx:
            for context, args in cntx.iteritems():
                item.context(context, False, *args)
        item.call(key, old, ispw)
        return old

    def selectcountry(self, key):
        current = self.platform.getsetting(key)
        ncurrent = gui.select("Allowed Countries", defs.tor_countries, False, current, False, True)
        if ncurrent:
            self.platform.setsetting(key, ncurrent)

    def getfile(self):
        location = gui.select("Location", ["Local", "Remote"], multi=False)
        if location == 0:
            path = gui.browse(1, "Select File")
            try:
                with open(path, "r") as f:
                    return f.read()
            except Exception:
                pass
        elif location == 1:
            conf, url = gui.keyboard()
            if conf:
                try:
                    cfg = net.http(url)
                except Exception, e:
                    gui.warn(str(e), "%s url can't be reached" % url)
                    return
                return cfg

    def setvpnconfig(self):
        cfg = self.getfile()
        if cfg:
            self.platform.setsetting("openvpn_config", cfg)
        container.refresh()

    def setcfg(self, key, value, hidden, showgui=True):
        if not showgui:
            self.platform.setsetting(key, value)
        else:
            conf, nvalue = gui.keyboard(value, hidden=hidden)
            if conf and not value == "auto":
                self.platform.setsetting(key, nvalue)
        container.refresh()

    def viewcfg(self):
        gui.textviewer("OpenVPN Config File", self.platform.getsetting("openvpn_config"))

    def machine(self):
        system = platform.system().lower()
        if "windows" in system or xbmc.getCondVisibility('system.platform.windows'):
            os = "windows"
        if "linux" in system or xbmc.getCondVisibility('system.platform.linux'):
            if xbmc.getCondVisibility('system.platform.android'):
                os = "android"
            os = "linux"
        try:
            iselec = False
            with open("/etc/os-release") as f:
                if "ELEC" in f.read():
                    iselec = True
        except Exception:
            pass
        ar = platform.architecture()[0].lower()
        mach = platform.machine().lower()
        if ar == "32bit":
            if "arm" in mach:
                arch = "arm"
            arch = "x86"
        if ar == "64bit":
            if "arm" in mach:
                arch = "aarch64"
            arch = "amd64"
        machine = "%s-%s" % (os, arch)
        if os == "linux":
            if iselec:
                from anon.platforms import libreelec
                return libreelec.Platform(addon.get_addondir(), machine, getinputpw)
            from anon.platforms import linux
            return linux.Platform(addon.get_addondir(), machine, getinputpw)
        else:
            return machine


navi()
