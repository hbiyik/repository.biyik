import subprocess
import os
import time
import select
import re
import json
import shutil
from tinyxbmc import abi
from tinyxbmc import addon
from tinyxbmc import gui
from tinyxbmc import const


addondir = addon.get_addondir("script.module.chromium")
datadir = os.path.join(addondir, "data")
downdir = os.path.join(addondir, "downloads")
winbinaries = ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
               "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"]

_OS = abi.detect_os()

if _OS == "linux":
    import pty


for d in [datadir, downdir, os.path.join(datadir, "Default")]:
    if not os.path.exists(d):
        os.makedirs(d)

prefs = {"download": {"default_directory": "/addondir/downloads",
                      "prompt_for_download": False,
                      "directory_upgrade": True},
         "safebrowsing": {"enabled": True}}

with open(os.path.join(datadir, "Default", "Preferences"), "wb") as f:
    f.write(json.dumps(prefs).encode())


class ChromiumService(addon.blockingloop):
    def init(self, port):
        self.errorname = "Chromium Service"
        self.dropboxtoken = const.DB_TOKEN
        self.process = None
        self.port = port
        self.hasdocker = False
        self.hasimage = False
        self.iscomptible = False
        self.target = None
        self.image = None

    def log(self, txt):
        addon.log("TINYXBMC:CHROMIUM SERVICE:%s" % txt)

    def checkimages(self):
        process = subprocess.Popen(["docker", "images"], stdout=subprocess.PIPE)
        self.hasdocker = True
        self.hasimage = False
        for line in process.stdout:
            line = line.decode()
            if not self.hasdocker and re.search("unix\:///var/run/docker\.sock", line):
                self.hasdocker = False
                self.log("Detected faulty docker daemon")
            if not self.hasimage and re.search(self.image, line):
                self.hasimage = True
                self.log("Found ddocker image: %s" % self.image)
        process.wait()
        if not process.returncode == 0:
            self.hasdocker = False

    def pullimage(self):
        master, slave = pty.openpty()
        process = subprocess.Popen(["docker", "pull", self.image], stdout=slave)
        progress = None
        output = ""
        while process.poll() is None:
            rlist, _, _ = select.select([master], [], [], 1)
            for f in rlist:
                c = os.read(f, 1).decode()
                if c in ["", " ", "\r", "\n", "\t"]:
                    continue
                output += c
                output = output[-50:]
                m = re.findall("\:(.+?)([0-9\.]+)[A-Za-z]+\/([0-9\.]+)", output)
                if m:
                    if not progress:
                        progress = gui.bgprogress("Chromium")
                    desc = m[-1][0]
                    done = float(m[-1][1])
                    total = float(m[-1][2])
                    perc = int(100 * done / total)
                    if 0 <= perc <= 100:
                        progress.update(perc, "%s:%s" % (desc, self.image))
        if progress:
            progress.close()

    def executecmd(self, cmd, wait=True, log=True, shell=True):
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=shell)
        if log:
            self.log(cmd)
            for l in process.stdout:
                self.log(l.decode())
        if wait:
            process.wait()
        return process.returncode

    def oninit(self):
        canspawn = False
        if _OS == "linux":
            self.log("Current system is Linux")
            self.target = abi.getelfabi()[0][0]
            if self.target == "aarch64":
                self.target = "arm64"
            self.image = "boogiepy/chromium-xvfb-%s" % self.target
            self.log("Current image is %s" % self.image)
            try:
                process = subprocess.Popen(["docker", "--version"], stdout=subprocess.PIPE)
                process.wait()
            except OSError:
                process = None
            if process is None or process.returncode != 0:
                gui.notify("Chromium", "Docker is not installed or broken. Please install docker to your system")
                self.close()
                return
            else:
                self.log("Docker installation is found")
                self.checkimages()
                if addon.has_addon("service.system.docker") and not self.hasdocker:
                    self.log("Enabling Libreelec Docker Service")
                    self.executecmd("systemctl enable /storage/.kodi/addons/service.system.docker/system.d/service.system.docker.service")
                    self.executecmd("systemctl start service.system.docker.service")
                    time.sleep(2)
                    self.checkimages()
                if not self.hasimage:
                    self.log("Pulling image %s" % self.image)
                    self.pullimage()
                    self.checkimages()
            if not self.hasdocker:
                gui.warn("Chromium", "Docker Daemon is not working")
            if not self.hasimage:
                gui.warn("Chromium", "Docker does not have chromium image")
            if self.hasdocker and self.hasimage:
                canspawn= True
        elif _OS == "windows":
            for winbinary in winbinaries:
                if os.path.exists(winbinary):
                    self.image = winbinary
                    canspawn = True
                    break
        if canspawn:
            self.spawn()
        else:
            self.close()

    def spawn(self):
        procargs = None
        if _OS == "linux":
            self.executecmd("docker rm chromium")
            self.log("Chromium Container Starting")
            procargs = ["docker", "run", "-v", "%s:/addondir" % addondir, "--user", "%s:%s" % (os.getuid(), os.getgid()),
                        "--name=chromium", "--network=host", self.image,
                        "xvfb-chromium", "--disable-gpu", "--no-sandbox", "--remote-debugging-port=%d" % self.port,
                        "--disable-dev-shm-usage", "--user-data-dir=/addondir/data"]
        elif _OS == "windows":
            procargs = [self.image, "--remote-debugging-port=%d" % self.port, "--disable-dev-shm-usage",
                        "--user-data-dir=%s" % addondir, "--headless"]
        
        if procargs:
            self.log(" ".join(procargs))
            self.process = subprocess.Popen(procargs, stdout=subprocess.PIPE)
            self.log("Chromium Service Spawned")

    def onclose(self):
        if self.process:
            self.log("Chromium Service Stopping")
            if self.hasdocker:
                self.executecmd("docker stop chromium")
            self.process.kill()
            self.log("Chromium Service Stopped")
            shutil.rmtree(downdir, True)


if __name__ == "__main__":
    ChromiumService(9222)
