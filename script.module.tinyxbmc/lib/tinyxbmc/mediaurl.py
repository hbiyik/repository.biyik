'''
Created on Feb 18, 2023

@author: boogie
'''
from tinyxbmc import addon
from tinyxbmc import net
from tinyxbmc import const
from tinyxbmc.distversion import LooseVersion
from tinyxbmc.stubmod import isstub

import ghub
import xbmc
import os
import re
import traceback
from urllib import parse

aceengine = None
if addon.has_addon("plugin.program.aceengine"):
    addon.depend_addon("plugin.program.aceengine")
    import aceengine


HEADER_CONFIG = {"pushnoverify": True,
                 "pushua": True,
                 "pushcookie": True}


def installwidevine():
    HASWV = False
    CDMVER = None
    try:
        ishelper = ghub.load("emilsvennesson", "script.module.inputstreamhelper", "master", period=24 * 7, path=["lib"])
        fname = os.path.join(ishelper, "lib", "inputstreamhelper", "kodiutils.py")
        with open(fname) as f:
            src = f.read()
        src = re.sub(r"script\.module\.inputstreamhelper", "script.module.tinyxbmc", src)
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
    except Exception as _e:
        addon.log(traceback.format_exc())

    return HASWV, CDMVER


class BaseUrl(dict):
    mediaurltype = const.URL_BASE
    url = None

    @staticmethod
    def fromdict(dct):
        mediaurltype = dct.get("mediaurltype")
        if not mediaurltype:
            return dct
        urltype = URLTYPES.get(mediaurltype)
        if not urltype:
            return
        dct.pop("mediaurltype")
        return urltype(**dct)

    def __init__(self, **kwargs):
        kwargs["mediaurltype"] = self.mediaurltype
        for k, v in kwargs.items():
            setattr(self, k, v)
        dict.__init__(self, **kwargs)

    def __str__(self):
        return self.prettyurl

    @property
    def kodiurl(self):
        return self.url

    @property
    def prettyurl(self):
        return "%s(%s)" % (self.mediaurltype.title(), self.url)

    @property
    def inputstream(self):
        return


class AddonUrl(BaseUrl):
    mediaurltype = const.URL_ADDON

    def __init__(self, addon, path="", query=None):
        super().__init__(addon=addon,
                         path=path,
                         query=query or {})

    @staticmethod
    def parse(url):
        if not url.startswith("plugin://"):
            return
        parsed = parse.urlparse(url)
        return AddonUrl(parsed.domain, parsed.path, parsed.query)

    @property
    def url(self):
        return f"plugin://{self.addon}/{self.path}?{parse.urlencode(self.query)}"


class LinkUrl(BaseUrl):
    mediaurltype = const.URL_LINK

    def __init__(self, url, headers=None, **kwargs):
        headers = net.makeheader(url, headers=headers, **HEADER_CONFIG)
        super().__init__(url=url,
                         headers=headers,
                         **kwargs)

    @property
    def kodiurl(self):
        return net.tokodiurl(self.url, self.headers)


class HlsUrl(LinkUrl):
    HASWV = False
    CDMVER = None
    manifest = const.MANIFEST_HLS
    HASISA = addon.has_addon(const.INPUTSTREAMADAPTIVE) and addon.addon_details(const.INPUTSTREAMADAPTIVE).get("enabled")
    HASFFDR = addon.has_addon(const.INPUTSTREAFFMPEGDIRECT) and addon.addon_details(const.INPUTSTREAFFMPEGDIRECT).get("enabled")
    mediaurltype = const.URL_HLS

    if HASISA:
        HASWV, CDMVER = installwidevine()
    else:
        addon.log("MPD: Inputstream.adaptive is not installed")

    if isstub():
        HASWV = True

    def __init__(self, url, headers=None, adaptive=True, ffmpegdirect=True,
                 lurl=None, lheaders=None, lbody="R{SSM}", lresponse="", lic="com.widevine.alpha", aesparams=None, mincdm=None):
        headers = headers or {}
        lheaders = lheaders or headers or {}
        headers = net.makeheader(url, headers=lheaders, **HEADER_CONFIG)
        lheaders = net.makeheader(lurl or url, headers=lheaders, **HEADER_CONFIG)
        aesparams = aesparams or {}
        if mincdm:
            mincdm = LooseVersion(mincdm)
        super(HlsUrl, self).__init__(url, headers,
                                     adaptive=adaptive, ffmpegdirect=ffmpegdirect,
                                     lurl=lurl, lheaders=lheaders, lbody=lbody, lresponse=lresponse, lic=lic,
                                     aesparams=aesparams, mincdm=mincdm)

    @property
    def kodilurl(self):
        if self.lurl:
            return "%s|%s|%s|%s" % (self.lurl, parse.urlencode(self.lheaders), self.lbody, self.lresponse)
        else:
            return "%s|%s" % (parse.urlencode(self.aesparams), parse.urlencode(self.lheaders))

    def props(self):
        props = {}
        if int(xbmc.getInfoLabel('System.BuildVersion')[:2]) >= 19:
            props['inputstream'] = self.inputstream
        else:
            props['inputstreamaddon'] = self.inputstream
        headers = parse.urlencode(self.headers)
        props['inputstream.adaptive.manifest_type'] = const.MANIFEST_HLS
        props['inputstream.adaptive.stream_headers'] = headers
        props['inputstream.adaptive.manifest_headers'] = headers
        if self.lurl:
            props['inputstream.adaptive.license_type'] = self.license
        props['inputstream.adaptive.license_key'] = self.kodilurl
        return props

    @property
    def inputstream(self):
        if (self.lurl or self.aesparams) and not self.HASISA:
            addon.log("HLS stream requires drm but inputstream.adaptive is not available: %s" % (self.url))
            return
        if self.mincdm and (self.mincdm > self.CDMVER or not self.HASISA):
            addon.log("HLS stream requires widewine but widewine is not available: %s" % (self.url))
            return
        if self.HASISA and self.adaptive:
            return const.INPUTSTREAMADAPTIVE
        elif self.HASFFDR and self.ffmpegdirect:
            return const.INPUTSTREAFFMPEGDIRECT


class AceUrl(BaseUrl):
    mediaurltype = const.URL_ACE

    def __init__(self, url):
        super(AceUrl, self).__init__(url=url)
        if aceengine:
            self.aceurl = aceengine.acestream(self.url)
        else:
            self.aceurl = None

    @property
    def kodiurl(self):
        if aceengine:
            return self.aceurl.httpurl


URLTYPES = {const.URL_BASE: BaseUrl,
            const.URL_LINK: LinkUrl,
            const.URL_ADDON: AddonUrl,
            const.URL_HLS: HlsUrl,
            const.URL_ACE: AceUrl}
