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
import importlib
import gc

from tinyxbmc import tools
from tinyxbmc import hay
from tinyxbmc import const

import xbmc

global _xhay

_debug = True
_addons = None
_xhay = None



def loadmodule(modname, *paths):
    spec = importlib.machinery.PathFinder.find_spec(modname, paths)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
    data = {"jsonrpc": "2.0",
            "method": "Addons.GetAddons",
            "id": 1,
            "params": {"properties": ["name",
                                      "version",
                                      "path",
                                      "dependencies",
                                      "enabled",
                                      "broken",
                                      ],
                       "enabled": True,
                       }
            }
    
    addons = {}
    for addon in json.loads(xbmc.executeJSONRPC(json.dumps(data)))["result"]["addons"]:
        addons[addon["addonid"]] = addon
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
    if not exclude:
        exclude = []
    addons = getaddons()
    adn = addons.get(addon)
    if adn is None or adn["addonid"] in exclude:
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


def doesinherit(cls, parents=None):
    parents = parents or []
    badchild = False
    for parent in parents:
        if not inspect.isclass(parent) or not issubclass(cls, parent) or cls == parent:
            badchild = True
    return not badchild


def getobjects(*directories, mod=None, cls=None, parents=None):
    '''
    Collects the class objects in a given directory.
    The objects can be narrowed by the module name, class name, and the
    classes that they must be inherited from.
    '''
    # find all files in dir
    for directory in directories:
        if directory not in sys.path:
            sys.path.append(directory)
    for finder, modname, _ispkg in pkgutil.walk_packages(directories):
        try:
            spec = finder.find_spec(modname)
            imod = importlib.util.module_from_spec(spec)
            if inspect.getfile(imod).endswith("__init__.py"):
                continue
            if mod and imod.__name != mod:
                continue
            spec.loader.exec_module(imod)
        except Exception as e:
            print("Object Loading Error: %s: %s, exception: %s" % (finder.path, modname, e))
            print(traceback.format_exc())
            continue
        gc.collect()
        for _k, icls in vars(imod).items():
            # k: class name, icls: imported class object
            if not inspect.isclass(icls):
                # skip other objects which are not classes
                continue
            if not doesinherit(icls, parents):
                continue
            if cls and cls != icls.__name__:
                continue 
            print("Object Loaded: %s.%s" % (modname, icls.__name__))
            yield imod, icls


def getplugins(pid, addon=None, path=None, package=None, module=None, instance=None):
    if not isinstance(pid, (tuple, list)):
        pid = (pid,)
    for addonid, adn in getaddons().items():
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
            if plugin["id"] not in pid:
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
                    m = loadmodule(subm, *paths)
                except Exception:
                    print(traceback.format_exc())
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
