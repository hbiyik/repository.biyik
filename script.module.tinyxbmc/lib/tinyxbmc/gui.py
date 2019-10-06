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
import xbmcgui
import xbmc
import os
import math

from distutils.version import LooseVersion

from tinyxbmc import addon
from tinyxbmc import hay
from tinyxbmc import const

__artdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "images")
_white = os.path.join(__artdir, "white.png")
_gray = os.path.join(__artdir, "gray.png")
_black = os.path.join(__artdir, "black.png")
_red = os.path.join(__artdir, "red.png")


def browse(typ, heading, shares="files", mask="", useThumbs=True, treatAsFolder=True,
           default="", enableMultiple=False):
    '''
    Types:
    - 0 : ShowAndGetDirectory
    - 1 : ShowAndGetFile
    - 2 : ShowAndGetImage
    - 3 : ShowAndGetWriteableDirectory
    '''
    dialog = xbmcgui.Dialog()
    return dialog.browse(typ, heading, shares, mask, useThumbs, treatAsFolder,
                         default, enableMultiple)
    

def textviewer(heading, text, mono=False):
    dialog = xbmcgui.Dialog()
    return dialog.textviewer(heading, text)


def select(heading, options, autoclose=0, preselect=None, useDetails=False, multi=False):
    dialog = xbmcgui.Dialog()
    if multi:
        if not preselect:
            preselect = []
        return dialog.multiselect(heading, options, autoclose, preselect, useDetails)
    else:
        if not preselect:
            preselect = -1
        return dialog.select(heading, options, autoclose, preselect, useDetails)


def notify(title, content, sound=True, typ=None):
    if LooseVersion(xbmcgui.__version__) >= LooseVersion("2.14.0"):  # @UndefinedVariable
        if not typ:
            typ = xbmcgui.NOTIFICATION_INFO
        dialog = xbmcgui.Dialog()
        dialog.notification(title, content, typ, sound=sound)
    else:
        xbmc.log("%s : %s" % (title, content))


def ok(title, *lines):
    dialog = xbmcgui.Dialog()
    dialog.ok(title, *lines)


def warn(title, content, sound=True):
    notify(title, content, sound=sound, typ=xbmcgui.NOTIFICATION_WARNING)


def error(title, content, sound=True):
    notify(title, content, sound=sound, typ=xbmcgui.NOTIFICATION_ERROR)


def progress(name):
    dialog = xbmcgui.DialogProgress()
    dialog.create(name)
    return dialog


def bgprogress(name):
    dialog = xbmcgui.DialogProgressBG()
    dialog.create(name)
    return dialog


def keyboard(default="", heading=None, hidden=False):
    kb = xbmc.Keyboard(default, heading, hidden)
    kb.doModal()
    text = kb.getText()
    return kb.isConfirmed(), text


