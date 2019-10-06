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
        self.item("Stop", method="stop").dir()
        self.item("(Re)Start", method="start").dir()

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

    def settings(self):
        title = "View OVPN Config File"
        if self.platform.getsetting("openvpn_config") == "?":
            title = "[COLOR red]%s[/COLOR]" % title
        self.item(title, method="viewcfg").call()
        self.item("Download OVPN Config File", method="setvpnconfig").dir()
        self.item("Download OVPN Config File from archive", method="setvpnconfig").dir(True)

        select_all = self.item("Select All", method="select")
        select_none = self.item("Select None", method="select")

        limit_tor_nodes = self.item("Limit Location of All Tor Nodes to: %s Countriess" % len(self.platform.getsetting("tor_limit_nodes_to")),
                                    method="selectcountry")
        limit_tor_nodes.context(select_all, True, "tor_limit_nodes_to", True)
        limit_tor_nodes.context(select_none, True, "tor_limit_nodes_to", False)
        limit_tor_nodes.dir("tor_limit_nodes_to")

        limit_tor_exit_nodes = self.item("Limit Location of Tor Exit Nodes to: %s Countries" % len(self.platform.getsetting("tor_limit_exit_nodes_to")),
                                         method="selectcountry")
        limit_tor_exit_nodes.context(select_all, True, "tor_limit_exit_nodes_to", True)
        limit_tor_exit_nodes.context(select_none, True, "tor_limit_exit_nodes_to", False)
        limit_tor_exit_nodes.dir("tor_limit_exit_nodes_to")

        for key in self.platform.cfg:
            if key not in ["openvpn_config", "tor_limit_nodes_to", "tor_limit_exit_nodes_to"]:
                self.settingitem(key)

    def settingitem(self, key):
        old = self.platform.getsetting(key)
        title = key.replace("_", " ").title()
        if old == "?":
            title = "[COLOR red]%s[/COLOR]" % title
        ispw = "password" in key
        if ispw:
            old = "*" * len(old)
        self.item("%s : %s" % (title, old), method="setcfg").dir(key, old, ispw)

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

    def setvpnconfig(self, archive=False):
        cfg = self.getfile()
        if cfg:
            self.platform.setsetting("openvpn_config", cfg)

    def setcfg(self, key, value, hidden):
        conf, nvalue = gui.keyboard(value, hidden=hidden)
        if conf and not value == "auto":
            self.platform.setsetting(key, nvalue)

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
