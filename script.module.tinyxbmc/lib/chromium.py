import subprocess
import os
from tinyxbmc import abi
from tinyxbmc import addon


class ChromiumService(addon.blockingloop):
    @staticmethod
    def iscomptible():
        if abi.detect_os() == "linux":
            process = subprocess.Popen(["docker", "--version"], stdout=subprocess.PIPE)
            process.wait()
            if process.returncode == 0:
                return True
        return False

    def oninit(self, port=9222):
        self.process = None
        self.port = port
        self.target = abi.getelfabi()[0][0]
        self.spawn()

    def spawn(self):
        os.system("docker rm chromium")
        self.process = subprocess.Popen(["docker", "run", "--name=chromium", "--network=host", "boogiepy/chromium-xvfb-%s" % self.target,
                                         "xvfb-chromium", "--disable-gpu", "--no-sandbox", "--remote-debugging-port=%d" % self.port], stdout=subprocess.PIPE)

    def onclose(self):
        if self.process:
            os.system("docker stop chromium")


if __name__ == "__main__" and ChromiumService.iscomptible():
    ChromiumService()
