from __future__ import absolute_import, division, unicode_literals
from future import standard_library
from future.builtins import *
# -*- coding: utf-8 -*-
import os, sys, binascii, threading, platform, datetime, math, urllib, urllib.request
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import gc

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
T = ADDON.getLocalizedString

PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
PROFILE = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')),'Cache')
if not os.path.exists(PROFILE): os.makedirs(PROFILE)

CACHE_PATH = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('profile')),'Cache')
COLOR_GIF_PATH = os.path.join(CACHE_PATH,'color_gifs')
if not os.path.exists(COLOR_GIF_PATH): os.makedirs(COLOR_GIF_PATH)

SOURCE_GIF = os.path.join(xbmcvfs.translatePath(ADDON.getAddonInfo('path')),'resources','media','white1px.gif')

TIME_DISPLAY = '%H:%M'

try:
    KODI_MAJOR_VERSION = int(xbmc.getInfoLabel('System.BuildVersion').split('.', 1)[0])
except:
    KODI_MAJOR_VERSION = 16

def ERROR(txt='',hide_tb=False,notify=False):
    if isinstance (txt,str): txt = txt #.decode("utf-8")
    short = str(sys.exc_info()[1])
    if hide_tb:
        LOG('ERROR: {0} - {1}'.format(txt,short))
        return short
    xbmc.log("_________________________________________________________________________________",2)
    LOG('ERROR: ' + txt)
    import traceback
    tb = traceback.format_exc()
    for l in tb.splitlines(): xbmc.log(str( '    ' + l),2)
    xbmc.log("_________________________________________________________________________________",2)
    xbmc.log("`")
    if notify: showNotification('ERROR: {0}'.format(short))
    return short

def LOG(message):
    message = '{0}: {1}'.format(ADDON_ID,message)
    xbmc.log(msg=message, level=xbmc.LOGINFO)

def DEBUG_LOG(message):
    if DEBUG: LOG(message)

def openSettings():
    global DEBUG
    ADDON.openSettings()
    DEBUG = getSetting('debug',False) or xbmc.getCondVisibility('System.GetBool(debug.showloginfo)')
    initTimeDisplay()

def getIcon(name,number):
    NEW_LOGOBASE = 'https://fast-guide.smoothstreams.tv/assets/images/channels/{0}-kodi.png'
    path = os.path.join(PATH,'resources','skins','Main','media','icons','channels',name+'.png')
    if os.path.exists(path):
        return path
    else:
        DEBUG_LOG("Returning default for %s" % name)
        return NEW_LOGOBASE.format(number)

def initTimeDisplay():
    global TIME_DISPLAY
    if getSetting('12_hour_times',False):
        TIME_DISPLAY = '%-I:%M %p'
        try:
            datetime.datetime.strftime(datetime.datetime.now(),'%-I:%M %p') #Some platforms can't handle the %-I
        except:
            TIME_DISPLAY = '%I:%M %p'
    else:
        TIME_DISPLAY = '%H:%M'

def timeDisplay(ms):
    h = ms / 3600000
    m = (ms % 3600000) / 60000
    s = (ms % 60000) / 1000
    return '{0:0>2}:{1:0>2}:{2:0>2}'.format(h, m, s)

def simplifiedTimeDisplay(ms):
    left, right = timeDisplay(ms).rsplit(':', 1)
    left = left.lstrip('0:') or '0'
    return left + ':' + right

def setGlobalProperty(key, val):
    xbmcgui.Window(10000).setProperty('script.smoothstreams-v3.{0}'.format(key), val)

def getGlobalProperty(key):
    xbmcgui.Window(10000).getProperty('script.smoothstreams-v3.{0}'.format(key))

def makeColorGif(hex6color,outpath):
    return 'colors/{0}.png'.format(hex6color)

