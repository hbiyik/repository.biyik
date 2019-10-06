import sys
sys.path.append('../lib')
try:
    import xbmc
except ImportError:
    #kodi stubs directory
    sys.path.append(sys.argv[1])
import ghub
import pydocmd
modules = [ghub]
pages = ["introduction.md"]
pydocmd.create(modules, pages, "../README.md")
