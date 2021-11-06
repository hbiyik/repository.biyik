# -*- coding: utf-8 -*-
'''
Created on Nov 1, 2021

@author: boogie
'''

import platform
import xbmc
import struct
import uuid
import sys
import random
import binascii

from tinyxbmc import const
from tinyxbmc import tools

elf_machines = {2: "sparc", 3: "x86", 8: "mips", 20: "ppc", 21: "ppc64", 22: "s390",
                40: "arm", 42: "superh", 50: "ia64", 62: "amd64", 183: "aarch64", 243: "riscv"}


def detect_os():
    system = platform.system().lower()
    if xbmc.getCondVisibility('system.platform.osx'):
        if xbmc.getCondVisibility('system.platform.atv2'):
            return "osx-atv2"
        return "osx"
    if xbmc.getCondVisibility('system.platform.ios'):
        return "ios"
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
    with open("/proc/self/exe", "rb") as f:
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
        elif mflags_d["HRD"]:
            toolchains.append("armhf")
            toolchains.append("armel")
        else:
            toolchains.append("armel")
    return toolchains, machine, is64, mflags


def getmachineid():
    mid = None
    prefix = "m:"
    getters = []
    if hasattr(uuid, "_OS_GETTERS"):
        getters = uuid._OS_GETTERS
    elif hasattr(uuid, "_NODE_GETTERS_WIN32") and sys.platform == 'win32':
        getters = uuid._NODE_GETTERS_WIN32
    elif hasattr(uuid, "_NODE_GETTERS_UNIX"):
        getters = uuid._NODE_GETTERS_UNIX

    for getter in getters:
        try:
            mid = getter()
        except Exception:
            continue
        if (mid is not None) and (0 <= mid < (1 << 48)):
            break
        else:
            mid = None

    if not mid:
        prefix = "i:"
        from tinyxbmc import hay
        with hay.stack(const.OPTIONHAY) as stack:
            mid = stack.find("installid").data
            if not mid:
                mid = random.getrandbits(48) | (1 << 40)
                stack.throw("installid", mid)
                stack.snapshot()

    mid = binascii.hexlify(struct.pack("q", tools.hashfunc(struct.pack("Q", mid)[:-2]))).decode()
    return prefix + mid