# def makeColorGif(hex6color,outpath):
#     if os.path.exists(outpath): return outpath
#     gifReplace = chr(255)*6
#     try:
#         replace = binascii.unhexlify(hex6color)
#     except:
#         replace = chr(255)*3
#     replace += replace
#     with open(outpath,'w') as t:
#         with open(SOURCE_GIF,'r') as c:
#             t.write(c.read().replace(gifReplace,replace))
#     return outpath

def showNotification(message,time_ms=3000,icon_path=None,header='XBMC TTS'):
    try:
        icon_path = icon_path or xbmcvfs.translatePath(ADDON.getAddonInfo('icon'))
        xbmc.executebuiltin('Notification({0},{1},{2},{3})'.format(header,message,time_ms,icon_path))
    except RuntimeError: #Happens when disabling the addon
        LOG(message)

def kodiPlatform():
    openelec = xbmc.getCondVisibility('System.HasAddon(os.openelec.tv)') and '/OpenELEC' or ''
    try:
        if xbmc.getCondVisibility('System.Platform.Linux.RaspberryPi'):
            kplatform = 'RPi'
        elif xbmc.getCondVisibility('System.Platform.Android'):
            kplatform = 'Android'
        elif xbmc.getCondVisibility('System.Platform.ATV2'):
            kplatform = 'ATV2'
        elif xbmc.getCondVisibility('System.Platform.IOS'):
            kplatform = 'IOS'
        elif xbmc.getCondVisibility('System.Platform.OSX'):
            kplatform = 'OSX'
        elif xbmc.getCondVisibility('System.Platform.Darwin'):
            kplatform = 'Darwin'
        elif xbmc.getCondVisibility('System.Platform.Windows'):
            kplatform = 'Windows'
        elif xbmc.getCondVisibility('System.Platform.Linux'):
            kplatform = 'Linux'
    except:
        kplatform = ''
    return kplatform + openelec

def userAgent():
    base = "SSTV Kodi/v{addon_version}" # (Kodi {kodi_version}; {system} {processor}) {platform}"
    try:
        ua = base.format(
            addon_version=ADDON.getAddonInfo('version'),
            kodi_version=xbmc.getInfoLabel('System.BuildVersion'),
            system=platform.system(),
            processor=platform.machine(),
            platform=kodiPlatform()
        )
    except:
        ua = base.format(
            addon_version=ADDON.getAddonInfo('version'),
            kodi_version=xbmc.getInfoLabel('System.BuildVersion'),
            system='',
            processor='',
            platform=''
        )
    opener = urllib.request.build_opener()
    opener.addheaders = {'User-agent': ua}
    urllib.request.install_opener(opener)
    return ua

USER_AGENT = userAgent()

def getSetting(key,default=None):
    setting = ADDON.getSetting(key)
    return _processSetting(setting,default)

def _processSetting(setting,default):
    if not setting: return default
    if isinstance(default,bool):
        return setting.lower() == 'true'
    elif isinstance(default,float):
        return float(setting)
    elif isinstance(default,int):
        return int(float(setting or 0))
    elif isinstance(default,list):
        if setting: return binascii.unhexlify(setting).split('\0')
        else: return default

    return setting

def setSetting(key,value):
    value = _processSettingForWrite(value)
    ADDON.setSetting(key,value)

def _processSettingForWrite(value):
    if isinstance(value,list):
        value = binascii.hexlify('\0'.join(value))
    elif isinstance(value,bool):
        value = value and 'true' or 'false'
    return str(value)


def busyDialog(func):
    def inner(*args,**kwargs):
        try:
            xbmc.executebuiltin("ActivateWindow(10138)")
            func(*args,**kwargs)
        finally:
            xbmc.executebuiltin("Dialog.Close(10138)")
    return inner

# class KeymapOverride(object):
#     target = os.path.join(xbmcvfs.translatePath('special://userdata'),'keymaps','zzzzz-overrides-keymap.xml')
#     source = os.path.join(xbmcvfs.translatePath(xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')),'resources','zzzzz-overrides-keymap.xml')
#
#     def __enter__(self):
#         self.copyKeymap()
#         return self
#
#     def __exit__(self,etype, evalue, traceback):
#         self.removeKeymap()
#
#     def removeKeymap(self):
#         if os.path.exists(self.target): xbmcvfs.delete(self.target)
#         xbmc.executebuiltin("action(reloadkeymaps)")
#
#     def copyKeymap(self):
#         if os.path.exists(self.target): return
#         xbmcvfs.copy(self.source,self.target)
#         xbmc.executebuiltin("action(reloadkeymaps)")

