import subprocess
import os
import select
import re
import pty
import time
from tinyxbmc import addon
from tinyxbmc import gui
from tinyxbmc import const
from tinyxbmc import flare


class FlareSolverrService(addon.blockingloop):
    def init(self, port):
        self.errorname = "FlareSolverr Service"
        self.dropboxtoken = const.DB_TOKEN
        self.process = None
        self.port = port
        self.hasdocker = False
        self.hasimage = False
        self.image = None
        self.dockername = None

    def checkimages(self):
        process = subprocess.Popen(["docker", "images"], stdout=subprocess.PIPE)
        self.hasdocker = True
        self.hasimage = False
        for line in process.stdout:
            line = line.decode()
            if not self.hasdocker and re.search(r"unix\:///var/run/docker\.sock", line):
                self.hasdocker = False
                addon.log("Detected faulty docker daemon")
            if not self.hasimage and re.search(self.image, line):
                self.hasimage = True
                addon.log("Found ddocker image: %s" % self.image)
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
                m = re.findall(r"\:(.+?)([0-9\.]+)[A-Za-z]+\/([0-9\.]+)", output)
                if m:
                    if not progress:
                        progress = gui.bgprogress("FlareSolverr")
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
            addon.log(cmd)
            for l in process.stdout:
                addon.log(l.decode())
        if wait:
            process.wait()
        return process.returncode

    def getdockername(self):
        return "kodi-%s" % self.image.replace("/", "-")

    def oninit(self):
        canspawn = False
        self.image = "ghcr.io/flaresolverr/flaresolverr:latest"
        self.dockername = "kodi-%s" % self.image.replace("/", "-").replace(":", ".")
        addon.log("Current image is %s" % self.image)
        try:
            process = subprocess.Popen(["docker", "--version"], stdout=subprocess.PIPE)
            process.wait()
        except OSError:
            process = None
        if process is None or process.returncode != 0:
            addon.log("Docker is not installed or broken. Please install docker to your system to use FlareSolverr")
            self.close()
            return
        addon.log("Docker installation is found")
        self.checkimages()
        if addon.has_addon("service.system.docker") and not self.hasdocker:
            addon.log("Enabling Libreelec Docker Service")
            self.executecmd("systemctl enable /storage/.kodi/addons/service.system.docker/system.d/service.system.docker.service")
            self.executecmd("systemctl start service.system.docker.service")
            time.sleep(2)
            self.checkimages()
        if not self.hasimage:
            addon.log("Pulling image %s" % self.image)
            self.pullimage()
            self.checkimages()
        if not self.hasdocker:
            addon.log("Docker Daemon is not working")
        if not self.hasimage:
            addon.log("Docker does not have FlareSolverr image")
        if self.hasdocker and self.hasimage:
            canspawn = True
        if canspawn:
            self.spawn()
        else:
            self.close()

    def spawn(self):
        self.resetdocker()
        addon.log("FlareSolverr Container Starting")
        procargs = ["docker", "run",
                    "--name=%s" % self.dockername,
                    "--network=host",
                    "-e", "LOG_LEVEL=info",
                    "--restart", "unless-stopped",
                    self.image]
        addon.log(" ".join(procargs))
        self.process = subprocess.Popen(procargs, stdout=subprocess.PIPE)
        self.process.wait()
        if not self.process.returncode == 0:
            raise RuntimeError("Can not spawn FlareSolverr Service")
        else:
            addon.log("FlareSolverr Service Spawned")

    def resetdocker(self):
        self.executecmd("docker stop %s" % self.dockername)
        self.executecmd("docker rm %s -f" % self.dockername)

    def onclose(self):
        if self.process:
            addon.log("FlareSolverr Service Stopping")
            if self.hasdocker:
                self.resetdocker()
            self.process.kill()
            addon.log("FlareSolverr Service Stopped")


if __name__ == "__main__":
    FlareSolverrService(flare.PORT)
