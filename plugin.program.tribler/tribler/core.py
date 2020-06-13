import platform
import xbmc
import struct
import os
import stat

from defs import BINARY_URL

elf_machines = {2: "sparc", 3: "x86", 8: "mips", 20: "ppc", 21: "ppc64", 22: "s390",
                40: "arm", 42: "superh", 50: "ia64", 62: "amd64", 183: "aarch64", 243: "riscv"}


def detect_os():
    system = platform.system().lower()
    if "windows" in system or xbmc.getCondVisibility('system.platform.windows'):
        return "windows"
    if "linux" in system or xbmc.getCondVisibility('system.platform.linux'):
        if xbmc.getCondVisibility('system.platform.android'):
            return "android"
        return "linux"


def getelfabi():
    def readbyte(offset, decoder="B", size=1):
        f.seek(offset)
        return struct.unpack(decoder, f.read(size))[0]
    mflags_d = {}
    with open("/proc/self/exe") as f:
        is64 = readbyte(0x4) == 2
        oseabi = readbyte(0x7)
        eabiver = readbyte(0x8)
        machine = elf_machines.get(readbyte(0x12, "H", 2))
        if is64:
            f.seek(0x30)
        else:
            f.seek(0x24)
        mflags = f.read(4)
    if machine in ["arm", "arm64"]:
        first, mid, abi = struct.unpack("HBB", mflags)
        mflags_d["ABI"] = abi
        mflags_d["HRD"] = first >> 10 & 1
        mflags_d["SFT"] = first >> 9 & 1
    toolchains = []
    if machine == "x86":
        toolchains.append("i386")
    elif machine == "amd64":
        if is64:
            toolchains.append("amd64")
            toolchains.append("i386")
        else:
            toolchains.append("i386")
    elif machine in ["arm", "aarch64"]:
        if is64:
            toolchains.append("aarch64")
        elif mflags_d["HARD"]:
            toolchains.append("armhf")
            toolchains.append("armel")
        else:
            toolchains.append("armel")
    return toolchains, machine, is64, mflags


def getbinary():
    error = None
    os = detect_os()
    if os == "linux":
        toolchains, machine, is64, mflags = getelfabi()
        if toolchains:
            return [("%s-%s" % (os, x), "%s/triblerd-%s-%s/triblerd" % (BINARY_URL,
                                                                        os,
                                                                        x)) for x in toolchains], error
        else:
            return [], "Can't detect abi for os linux, machine: %s, 64bit: %s, flags: %s" % (machine,
                                                                                             is64,
                                                                                             mflags)
    else:
        return [], "%s os is not supported" % os


def chmod_plus_x(path):
    os.chmod(path, os.stat(path).st_mode | ((stat.S_IXUSR |
                                             stat.S_IXGRP |
                                             stat.S_IXOTH
                                             ) & ~ os.umask(os.umask(0))
                                            ))