class xbmcDialogSelect:
    def __init__(self,heading='Options'):
        self.heading = heading
        self.items = []

    def addItem(self,ID,display):
        self.items.append((ID,display))

    def getResult(self):
        IDs = [i[0] for i in self.items]
        displays = [i[1] for i in self.items]
        idx = xbmcgui.Dialog().select(self.heading,displays)
        if idx < 0: return None
        return IDs[idx]

class xbmcDialogProgress:
    def __init__(self,heading,line1='',line2='',line3='',update_callback=None):
        self.heading = heading
        self.line1 = line1
        self.line2 = line2
        self.line3 = line3
        self._updateCallback = update_callback
        self.lastPercent = 0
        self.setRange()
        self.dialog = xbmcgui.DialogProgress()

    def __enter__(self):
        self.create(self.heading,self.line1,self.line2,self.line3)
        self.update(0,self.line1,self.line2,self.line3)
        return self

    def __exit__(self,etype, evalue, traceback):
        self.close()

    def setRange(self,start=0,end=100):
        self.start = start
        self.end = end
        self.range = end - start

    def recalculatePercent(self,pct):
        #print '%s - %s %s %s' % (pct,self.start,self.range,self.start + int((pct/100.0) * self.range))
        return self.start + int((pct/100.0) * self.range)

    def create(self,heading,line1='',line2='',line3=''):
        self.dialog.create(heading,line1,line2,line3)

    def update(self,pct,line1='',line2='',line3=''):
        if self.dialog.iscanceled():
            return False
        pct = self.recalculatePercent(pct)
        if pct < self.lastPercent: pct = self.lastPercent
        self.lastPercent = pct
        self.dialog.update(pct,line1,line2,line3)
        return True

    def updateSimple(self,message):
        pct = 0
        if hasattr(message,'percent'): pct = message.percent
        return self.update(pct,message)

    def updateCallback(self,a):
        if self._updateCallback: return self._updateCallback(self,a)
        return True

    def iscanceled(self):
        return self.dialog.iscanceled()

    def close(self):
        self.dialog.close()

def cleanFilename(filename):
    import string
    # try:
    #     filename = unidecode.unidecode(filename).decode('utf8')
    # except:
    #     ERROR('Failed to convert chars in filename',hide_tb=True)
    filename = filename.replace(': ',' - ').strip()
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    return ''.join(c if c in valid_chars else '_' for c in filename)

