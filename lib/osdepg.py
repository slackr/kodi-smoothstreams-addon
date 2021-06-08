from __future__ import absolute_import, division, unicode_literals

import xbmc, xbmcgui
# import os
import datetime
# import threading
import URLDownloader
from .smoothstreams import authutils, schedule, timeutils, skinutils, chanutils
from .smoothstreams.windowutils import BaseDialog, BaseWindow, ActionHandler, FakeActionHandler, KodiChannelEntry
from . import util
from . import kodigui
from . import smoothstreams
from . import settings
from .downloadregistry import DownloadRegistry

#==============================================================================
# TimeIndicator
#==============================================================================
class TimeIndicator(object):
	def __init__(self,epg):
		self.epg = epg
		self.indicatorControl = self.epg.getControl(102)
		self.xLimit = self.epg.epgRight
#        self.lastHalfHourRight = 190 + (180 * 6)
		self.showing = False
		self.update()

	def hide(self):
		#Hide it if out of range
		self.showing = False
		self.indicatorControl.setPosition(-20,50)

	def move(self,pos):
		self.showing = True
		self.indicatorControl.setPosition(pos,50)

	def update(self,from_timer=True):
		timeInDay = timeutils.timeInDayLocalSeconds()/60.0
		xPos = 190 + int(((timeInDay - self.epg.viewManager.displayOffset) * 6.0))

		if from_timer and self.showing and ((xPos >= self.xLimit and (xPos - self.xLimit < 12))): #Only advance if are just off the edge
			self.hide()
			return True

		if xPos < 181 or xPos > self.xLimit:
			self.hide()
			return False

#        if from_timer and xPos > self.lastHalfHourRight and self.showing:
#            self.move(xPos)
#            return True

		self.move(xPos)

