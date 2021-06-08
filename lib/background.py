from __future__ import absolute_import, division, unicode_literals
from . import kodigui
from . import util, settings

util.setGlobalProperty('background.busy', '')
util.setGlobalProperty('background.shutdown', '')
util.setGlobalProperty('background.splash', '')
util.setGlobalProperty('splashtext', '')

class BackgroundWindow(kodigui.BaseWindow):
    xmlFile = 'script-smoothstreams-v3-background.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    def __init__(self, *args, **kwargs):
        kodigui.BaseWindow.__init__(self, *args, **kwargs)
        self.function = kwargs.get('function')

    def onFirstInit(self):

        self.function()
        self.doClose()


def setBusy(on=True):
    util.setGlobalProperty('background.busy', on and '1' or '')


def setSplash(on=True):
    util.setGlobalProperty('background.splash', on and '1' or '')


def setShutdown(on=True):
    util.setGlobalProperty('background.shutdown', on and '1' or '')

def setSplashText(text):
    util.setGlobalProperty('splashtext', text)