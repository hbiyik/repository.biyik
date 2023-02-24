'''
Created on Feb 18, 2023

@author: boogie
'''
from tinyxbmc import addon
from tinyxbmc import const
from tinyxbmc import net
from tinyxbmc.distversion import LooseVersion
from tinyxbmc.stubmod import isstub

import six
import ghub
import xbmc
import os
import re
import traceback


if addon.has_addon("plugin.program.aceengine"):
    addon.depend_addon("plugin.program.aceengine")
    import aceengine
else:
    aceengine = None


def installwidevine():
    HASWV = False
    CDMVER = None
    try:
        ishelper = ghub.load("emilsvennesson", "script.module.inputstreamhelper", "master", period=24 * 7, path=["lib"])
        fname = os.path.join(ishelper, "lib", "inputstreamhelper", "kodiutils.py")
        with open(fname) as f:
            src = f.read()
        src = re.sub("script\.module\.inputstreamhelper", "script.module.tinyxbmc", src)
        with open(fname, "w") as f:
            f.write(src)
        import inputstreamhelper
        inputstreamhelper.ok_dialog = lambda *args, **kwargs: True
        inputstreamhelper.widevine_eula = lambda *args, **kwargs: True
        helper = inputstreamhelper.Helper("mpd")
        HASWV = inputstreamhelper.has_widevinecdm()
        canwv = helper._supports_widevine()
        if not canwv:
            addon.log("MPD: Widewine is not supported by platform")
        if not HASWV and canwv:
            helper.install_widevine()
            HASWV = True
        if HASWV:
            CDMVER = LooseVersion(helper._get_lib_version(inputstreamhelper.widevinecdm_path()))
            addon.log("MPD: Widewine is enabled with CDM version %s" % CDMVER)
    except Exception as e:
        print(traceback.format_exc())
        
    return HASWV, CDMVER


class url(dict):
    HASISA = addon.has_addon(const.INPUTSTREAMADAPTIVE) and addon.addon_details(const.INPUTSTREAMADAPTIVE).get("enabled")
    HASFFDR = addon.has_addon(const.INPUTSTREAFFMPEGDIRECT) and addon.addon_details(const.INPUTSTREAFFMPEGDIRECT).get("enabled")
    
    def __init__(self, manifest=None, adaptive=True, ffmpegdirect=True, noinputstream=True, **kwargs):
        self.adaptive = adaptive
        self.ffmpegdirect = ffmpegdirect
        self.noinputstream = noinputstream
        self.manifest = manifest
        for k, v in kwargs.items():
            setattr(self, k, v)
        dict.__init__(self, manifest=self.manifest,
                            adaptive=self.adaptive,
                            ffmpegdirect=self.ffmpegdirect,
                            noinputstream=self.noinputstream,
                            **kwargs)

    def props(self):
        props = {}
        if self.inputstream:
            if int(xbmc.getInfoLabel('System.BuildVersion')[:2]) >= 19:
                props['inputstream'] = self.inputstream
            else:
                props['inputstreamaddon'] = self.inputstream
        if self.manifest:
            props['inputstream.adaptive.manifest_type'] = self.manifest
        return props
    
    @property
    def inputstream(self):
        if self.HASISA and self.adaptive:
            return const.INPUTSTREAMADAPTIVE
        elif self.HASFFDR and self.ffmpegdirect:
            return const.INPUTSTREAFFMPEGDIRECT
        return None


class hlsurl(url):
    def __init__(self, url, headers=None, adaptive=True, ffmpegdirect=True, noinputstream=True):
        super(hlsurl, self).__init__(const.MANIFEST_HLS, adaptive, ffmpegdirect, noinputstream, url=url, headers=headers or {})

    @property
    def kodiurl(self):
        return net.tokodiurl(self.url, headers=self.headers, pushverify="false", pushua=const.USERAGENT)
    
    def props(self):
        props = super(hlsurl, self).props()
        props['inputstream.adaptive.manifest_type'] = self.manifest
        return props


class mpdurl(url):
    HASWV = False
    CDMVER = None

    if url.HASISA:
        HASWV, CDMVER = installwidevine()
    else:
        addon.log("MPD: Inputstream.adaptive is not installed")

    if isstub():
        HASWV = True

    def __init__(self, url, headers=None, lurl=None, lheaders=None, lbody="R{SSM}", lresponse="", mincdm=None):
        self.license = "com.widevine.alpha"
        if isinstance(mincdm, six.string_types):
            mincdm = LooseVersion(mincdm)
        else:
            mincdm = None
        headers = headers or {}
        lheaders = lheaders or {}
        super(mpdurl, self).__init__(const.MANIFEST_MPD, True, False, False, license=license, mincdm=mincdm, url=url, headers=headers,
                                     lurl=lurl, lheaders=lheaders, lbody=lbody, lresponse=lresponse)

    @property
    def inputstream(self):
        inputstream = None
        if self.lurl:
            if self.HASWV:
                if self.mincdm:
                    if self.mincdm <= self.CDMVER:
                        inputstream = const.INPUTSTREAMADAPTIVE
                    else:
                        addon.log("MPD: Available CDM version (%s) is not >= minimum required (%s): %s" % (self.CDMVER,
                                                                                                           self.mincdm,
                                                                                                           self.url))
                else:
                    inputstream = const.INPUTSTREAMADAPTIVE
            else:
                addon.log("MPD: DASH stream requires drm but widewine is not available: %s" % (self.url))
        elif self.HASISA:
            inputstream = const.INPUTSTREAMADAPTIVE
        return inputstream

    @property
    def kodiurl(self):
        return net.tokodiurl(self.url, headers=self.headers, pushverify="false", pushua=const.USERAGENT)

    @property
    def kodilurl(self):
        if self.lurl:
            lurl = net.tokodiurl(self.lurl, headers=self.lheaders)
            if "|" not in lurl:
                return lurl + "|"
            return "%s|%s|%s" % (lurl, self.lbody, self.lresponse)

    def props(self):
        props = super(hlsurl, self).props()
        props['inputstream.adaptive.manifest_type'] = self.manifest
        if self.lurl:
            props['inputstream.adaptive.license_type'] = self.license
            self.lurl, self.lheaders = net.fromkodiurl(net.tokodiurl(self.lurl, headers=self.lheaders, pushua=const.USERAGENT, pushverify="false"))
        props['inputstream.adaptive.license_key'] = self.kodilurl
        return props


class acestreamurl(url):
    def __init__(self, url, adaptive=False, ffmpegdirect=True, noinputstream=True):
        super(acestreamurl, self).__init__(const.MANIFEST_ACE, adaptive, ffmpegdirect, noinputstream, url=url)
        if aceengine:
            self.aceurl = aceengine.acestream(self.url)
        else:
            self.aceurl = None

    @property
    def kodiurl(self):
        if aceengine:
            return self.aceurl.httpurl


def urlfromdict(url):
    if isinstance(url, dict):
        manifest = url.pop("manifest")
        if manifest == const.MANIFEST_HLS:
            return hlsurl(**url)
        elif manifest == const.MANIFEST_MPD:
            return mpdurl(**url)
        elif manifest == const.MANIFEST_ACE:
            return acestreamurl(**url)
    else:
        return url