SIZE_NAMES = ("B","KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
def simpleSize(size):
    """
    Converts bytes to a short user friendly string
    Example: 12345 -> 12.06 KB
    """
    s = 0
    if size > 0:
        i = int(math.floor(math.log(size,1024)))
        p = math.pow(1024,i)
        s = round(size/p,2)
    if (s > 0):
        return '%s %s' % (s,SIZE_NAMES[i])
    else:
        return '0B'

def durationToShortText(seconds):
    """
    Converts seconds to a short user friendly string
    Example: 143 -> 2m 23s
    """
    days = int(seconds/86400)
    if days: return '%sd' % days
    left = seconds % 86400
    hours = int(left/3600)
    if hours: return '%sh' % hours
    left = left % 3600
    mins = int(left/60)
    if mins: return '%sm' % mins
    sec = int(left % 60)
    if sec: return '%ss' % sec
    return '0s'

def notify(heading,message,icon=ADDON.getAddonInfo('icon'),time=5000,sound=True):
    try:
        xbmcgui.Dialog().notification(heading,message,icon,time,sound)
    except Exception as e:
        ERROR(str(e))
        LOG('Pre-Gotham Notification: {0}: {1}'.format(repr(heading),repr(message)))

def about():
    serviceVersion = xbmc.getInfoLabel('Window(10000).Property(service.url.downloader.VERSION)')
    serviceVersionInstalled = xbmc.getInfoLabel('System.AddonVersion(service.url.downloader)')
    serviceVersionInstalled = serviceVersion == serviceVersionInstalled and serviceVersionInstalled or '[COLOR FFFF0000]{0}[/COLOR]'.format(serviceVersionInstalled)
    xbmcgui.Dialog().ok('About','Version:  [B]{0}[/B]'.format(ADDON.getAddonInfo('version')),'','Recording Service Version:  [B]{0}[/B]   Installed:  [B]{1}[/B]'.format(serviceVersion,serviceVersionInstalled))

def garbageCollect():
    gc.collect(2)

class CronReceiver(object):
    def tick(self): pass
    def minute(self): pass
    def halfHour(self): pass
    def day(self): pass
    def minute(self): pass

class Cron(threading.Thread):
    def __init__(self,interval):
        threading.Thread.__init__(self)
        self.stopped = threading.Event()
        self.interval = interval
        from .smoothstreams import timeutils
        self.timeutils = timeutils
        self._lastMinute = self._getMinute()
        self._lastHalfHour = self._getHalfHour()
        self._receivers = []

    def __enter__(self):
        self.start()
        DEBUG_LOG('Cron started')
        return self

    def __exit__(self,exc_type,exc_value,traceback):
        self.stop()
        self.join()

    def _wait(self):
        ct=0
        while ct < self.interval:
            xbmc.sleep(100)
            ct+=0.1
            if xbmc.Monitor().abortRequested() or self.stopped.isSet(): return False
        return True

    def stop(self):
        self.stopped.set()

    def run(self):
        while self._wait():
            self._tick()
        DEBUG_LOG('Cron stopped')

    def _getHalfHour(self):
        tid = self.timeutils.timeInDayLocalSeconds()/60
        return tid - (tid % 30)

    def _getMinute(self):
        tid = self.timeutils.timeInDayLocalMinutes()
        return tid

    def _tick(self):
        receivers = list(self._receivers)
        receivers = self._halfHour(receivers)
        receivers = self._minute(receivers)
        for r in receivers:
            try:
                r.tick()
            except Exception as e:
                ERROR(str(e))

    def _halfHour(self,receivers):
        hh = self._getHalfHour()
        if hh == self._lastHalfHour: return receivers
        try:
            receivers = self._day(receivers,hh)
            ret = []
            for r in receivers:
                try:
                    if not r.halfHour(): ret.append(r)
                except Exception as e:
                    ret.append(r)
                    ERROR(str(e))
            return ret
        finally:
            self._lastHalfHour = hh

    def _minute(self,receivers):
        mm = self._getMinute()
        if mm == self._lastMinute: return receivers
        try:
            ret = []
            for r in receivers:
                try:
                    if not r.minute(): ret.append(r)
                except Exception as e:
                    ret.append(r)
                    ERROR(str(e))
            return ret
        finally:
            self._lastMinute = mm

    def _day(self,receivers,hh):
        if hh >= self._lastHalfHour: return receivers
        ret = []
        for r in receivers:
            try:
                if not r.day(): ret.append(r)
            except Exception as e:
                ret.append(r)
                ERROR(str(e))
        return ret

    def registerReceiver(self,receiver):
        DEBUG_LOG("reg rx: %s" % receiver)
        self._receivers.append(receiver)
        DEBUG_LOG("rx list: %s" % self._receivers)

    def cancelReceiver(self,receiver):
        if receiver in self._receivers:
            self._receivers.pop(self._receivers.index(receiver))

DEBUG = getSetting('debug',False) or xbmc.getCondVisibility('System.GetBool(debug.showloginfo)')
if DEBUG: LOG('Debug logging enabled')
LOG('User-Agent: {0}'.format(USER_AGENT))

initTimeDisplay()