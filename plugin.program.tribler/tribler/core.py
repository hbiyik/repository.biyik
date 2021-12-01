import os
import stat
import subprocess

from tinyxbmc import abi
from tinyxbmc import addon
from tinyxbmc import net
from tinyxbmc import gui

from tribler import defs


BINARY_URL = "https://raw.githubusercontent.com/hbiyik/repository.biyik/master/%s/bin" % defs.ADDONID
PROFILE_DIR = addon.get_addondir(defs.ADDONID)
STATE_DIR = os.path.join(PROFILE_DIR, "tribler_state")
MEI_DIR = os.path.join(PROFILE_DIR, "tribler_freeze")
BIN_DIR = os.path.join(PROFILE_DIR, "tribler_binary")

for d in [MEI_DIR, STATE_DIR, BIN_DIR]:
    os.makedirs(d, exist_ok=True)


def getbinaryurls():
    error = None
    os = abi.detect_os()
    # TO-DO: windows .exe extension
    if os == "linux":
        toolchains, machine, is64, mflags = abi.getelfabi()
        if toolchains:
            return [("%s-%s" % (os, x), "%s/%s-%s/triblerd" % (BINARY_URL,
                                                               os,
                                                               x)) for x in toolchains], error
        else:
            return [], "Can't detect abi for os linux, machine: %s, 64bit: %s, flags: %s" % (machine,
                                                                                             is64,
                                                                                             mflags)
    else:
        return [], "%s os is not supported" % os


def update():
    for binaryurl, error in getbinaryurls():
        if error:
            # there is an error, we can't use
            gui.error("TRIBLER", error)
            return None
        fname = os.path.basename(binaryurl)
        localbin = os.path.join(BIN_DIR, fname)
        localurl = os.path.join(BIN_DIR, "%s.url" % fname)
        if os.path.exists(localurl):
            with open(localurl) as f:
                localurladdr = f.read().decode()
            if localurladdr != binaryurl:
                # we have detected another toolchain is active, dont try this one
                continue
            # we know the existing toolchain from now on
            elif os.path.exists(localbin):
                # we are in the right toolchain lets check if there is an update or not
                resp = net.http(binaryurl, method="HEAD")
                if int(resp.headers['content-length']) != os.path.getsize(localbin):
                    # filesizes dont match, we need an update
                    downloadbinary(binaryurl, localbin)
                    return True
            else:
                # we have detected toolchain but binary is not available, may be someone deleted it.
                downloadbinary(binaryurl, localbin)
                return True
            break
        else:
            # we have to determine the toolchain by testing
            # toolchain can give several alternatives, we can use first one that works
            downloadbinary(binaryurl, localbin)
            try:
                process = subprocess.Popen([fname, "--help"])
                process.wait()
                success = process.returncode == 0
            except Exception:
                success = False
            if success:
                with open(localurl, "w") as f:
                    f.write(binaryurl)
                return True
        return False


def downloadbinary(url, fpath):
    with net.http(url, stream=True, text=False) as resp:
        # TO-DO: handle exceptions
        progress = gui.bgprogress("Tribler")
        with open(fpath, "wb") as f:  # TO-DO: windows?
            total = int(resp.headers['content-length'])
            since = 0
            for content in resp.iter_content():
                since += len(content)
                progress.update(100 * since / total, "Downloading")
                f.write(content)
        progress.close()
        # TO-DO: linux only
        os.chmod(fpath, os.stat(fpath).st_mode | ((stat.S_IXUSR |
                                                   stat.S_IXGRP |
                                                   stat.S_IXOTH
                                                   ) & ~ os.umask(os.umask(0))))
