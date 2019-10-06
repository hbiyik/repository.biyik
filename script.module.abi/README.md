# script.module.abi
Precompiled python module loader for kodi interpreter on multiple-platforms

Visit https://forum.kodi.tv/showthread.php?tid=312515 for details

I am happy to announce abi (Application Binary Interface) module for kodi. This module's purpose is to provide an interface for python c/c++ addon packagers inside kodi / xbmc python interpreter. It opens a total new dimension for kodi addons.

The interface is pretty straight forward:

```
import abi
binmodule = abi.load("some.addon.name", "modulename") 
```
where some.addon.name has /bin/os@toolchain-architecture_pythonid/modulename.so [or pyd, dll] directory structure. Abi module automatically detects the machine id name [os@...] automatically and imports to module in wicked ways depending to the machine.

Machine Definitions:
os: windows, linux, android, 
apple products like ios, darwin appletv is not implemented yet for 3 reasons, 1) i dont use apple things, 2) i dont like about apple things, 3) i dont care about apple things. However it can be impelented and is possible.

**toolchain:**\
toolchain is the binary dependence of your interpreter to load a binary addon, in which it is your current systems operating systems ABI, and your interpreters c-library dependence if your module to be loaded is not compiled staticaly with c-libs.\
**a)** for windows there are following toolchains:\
**a.1)** vc2008 toolchain: where your addon is compiled with cruntime of vc 2008 (msvcrt90.dll dependency)\
**a.2)** vc2015 toolchain: your addon is compiled vc 2015 (vcruntime140.dll) which is kodi 17 krypton. Those addons require vc redist dependency, but this dependency must already be satisfied on the kodi install, because kodi itself already depends on vc2015.\
**a.3)** winabi: this toolchain stands for the binaries which has cruntime is statically compiled with it. ABI module first tries to load one of the above toolchain (vc2008 or vc2015) if it fails, it tries to load winabi. As you can tell winabi toolchain is more generic, but not all of the addons can be compiled with static cruntime, it has so tweaks, and quirks.

**b) for linux:**\
**b.1)** pep513: which stands for manylinux1 tag standartized in https://www.python.org/dev/peps/pep-0513/ which satisfies a generic vast majority of linux distributions.

**c) for android:**\
c.1) ndk: android bionic c-library seems to be backwards compatible (i didnt check in much in details yet)

**architecture:** architecture is the definition to identify on which kind of cpu that the binary addon will run. Options are: x86, x64, arm5, arm6, arm7, arm8. Rest of fancy cpus can be implemented later on.

**pythonid:** we know that xbmc/kodi is shipped with either python 2.6 or python 2.7, these two create 2 different dependency however this is not all, there is also UCS2, UCS4 compile time variants. UCS defines how wide is the unicode support inside the interpreter and it is an header definition which means it creates another dependency. There is also another varian of which interpreter should be used inside python but it is always cpython for kodi/xbmc so it can be dismissed generally. At the end of the day this leaves us 4 variants:\
1) cp26m : cpython 2.6 UCS 2 Narrow Unicode Support
2) cp26mu : cpython 2.6 UCS 4 Wide Unicode Support
3) cp27m : cpython 2.7 UCS 2 Narrow Unicode Support
4) cp27mu : cpython 2.7 UCS 2 Wide Unicode Support

**Practical Machine Ids:**
As you can understand above combination of above parameters generated a bunch of targets however in practice not all of the combinations are needed. If the target operating system has generic market for kodi distribition compile-time options narrow down drastically. Ie: for windows and android there is on UCS2 builds. For windows there is never X64 distribution. For android there is only amr7 & arm8 cpu targets. So we can guess that practical machine ids are :

**Desktop PCs with Windows**\
windows@vc2008-x86_cp26m (releases before xbmc < 13 i think)\
windows@vc2008-x86_cp27m (releases before 13 < xbmc < 16 i think)\
windows@vc2015-x86_cp27m (kodi 17 krypton)

**Desktop PCs with Linux:**\
linux@pep513-x86_cp26m\ 
linux@pep513-x86_cp26mu\
linux@pep513-x86_cp27m\
linux@pep513-x86_cp27mu\
linux@pep513-x64_cp26m\
linux@pep513-x64_cp26mu\
linux@pep513-x64_cp27m\
linux@pep513-x64_cp27mu

**Mobile Platforms with android:**\
android@ndk-arm7_cp26m (release before kodi < 17)\
android@ndk-arm7_cp27m (kodi 17)\
android@ndk-arm8_cp27m\
android@ndk-arm8_cp27m

