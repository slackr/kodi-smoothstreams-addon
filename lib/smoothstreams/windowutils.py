from __future__ import absolute_import, division, unicode_literals
import threading
import xbmcgui, xbmc
from . import player

class ActionHandler(object):
	def __init__(self,callback):
		self.callback = callback
		self.event = threading.Event()
		self.event.clear()
		self.timer = None
		self.delay = 0.001

	def onAction(self,action):
		if self.timer: self.timer.cancel()
		if self.event.isSet(): return
		self.timer = threading.Timer(self.delay,self.doAction,args=[action])
		self.timer.start()

	def doAction(self,action):
		self.event.set()
		try:
			self.callback(action)
		finally:
			self.event.clear()

	def clear(self):
		if self.timer: self.timer.cancel()
		return self.event.isSet()

class FakeActionHandler(object):
	def __init__(self,callback):
		self.callback = callback

	def onAction(self,action):
		self.callback(action)

	def clear(self):
		return False

class BaseWindow(xbmcgui.WindowXML):
	def __init__(self,*args,**kwargs):
		self._closing = False
		self._winID = ''

	def onInit(self):
		self._winID = xbmcgui.getCurrentWindowId()

	def setProperty(self,key,value):
		if self._closing: return
		xbmcgui.Window(self._winID).setProperty(key,value)
		xbmcgui.WindowXMLDialog.setProperty(self,key,value)

	def doClose(self):
		self._closing = True
		self.close()

	def onClosed(self): pass

class BaseDialog(xbmcgui.WindowXMLDialog):
	def __init__(self,*args,**kwargs):
		self._closing = False
		self._winID = ''

	def onInit(self):
		self._winID = xbmcgui.getCurrentWindowDialogId()

	def setProperty(self,key,value):
		if self._closing: return
		xbmcgui.Window(self._winID).setProperty(key,value)
		xbmcgui.WindowXMLDialog.setProperty(self,key,value)

	def doClose(self):
		self._closing = True
		self.close()

	def onClosed(self): pass

class KodiChannelEntry(BaseDialog):
	def __init__(self,*args,**kwargs):
		self.viewManager = kwargs['viewManager']
		self.digits = kwargs['digit']
		self.digit2 = None
		self.set = False
		self.digitFileBase = 'numbers/{0}.png'
		BaseDialog.__init__(self,*args,**kwargs)

	def onInit(self):
		BaseDialog.onInit(self)
		self.setProperty('digit1',self.digitFileBase.format(self.digits))

	def onAction(self, action):
		try:
			if action == xbmcgui.ACTION_SELECT_ITEM:
				self.finish()
			else:
				self.handleDigit(action)
		finally:
			BaseDialog.onAction(self,action)

	def handleDigit(self, action):
		if  action.getId() >= xbmcgui.REMOTE_0 and action.getId() <= xbmcgui.REMOTE_9:
			if self.digit2:
				digit3 = str(action.getId() - 58)
				self.digits += digit3
				self.setProperty('digit3',self.digitFileBase.format(digit3))
				self.setProperty('number',self.digits)
				xbmc.sleep(100)
			else:
				self.digit2 = str(action.getId() - 58)
				self.digits += self.digit2
				self.setProperty('digit2',self.digitFileBase.format(self.digit2))

	def finish(self):
		self.digits = int(self.digits)
		self.set = True
		player.initPlay(str(self.digits))
		self.close()
