'''
Created on Sep 30, 2019

@author: z0042jww
'''
from . import linux


class Platform(linux.Platform):
    def missing_reqs(self):
        for msg in linux.Platform.missing_reqs(self):
            if "TOR to be installed" in msg:  # this is weak & lame...
                continue
            yield msg
        process = self.run_cmd("docker --help", False)
        if not process:
            yield "Docker needs to be installed through 'service.system.docker' addon.\nIf you have installed it your device may need a reboot for docker to be available"

    def start_tor(self):
        cmdline = "docker run -v %s:/etc/tor/torrc:ro --net host --name tor amgxv/tor:stable" % self.torrc
        return linux.Platform.start_tor(self, cmdline)

    def stop_tor(self):
        list(self.run_cmd("docker stop tor"))
        list(self.run_cmd("docker rm tor"))
        return True