Apple things are ignored. Embedded Linuxes including raspberry pi or other embedded linuxes will be added later on.

**Current Status:**
I have first thought about this project like the rest of us complaining how slow BeautifulSoup is and how much i need lxml inside kodi, unfortunately lxml fast is because it is c written xml serializer and cant be run under kodi. Then i met tribler (see this presentation in stanford university) and i admired their effort on changing the internet. Then i here i am with the following addons required for Tribler Core. I have built below addons already for most of 32 bit platforms and tested under windows and android krypton, succesfully could use all of them:

**script.module.m2crypto=0.21.1 (fast cryptography api)\
script.module.cryptography=1.2.1 (fast cryptography api)\
script.module.libnacl=1.4.4 (fast cryptography api)\
script.module.libtorrent=1.0.8 (p2p torrent api)\
script.module.apsw=3.15.0 (fast sqlite api)\
script.module.plyvel=0.9 (leveldb api)\
script.module.netifaces=0.10.5 (acces os networking internals)\
script.module.cffi=1.10.0 (swiss knife dynamic dll loader/runtime compiler)**

You can see how it works and performs from the above packages from my github https://github.com/hbiyik?tab=repositories, currently there is no kodi repo at all and there is a bunch things to work on, and meanwhile since this is still a work in progress all of the above definitions are subject to change.

For those who want to contribute abi project or the packed packages above here is a basic dependency map of overall, triblerCore arhitecture for xbmc. You can find them in github repos for your reference..

```
script.module.triblercore (P)
  |||||||||||
  ||||||||||+--> script.module.twisted (P)
  ||||||||||      |
  ||||||||||      +--> script.module.zope.interface (P)
  ||||||||||      +--> script.module.incremental (P)
  ||||||||||      +--> script.module.constantly (P)
  ||||||||||      +--> script.module.zope.interface (P)
  ||||||||||      +--> script.module.pywin32ctypes (P)
  ||||||||||             |
  ||||||||||             +--> script.module.cffi (P/C)
  ||||||||||             |      |
  ||||||||||             |      +--> libffi (C)
  ||||||||||             |      +--> script.module.pycparser (P)
  ||||||||||             |      +------------------------------------+--> script.module.abi (P)
  ||||||||||             |                                           |
  |||||||||+--> script.module.crytography (P/C)                      |
  |||||||||       |                                                  |
  |||||||||       +--------------------------------------------------+
  |||||||||       +--> script.module.idna (P)                        |
  |||||||||       +--> script.module.pyasn1 (P)                      |
  |||||||||       +--> script.module.six (P)                         |
  |||||||||       +--> script.module.enum (P)                        |
  |||||||||       +--> script.module.ipaddress (P)                   |
  |||||||||       +------------------------------+--> OpenSSL (C)    |
  |||||||||                                      |                   |
  ||||||||+--> script.module.m2crypto (P/C)      |                   |
  ||||||||       |                               |                   |
  ||||||||       +-------------------------------+                   |
  ||||||||       +---------------------------------------------------+
  ||||||||                                                           |
  |||||||+--> script.module.libnacl (P)                              |
  |||||||       |                                                    |
  |||||||       +----------------------------------------------------+
  |||||||       +--> libsodium (C)                                   |
  |||||||                                                            |
  ||||||+--> script.module.apsw (P/C)                                |
  ||||||       |                                                     |
  ||||||       +-----------------------------------------------------+
  ||||||       +--> libsqlite3 (C)                                   |
  ||||||                                                             |
  |||||+--> script.module.plyvel (P/C++)                             |
  |||||       |                                                      |
  |||||       +------------------------------------------------------+
  |||||       +--> LevelDB (C++)                                     |
  |||||               |                                              |
  |||||               +--> Boost (C++)                               |
  |||||               |                                              |
  ||||+--> script.module.libtorrent (P/C++)                          |
  ||||       |                                                       |
  ||||       +-------------------------------------------------------+
  ||||                                                               |
  |||+--> script.module.netifaces (P/C)                              |
  |||       |                                                        |
  |||       +--------------------------------------------------------+
  ||| 
  ||+--> script.module.chardet (P)
  ||
  |+--> script.module.cherrypy (P)
  |       |
  |       +--> script.module.cheroot (P)
  |       +--> script.module.six (P)
  |       +--> script.module.portend (P)
  |
  +--> script.module.tempora (P)

(P) : Python Code
(C) : C Code
(C++) : C++ Code 
```
