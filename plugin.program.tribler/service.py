'''
Created on 2 Haz 2020

@author: boogie
'''
from tinyxbmc import addon
from tinyxbmc import gui
from tinyxbmc import net
from tribler import core
from tribler.api.settings import settings
import os
import subprocess
import time
import sys

pdevpath = "/home/boogie/local/eclipse/plugins/org.python.pydev.core_7.5.0.202001101138/pysrc/"
sys.path.append(pdevpath)
import pydevd  # @UnresolvedImport
pydevd.settrace(stdoutToServer=True, stderrToServer=True, suspend=False)


class Service(addon.blockingloop):
    def startriblerd(self):
        print 111
        if not self.error:
            if self.triblerd and self.triblerd.poll() is None and self.retries <= 3:
                return
            urls, error = core.getbinary()
            self.error = error
            if not error:
                for toolchain, url in urls:
                    pdir = addon.get_addondir("plugin.program.tribler")
                    loc_toolchain = os.path.join(pdir, "toolchain")
                    loc_triblerd = os.path.join(pdir, "triblerd")
                    loc_sha = loc_triblerd + ".sha256"
                    rem_sha = url + ".sha256"
                    loc_toolchain_val = None
                    loc_sha_val = None
                    rem_sha_val = net.http(rem_sha, text=False).content
                    if os.path.exists(loc_toolchain):
                        with open(loc_toolchain) as f:
                            loc_toolchain_val = f.read()
                    if loc_toolchain_val and loc_toolchain_val != toolchain:
                        continue
                    if os.path.exists(loc_sha):
                        with open(loc_sha) as f:
                            loc_sha_val = f.read()
                    if loc_sha_val != rem_sha_val or not os.path.exists(loc_triblerd):
                        gui.notify("Downloading Triblerd", toolchain)
                        with open(loc_triblerd, "w") as f:
                            f.write(net.http(url, text=False).content)
                        if core.detect_os() == "linux":
                            core.chmod_plus_x(loc_triblerd)
                        with open(loc_sha, "w") as f:
                            f.write(rem_sha_val)
                    port = 8085
                    self.triblerd = subprocess.Popen([loc_triblerd, "-p %s" % port],
                                                     stdout=subprocess.PIPE,
                                                     stderr=subprocess.PIPE,
                                                     stdin=subprocess.PIPE)
                    port = None
                    for _ in range(5):
                        time.sleep(1)
                        try:
                            stgs = settings.get()
                        except Exception:
                            continue
                        port = stgs.get("settings", {}).get("http_api", {}).get("port")
                        break
                    if port:
                        with open(loc_toolchain, "w") as f:
                            f.write(toolchain)
                        break
                if not port:
                    self.error = self.triblerd.communicate()
                else:
                    self.retries += 1
            if self.error:
                gui.error("Triblerd daemon", error)

    def oninit(self):
        self.retries = 0
        self.triblerd = None
        self.error = None

    def onloop(self):
        self.startriblerd()


Service()