class form(addon.blockingloop, xbmcgui.WindowDialog):
    def __init__(self, w1, w2, header="", *args, **kwargs):
        xbmcgui.WindowDialog.__init__(self)
        self.setCoordinateResolution(0)
        self.wait = 0.1
        #  1920x1080
        self.__cw = 1920
        self.__ch = 1080
        self.__w1 = w1
        self.__w2 = w2
        self.__padx = 25
        self.__rowh = 43  # changes depending on the selected skin :(
        self.__pady = self.__padx - 10
        self.__elems = {}
        self.__cmap = {}
        self.__eid = 0
        self.__numbtns = 0
        self.__focus = None
        self.__etypes = {
                "label": ("setLabel", "getLabel", [], False),
                "edit": ("setText", "getText", [], True),
                "text": ("setText", "reset", [], False),
                "bool": ("setSelected", "isSelected", [], True),
                "button": ("setLabel", "getLabel", [], True),
                "list": ("getSelectedPosition", "selectItem", [], False),
                "image": ("setImage", "getId", [], False),
                }
        self.__pre = None
        self.__header = header
        with hay.stack(const.OPTIONHAY, write=False) as stack:
            ua = stack.find("useragent").data
            if ua == {}:
                ua = const.USERAGENT
            self.__useragent = ua
        addon.blockingloop.__init__(self, *args, **kwargs)

    def oninit(self):
        if not self.terminate:
            self.__create(self.__header)
            if self.__focus:
                self.focus(self.__focus)
            self.show()

    def __pos(self, eid, x, y, w, h):
        elem = self.getelem(eid)
        elem.setPosition(x, y)
        elem.setWidth(w)
        elem.setHeight(h)
        elem.setVisible(True)
        elem.setEnabled(True)
        self.addControl(elem)
        self.__cmap[elem.getId()] = eid
        if self.__pre:
            self.__pre.controlDown(elem)
            self.__pre.controlRight(elem)
            elem.controlUp(self.__pre)
            elem.controlLeft(self.__pre)
        if not self.__focus:
            typ, lbl, clck, fcs, h, felem = self.__elems[eid]
            if self.__etypes[typ][3]:
                self.__focus = eid
                self.setFocus(felem)
        self.__pre = elem
        return elem

    def __row(self, eid, rx, y, rh, wdth, label):
        if label is not None:
            self.addControl(xbmcgui.ControlLabel(rx, y, self.__w1, rh,
                                                 label))
            x = rx + self.__w1
            w = self.__w2
        else:
            x = rx
            w = self.__w1 + self.__w2
        if wdth is int and wdth < w:
            w = wdth
        self.__pos(eid, x, y, w, rh)
        return y + rh + self.__pady

    def __create(self, header):
        h = 0
        w = self.__w1 + self.__w2
        bw = minbuttonw = (w - self.__padx * 2) / 3
        for eid, elem in self.__elems.iteritems():
            if not elem[0] == "button":
                h += elem[-2] + self.__pady
        bsize = int(w / minbuttonw)
        h += int(math.ceil(float(self.__numbtns) / bsize) *
                 (self.__rowh + self.__pady))  # ;) math porn
        h -= self.__pady
        x = rx = (self.__cw - w) / 2
        y = ry = (self.__ch - h) / 2
        self.addControl(xbmcgui.ControlImage(
                                             rx - self.__padx,
                                             ry - self.__pady - self.__rowh,
                                             w + 2 * self.__padx,
                                             self.__rowh,
                                             _red
                                             )
                        )
        self.addControl(xbmcgui.ControlLabel(
                                             rx,
                                             ry - self.__pady - self.__rowh,
                                             w + 2 * self.__padx,
                                             self.__rowh,
                                             header,
                                             )
                        )
        self.addControl(xbmcgui.ControlImage(
                                             rx - self.__padx,
                                             ry - self.__pady,
                                             w + 2 * self.__padx,
                                             h + 2 * self.__pady,
                                             _black
                                             )
                        )

        for eid, (typ, label, clck, wdth, rh, elem) in self.__elems.iteritems():
            if typ in ["label", "edit", "text", "bool", "list", "image"]:
                y = self.__row(eid, rx, y, rh, wdth, label)
            if typ == "progress":
                self.addControl(xbmcgui.ControlImage(rx, y, w, rh, _gray))
                self.__pos(eid, rx, y, 0, rh)
                y += self.__rowh + self.__pady
            if typ == "text" and False:
                elem.autoScroll(1, 1000, 1)
        numbtns = 0
        for eid, (typ, label, clck, fcs, rh, elem) in self.__elems.iteritems():
            if typ == "button":
                if minbuttonw * self.__numbtns + self.__padx * (self.__numbtns - 1) < w:
                    bw = (w - (self.__numbtns - 1) * self.__padx) / self.__numbtns
                else:
                    bw = (w - (bsize - 1) * self.__padx) / bsize
                self.__pos(eid, x, y, bw, rh)
                x += bw + self.__padx
                numbtns += 1
                if x + minbuttonw > rx + w:
                    x = rx
                    y += self.__rowh + self.__pady
                    self.__numbtns -= numbtns
                    numbtns = 0

    @staticmethod
    def __null(*args, **kwargs):
        pass

    def focus(self, eid):
        typ, lbl, clck, fcs, h, elem = self.__elems[eid]
        if self.__etypes[typ][3]:
            self.__focus = eid
            self.setFocus(elem)

    def getelem(self, eid):
        return self.__elems[eid][-1]

    def enable(self, eid):
        typ, lbl, clck, fcs, h, elem = self.__elems[eid]
        if not typ == "progress":
            elem.setEnabled(True)

    def disable(self, eid):
        typ, lbl, clck, fcs, h, elem = self.__elems[eid]
        if not typ == "progress":
            elem.setEnabled(False)

    def get(self, eid):
        typ, lbl, clck, fcs, h, elem = self.__elems[eid]
        if typ == "progress":
            return elem.getWidth() * 100 / (self.__w1 + self.__w2)
        else:
            setter, getter, args, canfocus = self.__etypes[typ]
            return getattr(elem, getter)(*args)

    def set(self, eid, value):
        typ, lbl, clck, fcs, h, elem = self.__elems[eid]
        if typ == "progress":
            if value > 100:
                value = 100
            elem.setWidth(int(value * (self.__w1 + self.__w2) / 100))
        else:
            setter, getter, args, canfocus = self.__etypes[typ]
            getattr(elem, setter)(value)

    def text(self, label="", height=None):
        if not height:
            height = self.__rowh
        elem = xbmcgui.ControlTextBox(0, 0, 0, 0)
        self.__eid += 1
        self.__elems[self.__eid] = ("text",
                                    label,
                                    self.__null,
                                    None,
                                    height,
                                    elem)
        return self.__eid

    def list(self, label="", values=[], onclick=None, height=None):
        if not height:
            height = self.__rowh
        if not onclick:
            onclick = self.__null
        height = len(values) * height
        elem = xbmcgui.ControlList(0, 0, 0, 0)
        for value in values:
            elem.addItem(value)
        self.__eid += 1
        self.__elems[self.__eid] = ("list",
                                    label,
                                    onclick,
                                    None,
                                    height,
                                    elem)
        return self.__eid

    def label(self, label="", value="", height=None):
        if not height:
            height = self.__rowh
        elem = xbmcgui.ControlLabel(0, 0, 0, 0, value)
        self.__eid += 1
        self.__elems[self.__eid] = ("label",
                                    label,
                                    self.__null,
                                    None,
                                    height,
                                    elem)
        return self.__eid

    def edit(self, label="", default="", height=None):
        if not height:
            height = self.__rowh
        elem = xbmcgui.ControlEdit(0, 0, 0, 0, default)
        self.__eid += 1
        self.__elems[self.__eid] = ("edit",
                                    label,
                                    self.__null,
                                    None,
                                    height,
                                    elem)
        return self.__eid

    def bool(self, label="", onclick=None, height=None):
        if not height:
            height = self.__rowh
        if not onclick:
            onclick = self.__null
        elem = xbmcgui.ControlRadioButton(0, 0, 0, 0, "",
                                          focusTexture=_red,
                                          noFocusTexture=_white)
        self.__eid += 1
        self.__elems[self.__eid] = ("bool",
                                    label,
                                    onclick,
                                    None,
                                    height,
                                    elem)
        return self.__eid

    def button(self, label="", onclick=None):
        if not onclick:
            onclick = self.__null
        elem = xbmcgui.ControlButton(0, 0, 0, 0, label)
        self.__eid += 1
        self.__elems[self.__eid] = ("button",
                                    label,
                                    onclick,
                                    None,
                                    self.__rowh,
                                    elem)
        self.__numbtns += 1
        return self.__eid

    def image(self, label, src, height, width=None, mode=2, onclick=None):
        if not onclick:
            onclick = self.__null
        from tinyxbmc.net import kodiurl
        src = kodiurl(src, None, {"User-agent": self.__useragent})
        elem = xbmcgui.ControlImage(0, 0, 0, 0, src, mode)
        self.__eid += 1
        self.__elems[self.__eid] = ("image",
                                    label,
                                    onclick,
                                    width,
                                    height,
                                    elem)
        return self.__eid

    def progress(self, label="", height=None):
        if not height:
            height = self.__rowh
        elem = xbmcgui.ControlImage(0, 0, 0, 0, _white)
        self.__eid += 1
        self.__elems[self.__eid] = ("progress",
                                    label,
                                    None,
                                    self.__null,
                                    height,
                                    elem)
        return self.__eid

    def onAction(self, action):
        if action in [
                      10, #  xbmcgui.ACTION_PREVIOUS_MENU
                      92, #  xbmcgui.ACTION_NAV_BACK
                      ]:
            self.close()

    def onControl(self, ctrl):
        eid = self.__cmap.get(ctrl.getId())
        if eid:
            typ, lbl, clck, fcs, h, elem = self.__elems[eid]
            clck()

    def close(self):
        addon.blockingloop.close(self)
        xbmcgui.WindowDialog.close(self)

    def init(self, *args, **kwargs):
        pass

    def onclose(self):
        pass

    def onloop(self):
        pass


def setArt(item, d):
    if LooseVersion(xbmcgui.__version__) >= LooseVersion("2.14.0"):  # @UndefinedVariable
        item.setArt(d)
    else:
        icon = d.get("icon", d.get("poster", d.get("thumb")))
        thumb = d.get("thumb", d.get("poster", d.get("icon")))
        if icon:
            item.setIconImage(icon)
        if thumb:
            item.setThumbnailImage(thumb)
    return item