#==============================================================================
# KodiEPGDialog
#==============================================================================
class KodiEPGDialog(kodigui.BaseDialog,util.CronReceiver):
	xmlFile = 'script-smoothstreams-v3-epg.xml'
	path = util.ADDON.getAddonInfo('path')
	theme = 'Main'
	res = '1080i'
	width = 1920
	height = 1080

	LI_AR16X9_THUMB_DIM = (178, 100)
	LI_SQUARE_THUMB_DIM = (100, 100)

	def __init__(self,*args,**kwargs):
		self.osdHandler = kwargs['osdHandler']
		self.viewManager = kwargs['viewManager']

		self.initSettings()
		self._started = False
		kodigui.BaseDialog.__init__(self,*args,**kwargs)

	@util.busyDialog
	def initSettings(self,flag=1):
		if not settings.SCHEDULE or not settings.CHANNELS:
			self.viewManager.reloadChannels()
		if flag:
			self.selectionTime = 0
			self.selectionPos = -1
			self.epg = None

		self.actionHandler = ActionHandler(self._onAction)

	def onInit(self):
		kodigui.BaseDialog.onInit(self)

		if self._started:
			self.epg.selectItem(int(settings.CURCHAN)-1)
			return
		self.setWindowProperties()
		self._started = True
		self.setupEPG()
		self.timeIndicator = TimeIndicator(self) #Must be created after setupEPG()
		self.setProperty('selection_time','0')
		self.initChannels()
		self.updateEPG()
		self.updateSelection(self.selectionTime)
		#self.showTweet()
		settings.CRON.registerReceiver(self)

	def setWindowProperties(self):
		self.setProperty('version','v{0}'.format(util.ADDON.getAddonInfo('version')))
		self.setProperty('local_time', timeutils.nowLocal().strftime('%H:%M'))
		self.setProperty('epg_type', '{0}'.format(util.getSetting('guide_source','sports')))

	def getSettingsState(self):
		return (    util.getSetting('12_hour_times',False),
					util.getSetting('gmt_offset',0),
					util.getSetting('schedule_plus_limiter',3),
					util.getSetting('schedule_minus_limiter',2)
		)

	def updateSettings(self,state):
		self.initSettings(0)
		self.setWindowProperties()
		if state != self.getSettingsState():
			self.viewManager.setEPGLimits()
			self.updateEPG()
			self.updateSelection(self.selectionTime)

	def setupEPG(self):
		if not self.epg: self.epg = self.getControl(101)
		self.epgLeft = self.epg.getX() + 190
		self.epgRight = min((self.epg.getX()  + self.epg.getWidth() - 1),1280)
		self.epgTop = self.epg.getY()
		self.epgBottom = min(self.epg.getY()  + self.epg.getHeight(),720)

	def initChannels(self):
		items = []
		for channel in settings.CHANNELS:
			item = xbmcgui.ListItem(channel['display-name'],str(channel['ID']))
			item.setArt({'icon':channel['logo'], 'thumb':channel['logo']})
			items.append(item)

		self.epg.reset()
		self.epg.addItems(items)
		self.setFocusId(101)

	def updateEPG(self):
		self.timeIndicator.update()
		gridRange = range(-30,210,15)
		epgStart = -30 + self.viewManager.displayOffset
		epgEnd = 210 + self.viewManager.displayOffset

		for idx in range(len(settings.CHANNELS)):
			item = self.epg.getListItem(idx)
			programs = settings.CHANNELS[idx].get('programs',[])
			shown = {}

			categories = self.viewManager.createCategoryFilter()
			for program in programs:
				start = program.epg.start
				stop = program.epg.stop
				duration = program.epg.duration
				end = start + duration
				old = False

				#Temp fix for :15/:45 start or end of any program

				'''if start % 10 != 0 or stop % 10 != 0:
					start += 15
				if duration % 10 != 0:
					duration += 15'''

				#Fix for programs not starting at either 0/15/30/45
				if start % 60 != 0 or start % 60 != 15 or start % 60 != 30 or start % 60 != 45:
					if start % 60 > 0 and start % 60 <= 7:
						start -= start % 60
					elif start % 60 > 7 and start % 60 < 15:
						start += 15 - (start % 60)
					elif start % 60 > 15 and start % 60 <= 22:
						start -= (start % 60) - 15
					elif start % 60 > 22 and start % 60 < 30:
						start += 30 - (start % 60)
					elif start % 60 > 30 and start % 60 <= 37:
						start -= (start % 60) - 30
					elif start % 60 > 37 and start % 60 < 45:
						start += 45 - (start % 60)
					elif start % 60 > 45 and start % 60 <= 52:
						start -= (start % 60) - 45
					elif start % 60 > 52 and start % 60 < 60:
						start += 60 - (start % 60)

				if (start >= self.viewManager.lowerLimit or stop > self.viewManager.lowerLimit) and start < self.viewManager.upperLimit:

					gridTime = int(start - self.viewManager.displayOffset)

					if start >= epgStart and start < epgEnd:
						shown[gridTime] = True
						item.setProperty('Program_{0}_Duration'.format(gridTime),str(int(duration)))
						item.setProperty('Program_{0}_Label'.format(gridTime),program.title)
					elif (end >= epgStart and end < epgEnd) or (start < epgStart and end > epgStart):
						duration -= (-30 - gridTime)
						if not duration: continue
						gridTime = -30
						shown[gridTime] = True
						item.setProperty('Program_{0}_Duration'.format(gridTime),str(int(duration)))
						item.setProperty('Program_{0}_Label'.format(gridTime),program.title)

					if gridTime in shown:
						item.setProperty('Program_{0}_Color'.format(gridTime),program.epg.colorGIF)
			#Clear properties that we didn't set
			for s in gridRange:
				if not s in shown:
					item.setProperty('Program_{0}_Duration'.format(s),'')
					item.setProperty('Program_{0}_Label'.format(s),'')
		self.updateEPGTimes(gridRange)

	def updateEPGTimes(self,gridRange):
		nowDT = timeutils.nowUTC()

		for s in gridRange:
			dt = datetime.datetime.fromtimestamp(self.viewManager.startOfDay() + ((self.viewManager.displayOffset + s) * 60))

			if dt.day != nowDT.day:
				timeDisp = datetime.datetime.strftime(dt,'%a {0}'.format(util.TIME_DISPLAY))
			else:
				timeDisp = datetime.datetime.strftime(dt,util.TIME_DISPLAY)

			if dt < nowDT and timeutils.timedelta_total_seconds(nowDT - dt) > 1800:
				timeDisp = ' [COLOR FF888888]{0}[/COLOR]'.format(timeDisp)

			self.setProperty('Time_{0}'.format(s),timeDisp)

	def tick(self):
		if self.timeIndicator.update(True) and util.getSetting('auto_advance',True):
			self.nextItem()
			self.updateSelection(self.selectionTime)

	def halfHour(self):
		self.viewManager.reloadChannels()
		self.updateSelection(self.selectionTime)

	def day(self):
		self.viewManager.reloadChannels()
		if util.getSetting('auto_advance',True) and self.timeIndicator.showing:
			self.viewManager.initDisplayOffset()
			# self.viewManager.displayOffset -= 150 #So time indicator is still on the last half hour
		self.updateEPG()
		self.updateSelection(self.selectionTime)
		return True

	def onClick(self, controlID):
		if controlID == 101:
			self.epgClicked()
		elif controlID == 110:
			self.prevItem()
		elif controlID == 111:
			self.nextItem()
		elif controlID == 107:
			self.viewManager.switch('CHANNELS')
		elif controlID == 106:
			self.viewManager.switch('EPG')
		elif controlID == 102:
			self.viewManager.viewRecordings()
		elif controlID == 103:
			self.viewManager.switch('CATS')
		elif controlID == 104:
			self.viewManager.switch('PANEL')
		elif controlID == 105:
			self.viewManager.showSettings()
		elif controlID == 108:
			# time left
			self.prevItem()
		elif controlID == 109:
			# time right
			self.nextItem()
		else:
			settings.CRON.cancelReceiver(self)
			self.doClose()

	def onAction(self,action):
		try:
			controlID = self.getFocusId()
			#print action.getId()
			if action == xbmcgui.ACTION_MOVE_RIGHT and controlID == 101:
				return self.actionHandler.onAction(action)
			elif action == xbmcgui.ACTION_MOVE_LEFT and controlID == 101:
				return self.actionHandler.onAction(action)

			if self.actionHandler.clear(): return

			if action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_DOWN:
				self.updateInfo()
			elif action == xbmcgui.ACTION_PAGE_UP or action == xbmcgui.ACTION_PAGE_DOWN:
				self.updateInfo()
			elif action == xbmcgui.ACTION_CONTEXT_MENU:
				self.viewManager.doContextMenu()
			elif action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
				settings.CRON.cancelReceiver(self)
				self.doClose()
			elif action == xbmcgui.ACTION_RECORD:
				self.viewManager.record()
			if self.viewManager.checkChannelEntry(action):
				return

			self.getMouseHover(action)
		except Exception as e:
			util.ERROR(str(e))
			BaseWindow.onAction(self,action)
			return
		BaseWindow.onAction(self,action)

	def _onAction(self,action):
		'''if action == xbmcgui.ACTION_MOVE_RIGHT:
			if not self.getSelectedProgram():
				self.moveRight()
				self.updateInfo()
			else:
				temp = self.getSelectedProgram()
				while self.getSelectedProgram():
					self.moveRight()
					if temp != self.getSelectedProgram():
						break
				self.updateInfo()

		elif action == xbmcgui.ACTION_MOVE_LEFT:
			if not self.getSelectedProgram():
				self.moveLeft()
				self.updateInfo()
			else:
				temp = self.getSelectedProgram()
				while self.getSelectedProgram():
					self.moveLeft()
					self.updateInfo()
					if temp != self.getSelectedProgram():
						break'''
		if action == xbmcgui.ACTION_MOVE_RIGHT:
			self.moveRight()
			#self.updateInfo()
		elif action == xbmcgui.ACTION_MOVE_LEFT:
			self.moveLeft()
			#self.updateInfo()

	def getMouseHover(self,action):
		x = action.getAmount1()/1.5
		y = action.getAmount2()/1.5
		delta = 158
		start = 215
		if y < self.epgTop or x < self.epgLeft or y > self.epgBottom or x > self.epgRight : return
		elif x < (start + 1*delta): sel = 0
		elif x < (start + 2*delta): sel = 30
		elif x < (start + 3*delta): sel = 60
		elif x < (start + 4*delta): sel = 90
		elif x < (start + 5*delta): sel = 120
		elif x < (start + 6*delta): sel = 150
		else: sel = 150
		pos = self.epg.getSelectedPosition()
		if sel == self.selectionTime and pos == self.selectionPos: return
		self.selectionTime = sel
		self.selectionPos = pos
		self.updateSelection(sel)

	def updateSelection(self,selection):
		#print('--- update selection routine ---')
		#print('selection requested:', str(selection))
		self.setProperty('selection_time',str(selection))
		offset = timeutils.TIMEZONE_OFFSET
		todayStr = datetime.datetime.strftime(datetime.datetime.fromtimestamp(self.viewManager.startOfDay() + ((self.viewManager.displayOffset + self.selectionTime) * 60)),'%a %d')
		self.setProperty('today',todayStr)
		self.updateInfo()

	def updateInfo(self):
		p = self.getSelectedProgram()
		if p:
			self.setProperty('program_title',p.title)
			self.setProperty('program_description',p.description)
			self.setProperty('program_times',p.epg.timeDisplay)
			self.setProperty('program_times1',p.epg.timeDisplay.split('(')[0])
			self.setProperty('program_duration',p.epg.timeDisplay.split('(')[1][0:-1])

			self.setProperty('program_quality',p.epg.quality)
			xbmcSelect, ver = self.getVersions(p)
			self.setProperty('program_versions','[CR]'.join(ver))
			self.setProperty('program_category',p.category)
			self.setProperty('program_flag','flags/{0}.png'.format(p.language))
		else:
			self.setProperty('program_title','')
			self.setProperty('program_description','')
			self.setProperty('program_times','')
			self.setProperty('program_times1','')
			self.setProperty('program_duration','')
			self.setProperty('program_quality','')
			self.setProperty('program_versions','')
			self.setProperty('program_category','')
			self.setProperty('program_flag','')

	def nextItem(self):
		self.selectionTime = 0
		self.viewManager.displayOffset+=150
		self.updateEPG()

	def prevItem(self):
		self.selectionTime = 150
		self.viewManager.displayOffset-=150
		self.updateEPG()

	def moveRight(self):
		self.selectionTime = 0
		self.viewManager.displayOffset+=30
		self.updateEPG()

	def moveLeft(self):
		self.selectionTime = 30
		self.viewManager.displayOffset-=30
		self.updateEPG()

	def getVersions(self, program):
		if util.getSetting('guide_source','sports').lower() == 'sports':
			data = settings.EVENTS_CHANNELS
		else:
			data = settings.CHANNELS
		channels = []
		flag = 0

		if program.parrentID == 'None' or not program.parrentID:
			for channel in data:
				if 'programs' in channel and isinstance(channel['programs'], list):
					for show in channel['programs']:
						if show.eventID == program.eventID and show.channel == program.channel and flag == 0:
							if show.start == program.start:
								flag = 1
								channels.append(show)

		elif program.parrentID == '0':
			for channel in data:
				if 'programs' in channel and isinstance(channel['programs'], list):
					for show in channel['programs']:
						if show.parrentID == program.eventID:
							channels.append(show)
						if show.eventID == program.eventID and flag == 0:
							if show.start == program.start:
								flag = 1
								channels.append(show)


		else:
			for channel in data:
				if 'programs' in channel and isinstance(channel['programs'], list):
					for show in channel['programs']:
						if show.parrentID == program.parrentID:
							channels.append(show)
						if show.eventID == program.parrentID and flag == 0:
							if show.start == program.start:
								flag = 1
								channels.append(show)
		schannel = channels

		d = util.xbmcDialogSelect()
		ver = []
		for v in schannel:
			ch = v.channel_number
			if len(ch) == 1: ch = '0' + str(ch)
			if v.quality:
				version = "%s ( %s / %s )" % (ch, v.quality or "", v.language.upper() or '')
			else:
				version = "%s ( %s )" % (ch, v.language.upper() or '')
			ver.append(version)
			d.addItem(ch, version)

		# Here d is xbmcSelect options and ver is versions in python list

		return d, ver

	def epgClicked(self):
		channel = self.getSelectedChannel()
		chanID = channel['ID']
		self.osdHandler.goToChannel(chanID)
		settings.CRON.cancelReceiver(self)
		self.doClose()

	def getSelectedChannel(self):
		idx = self.epg.getSelectedPosition()
		return settings.CHANNELS[idx]

	def getSelectedProgram1(self):
		idx = self.epg.getSelectedPosition()
		if not settings.CHANNELS: return None
		channel = settings.CHANNELS[idx]
		if not 'programs' in channel: return None
		for program in channel['programs']:
			gridTime = program.epg.start - self.viewManager.displayOffset
			if self.selectionTime >= gridTime and self.selectionTime < gridTime + program.epg.duration:
				return program,gridTime
		return None,None

	def getSelectedProgram(self):
		idx = self.epg.getSelectedPosition()
		if not settings.CHANNELS: return None
		channel = settings.CHANNELS[idx]
		if not 'programs' in channel: return None
		for program in channel['programs']:
			gridTime = program.epg.start - self.viewManager.displayOffset
			if self.selectionTime >= gridTime and self.selectionTime < gridTime + program.epg.duration:
				return program
		return None

	def onClosed(self):
		settings.CRON.cancelReceiver(self)
