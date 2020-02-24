# -*- coding: utf-8 -*-
'''
    Author    : Huseyin BIYIK <husenbiyik at hotmail>
    Year      : 2016
    License   : GPL

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import os
import pkgutil
import traceback
import inspect
import json
import sys
import imp
import gc

from tinyxbmc import tools
from tinyxbmc import hay
from tinyxbmc import const

import xbmc

_debug = True
_addons = None
_xhay = None


def _doesinherit(cls, parents=None):
    if not parents:
        parents = []
    badchild = False
    for parent in parents:
        if not issubclass(cls, parent) or cls == parent:
            badchild = True
    return not badchild


def getaddons(cache=True):
    global _addons
    if cache and _addons:
        return _addons
    '''Returns the list of installed addons in Kodi in a dict.

    Returns:
        {
        "addonid":{
            "name":str,
            "version":str,
            "path","str",
            "dependencies":[addonid,...],
            "enabled":Bool
            }
        }
    '''
    data = {
        "jsonrpc": "2.0",
        "method": "Addons.GetAddons",
        "id": 1,
        "params": {"properties": [
                                  "name",
                                  "version",
                                  "path",
                                  "dependencies",
                                  "enabled",
                                  "broken",
                                  ],
                   "enabled": True,
                   }
        }
    addons = json.loads(xbmc.executeJSONRPC(json.dumps(data)))
    addons = addons["result"]["addons"]
    if cache:
        _addons = addons
    return addons


def _openxhay():
    global _xhay
    if not _xhay:
        _xhay = hay.stack(const.ADDONHAY)
    return _xhay


def _closexhay():
    global _xhay
    if _xhay:
        _xhay.close()
        _xhay = None


def _readxml(axml, _xhay):
    xsize = os.stat(axml).st_size
    xhash = "%s%s" % (axml, xsize)
    xneedle = _xhay.find(xhash)
    if xneedle.data == {}:
        xneedle.data = {"plugins": [], "libraries": []}
        dxml = tools.readdom(axml)
        if not dxml:
            return xneedle.data["plugins"], xneedle.data["libraries"]
        txbmc = dxml.getElementsByTagName(const.XMLROOTNODE)
        if len(txbmc):
            for plugin in txbmc[0].getElementsByTagName(const.XMLPLUGINNODE):
                p = {}
                for attr in const.XMLPLUGINATTRS:
                    p[attr] = plugin.getAttribute(attr)
                    if p[attr] == "":
                        p[attr] = None
                if not p == {}:
                    xneedle.data["plugins"].append(p.copy())
        for ext in dxml.getElementsByTagName("extension"):
            if ext.getAttribute("point") == "xbmc.python.module":
                lib = ext.getAttribute("library")
                if lib:
                    xneedle.data["libraries"].append(lib)
        _xhay.throw(xhash, xneedle.data)
    return xneedle.data["plugins"], xneedle.data["libraries"]


def addonattrs(addon, depends=None, exclude=None):
    '''Collects the paths of the __addon the paths of its dependecies
    given by id.

    Example:
        import boogie

        class navi(boogie.container):
            @boogie.contianer
            def index(self):
                paths, dpaths = self.api.addonpaths("script.module.six")

    Params:
        __addon: string indicating the addonid
        depends: require the __addon given by the to depend on a
        specific __addon

    Returns:
        [[paths of the __addon], [paths of its dependencies]]

    '''
    found = False
    if not exclude:
        exclude = []
    addons = getaddons()
    for adn in addons:
        if addon == adn["addonid"]:
            found = True
            break
    if not found or adn["addonid"] in exclude:
        return [], [], []
    exclude.append(adn["addonid"])
    axml = os.path.join(adn["path"], "addon.xml")
    if not os.path.exists(axml):
        return [], [], []
    plugins, libraries = _readxml(axml, _openxhay())
    imps = []
    slibs = []
    dlibs = []
    for req in adn["dependencies"]:
        if req["addonid"] == "xbmc.python":
            continue
        if req["addonid"] == depends:
            depends = None
        imps.append(req["addonid"])
    if depends is None:
        slibs.append(adn["path"])
        for lib in libraries:
            ldir = os.path.join(adn["path"], lib)
            slibs.append(ldir)
        for im in imps:
            impslibs, impdlibs, _ = addonattrs(im, None, exclude)
            dlibs.extend(impslibs)
            dlibs.extend(impdlibs)
    return slibs, dlibs, plugins


def getobjects(directory, mod=None, cls=None, parents=None, stack=None):
    '''
    Collects the class objects in a given directory.
    The objects can be narrowed by the module name, class name, and the
    classes that they must be inherited from.
    '''
    # find all files in dir
    if not parents:
        parents = []
    if mod:
        files = [mod]
    else:
        files = []
        dirs = [x[0] for x in os.walk(directory)]
        packages = []
        for im, pck, ispkg in pkgutil.iter_modules(dirs):
            path = os.path.relpath(im.path, directory)
            path = path.replace(os.path.sep, ".")
            if path in packages:
                mod = path + "." + pck
            elif path == pck or path == ".":
                mod = pck
            else:
                continue
            if ispkg:
                packages.append(mod)
            files.append(mod)
    pid = ""
    for parent in parents:
        pid += inspect.getfile(parent)
        pid += parent.__name__
    for f in files:
        # prepare sys.path for import
        # import module
        gc.collect()
        objid = os.path.join(directory, f + ".py")
        if not os.path.exists(objid):
            print "Skipping %s" % objid
            continue
        objid += str(os.path.getsize(objid)) + pid
        if stack:
            cache = stack.find(objid).data
        else:
            cache = {}
        if cache.get("skip"):
            continue
        if directory not in sys.path:
            sys.path.append(directory)
        try:
            imod = imp.load_module(f, *imp.find_module(f, [directory]))
            clsd = vars(imod)
        except Exception:
            print "Error Loading File: %s: %s" % (directory, f)
            cache["skip"] = True
            if stack:
                stack.throw(objid, cache)
            if _debug:
                print traceback.format_exc()
            continue
        # gc.collect()
        # dont import if module is already imported,
        # sometimes when this function is called from getplugins
        # root path points to file from either plugin rootdir
        # or plugin include dir ie. lib folder
        found = False
        for k, icls in clsd.iteritems():
            # k: class name, icls: imported class object
            if cls and not k == cls:
                # if specific class is defined, skip other classes
                continue
            if not inspect.isclass(icls):
                # skip other objects which are not classes
                continue
            if not _doesinherit(icls, parents):
                continue
            found = True
            yield imod, icls
        cache["skip"] = not found
        if stack:
            stack.throw(objid, cache)


def getplugins(id, addon=None, path=None, package=None, module=None, instance=None):
    if not isinstance(id, (tuple, list)):
        id = (id,)
    for adn in getaddons():
        if (addon and not adn["addonid"] == addon) or adn["broken"]:
            continue
        slibs, dlibs, plugins = addonattrs(adn["addonid"])
        if not len(plugins):
            continue
        for p in slibs + dlibs:
            if p not in sys.path:
                sys.path.append(p)
        for plugin in plugins:
            if path and not plugin["path"] == path:
                continue
            if plugin["path"]:
                pp = os.path.join(adn["path"], plugin["path"])
                if pp not in sys.path:
                    sys.path.append(pp)
            if plugin["id"] not in id:
                continue
            ppackage = plugin["package"]
            pmodule = plugin["module"]
            pinstance = plugin["instance"]
            if package and not package == ppackage:
                continue
            if module and not module == pmodule:
                continue
            if instance and not instance == pinstance:
                continue
            modules = []
            if ppackage:
                modules = ppackage.split(".")
                modules.append(pmodule)
            else:
                modules = [pmodule]
            m = None
            for subm in modules:
                if m:
                    paths = [m.__path__]
                else:
                    paths = sys.path
                try:
                    m = imp.load_module(subm, *imp.find_module(subm, paths))
                except Exception:
                    print traceback.format_exc()
                    continue
            if pinstance:
                if not hasattr(m, pinstance):
                    continue
                ob = getattr(m, pinstance)
            else:
                ob = m
            plugin["addon"] = adn["addonid"]
            ob._tinyxbmc = plugin
            yield ob
    _closexhay()
