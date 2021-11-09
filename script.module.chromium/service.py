import subprocess
import os
import time
import select
import pty
import re
from tinyxbmc import abi
from tinyxbmc import addon
from tinyxbmc import gui
from tinyxbmc import const


class ChromiumService(addon.blockingloop):
    def init(self, port):
        self.errorname = "Chromium Service"
        self.dropboxtoken = const.DB_TOKEN
        self.process = None
        self.port = port
        self.hasdaemon = False
        self.hasimage = False
        self.iscomptible = False
        self.target = None
        self.image = None

    def log(self, txt):
        addon.log("TINYXBMC:CHROMIUM SERVICE:%s" % txt)

    def checkimages(self):
        process = subprocess.Popen(["docker", "images"], stdout=subprocess.PIPE)
        self.hasdaemon = True
        self.hasimage = False
        for line in process.stdout:
            line = line.decode()
            if not self.hasdaemon and re.search("unix\:///var/run/docker\.sock", line):
                self.hasdaemon = False
                self.log("Detected faulty docker daemon")
            if not self.hasimage and re.search(self.image, line):
                self.hasimage = True
                self.log("Found ddocker image: %s" % self.image)
        process.wait()
        if not process.returncode == 0:
            self.hasdaemon = False

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
        if abi.detect_os() == "linux":
            self.log("Current system is Linux")
            self.target = abi.getelfabi()[0][0]
            self.image = "boogiepy/chromium-xvfb-%s" % self.target
            self.log("Current image is %s" % self.image)
            process = subprocess.Popen(["docker", "--version"], stdout=subprocess.PIPE)
            process.wait()
            if process.returncode == 0:
                self.log("Docker installation is found")
                self.checkimages()
                if addon.has_addon("service.system.docker") and not self.hasdaemon:
                    self.log("Enabling Libreelec Docker Service")
                    self.executecmd("systemctl enable /storage/.kodi/addons/service.system.docker/system.d/service.system.docker.service")
                    self.executecmd("systemctl start service.system.docker.service")
                    time.sleep(2)
                    self.checkimages()
                if not self.hasimage:
                    self.log("Pulling image %s" % self.image)
                    self.pullimage()
                    self.checkimages()
        if not self.hasdaemon:
            gui.warn("Chromium", "Docker Daemon is not working")
        if not self.hasimage:
            gui.warn("Chromium", "Docker does not have chromium image")
        if self.hasdaemon and self.hasimage:
            self.spawn()
        else:
            self.close()

    def spawn(self):
        self.executecmd("docker rm chromium")
        self.log("Chromium Container Starting")
        self.process = subprocess.Popen(["docker", "run", "--name=chromium", "--network=host", self.image,
                                         "xvfb-chromium", "--disable-gpu", "--no-sandbox", "--remote-debugging-port=%d --disable-dev-shm-usage" % self.port], stdout=subprocess.PIPE)
        self.log("Chromium Container Started")

    def onclose(self):
        if self.process:
            self.log("Chromium Container Stopping")
            self.executecmd("docker stop chromium")
            self.log("Chromium Container Stopped")
            self.process.kill()


if __name__ == "__main__":
    ChromiumService(9222)