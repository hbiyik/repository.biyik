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
import six

from distutils.version import LooseVersion

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


def yesno(title, *lines, **kwargs):
    dialog = xbmcgui.Dialog()
    # this is weak and wrong
    return dialog.yesno(title, *lines, **kwargs)


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
    if six.PY2:
        text = kb.getText().decode("utf-8")
    else:
        text = kb.getText()
    return kb.isConfirmed(), text


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
