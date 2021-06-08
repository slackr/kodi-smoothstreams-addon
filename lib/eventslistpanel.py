from __future__ import absolute_import, division, unicode_literals

import xbmc, xbmcgui
import os
import datetime
# import threading
import URLDownloader
from .smoothstreams import authutils, schedule, timeutils, skinutils, chanutils, player
from .smoothstreams.windowutils import BaseDialog, BaseWindow, ActionHandler, FakeActionHandler, KodiChannelEntry
from . import util
from . import kodigui
# from . import smoothstreams
from . import settings
from .downloadregistry import DownloadRegistry


#==============================================================================
# KodiListDialog
#==============================================================================
class KodiListDialog(BaseWindow,util.CronReceiver):
	def __init__(self,*args,**kwargs):
		self.viewManager = kwargs['viewManager']
		if not settings.SCHEDULE:
			settings.SCHEDULE = schedule.Schedule()
		if not settings.EVENTS_CHANNELS:
			settings.EVENTS_CHANNELS = settings.SCHEDULE.epg(self.viewManager.startOfDay())
		self.categories = settings.SCHEDULE.categories()
		self.category = []
		self.started = False
		self.lastHalfHour = 0
		self.progressItems = []
		self.lastHalfHour = self.viewManager.getHalfHour()
		BaseWindow.__init__(self,*args,**kwargs)

	def onInit(self):
		BaseWindow.onInit(self)
		if self.started: return
		self.setWindowProperties()
		self.started = True
		self.categoryList = self.getControl(55)
		self.programsList = kodigui.ManagedControlList(self,50,11)
		self.fillCategories()
		self.setProperty('category','ALL')
		if not self.viewManager.search_key == '':
			self.setProperty('category','Search Results for: ' + str(self.viewManager.search_key))
		self.showList()
		self.setFocusId(200)
		settings.CRON.registerReceiver(self)

	def setWindowProperties(self):
		self.setProperty('description', 'true')
		self.setProperty('version','v{0}'.format(util.ADDON.getAddonInfo('version')))
		self.setProperty('epg_type', '{0}'.format(util.getSetting('guide_source','Sports')))
		# if util.getSetting('show_video_preview',True) and util.getSetting('disable_list_view_preview',True):
		# 	self.setProperty('hide_video_preview', '')
		# else:
		# 	self.setProperty('hide_video_preview', '1')

	def tick(self):
		self.updateProgressBars()

	def halfHour(self):
		self.updateProgramItems()
		return True

	def day(self):
		self.viewManager.reloadChannels()
		self.showPrograms()
		return True

	def updateEPG(self):
		util.LOG('updateEPG called')
		self.showPrograms()
		self.refresh()

	def updateProgressBars(self):
		timeInDay = self.viewManager.timeInDay()
		for item in self.progressItems:
			program = item.dataSource
			prog = ((timeInDay - program.epg.start)/float(program.epg.duration))*100
			prog = int(prog - (prog % 5))
			tex = 'progress_line/{0}.png'.format(prog)
			item.setProperty('playing',tex)

	def getProgramByID(self,pid):
		for channel in settings.EVENTS_CHANNELS:
			for program in channel.get('programs',{}):
				if pid == program.pid:
					return program

	def updateProgramItems(self):
		self.progressItems = []
		startOfDay = timeutils.startOfDayLocalTimestamp()
		timeInDay = self.viewManager.timeInDay()
		oldItems = []
		items = []

		selected = self.programsList.getSelectedItem()
		onCurrent = False
		for idx in self.programsList.getViewRange():
			if not self.programsList[idx].getProperty('old'):
				onCurrent = True
				break

		oldViewPosition = self.programsList.getViewPosition()

		for i in range(self.programsList.size()):
			item = self.programsList[i]
			pid = item.getProperty('pid')
			program = self.getProgramByID(pid)
			self.updateItemData(item,program)
			if item.getProperty('old'):
				oldItems.append(item)
			else:
				items.append(item)

		oldItems.sort(key=lambda x: int(x.getProperty('sort')))
		self.programsList.replaceItems(oldItems + items)

		if util.getSetting('auto_advance',True) and onCurrent:
			selected = self.programsList.getSelectedItem()
			if selected and selected.getProperty('old'):
				pos = selected.pos() + 1
				while self.programsList.positionIsValid(pos):
					item = self.programsList[pos]
					if not item.getProperty('old'):
						self.programsList.selectItem(item.pos())
						xbmc.sleep(100) #Allow Kodi to actually update the position
						viewPosition = self.programsList.getViewPosition()

						if viewPosition > oldViewPosition:
							diff = viewPosition - oldViewPosition
							self.programsList.shiftView(diff,True)

						break
					pos += 1
				else:
					self.programsList.selectItem(self.programsList.size()-1)

	def onAction(self,action):
		try:
			if action == xbmcgui.ACTION_CONTEXT_MENU:
				self.viewManager.doContextMenu(show_download=self.getFocusId() == 50)
			elif action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
				if self.viewManager.handlePreClose(): return
			elif action == xbmcgui.ACTION_RECORD:
				self.viewManager.record()

			if self.viewManager.checkChannelEntry(action):
				return
		except Exception as e:
			util.ERROR(str(e))
			BaseWindow.onAction(self,action)
			return
		BaseWindow.onAction(self,action)

	def onClick(self,controlID):
		if controlID == 55:
			self.categorySelected()
		elif controlID == 50:
			self.programSelected()
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

	def categorySelected(self):
		item = self.categoryList.getSelectedItem()
		name = item.getProperty('category')
		all = util.getSetting('show_all')
		if name == "ALL":
			for d in range(1,len(self.categories)):
				i = self.categoryList.getListItem(d)
				if item.getProperty('selected') == 'true':
					i.setProperty('selected','false')
					util.setSetting(i.getProperty('id'),'false')
				else:
					i.setProperty('selected','true')
					if i.getProperty('category') not in self.category:  self.category.append(i.getProperty('category'))
					util.setSetting(i.getProperty('id'),'true')

			if item.getProperty('selected') == 'false':
				item.setProperty('selected','true')
				util.setSetting(item.getProperty('id'),'true')
				if not 'ALL' in self.category:  self.category.append('ALL')
			else:
				item.setProperty('selected','false')
				util.setSetting(item.getProperty('id'),'false')
				self.category = []
			self.showPrograms()
			return

		if all == 'true':
			for d in range(1,len(self.categories)):
				i = self.categoryList.getListItem(d)
				# if item.getProperty('selected') == 'true':
				i.setProperty('selected','false')
				util.setSetting(i.getProperty('id'),'false')
				# else:
				# 	i.setProperty('selected','true')
				# 	if i.getProperty('category') not in self.category:  self.category.append(i.getProperty('category'))
				# 	util.setSetting(i.getProperty('id'),'true')
			i = self.categoryList.getListItem(0)
			i.setProperty('selected','false')
			util.setSetting('show_all','false')
			self.category = []
			# if item.getProperty('selected') == 'false':
			item.setProperty('selected','true')
			util.setSetting(item.getProperty('id'),'true')
			if name in self.catsub:
				for d in range(1,len(self.categories)):
					i = self.categoryList.getListItem(d)
					cat = i.getProperty('category')
					if cat in self.catsub[name]:
						# if item.getProperty('selected') == 'true':
						i.setProperty('selected','true')
						util.setSetting(i.getProperty('id'),'true')
						self.category.append(cat)
			self.category.append(name)
			self.showPrograms()
			return

		stat = item.getProperty('selected')

		if str(stat) == 'false' or stat == '':
			item.setProperty('selected','true')
			util.setSetting(item.getProperty('id'),'true')
			if name in self.catsub:
				for d in range(1,len(self.categories)):
					i = self.categoryList.getListItem(d)
					cat = i.getProperty('category')
					if cat in self.catsub[name]:
						# if item.getProperty('selected') == 'true':
						i.setProperty('selected','true')
						util.setSetting(i.getProperty('id'),'true')
						self.category.append(cat)
		else:
			item.setProperty('selected','false')
			util.setSetting(item.getProperty('id'),'false')
			if name in self.catsub:
				for d in range(1,len(self.categories)):
					i = self.categoryList.getListItem(d)
					cat = i.getProperty('category')
					if cat in self.catsub[name]:
						# if item.getProperty('selected') == 'true':
						i.setProperty('selected','false')
						util.setSetting(i.getProperty('id'),'false')
						self.category.remove(cat)

		for d in range(0,len(self.categories)):
			i = self.categoryList.getListItem(d)
			cat = i.getProperty('category')
			if i.getProperty('selected') == 'true':
				if cat not in self.category: self.category.append(cat)
			else:
				if cat in self.category: self.category.remove(cat)

		if not self.categoryCount == len(self.category):
			i = self.categoryList.getListItem(0)
			i.setProperty('selected','false')
			util.setSetting(i.getProperty('id'),'false')
			if "ALL" in self.category: self.category.remove("ALL")

		if self.categoryCount - 1 == len(self.category):
			i = self.categoryList.getListItem(0)
			i.setProperty('selected','true')
			util.setSetting(i.getProperty('id'),'true')
			if "ALL" not in self.category: self.category.append("ALL")

		self.showPrograms()

	def programSelected(self):
		item = self.programsList.getSelectedItem()
		if not item: return
		player.initPlay(item.dataSource.channel_number,viewManager=self.viewManager)

	def showPrograms(self):
		self.showList()
		return

	def getGifPath(self,c):
		hexColor = schedule.SPORTS_TABLE.get(c.lower(),{}).get('color','808080')
		return util.makeColorGif(hexColor,os.path.join(util.COLOR_GIF_PATH,'{0}.gif'.format(hexColor)))

	def fillCategories(self):
		items = []
		'''item = xbmcgui.ListItem('All')
		item.setProperty('color', util.makeColorGif('FFFFFFFF',os.path.join(util.COLOR_GIF_PATH,'{0}.gif'.format('FFFFFFFF'))))
		item.setProperty('category','ALL')
		self.category.append("ALL")
		item.setProperty('selected','true')
		items.append(item)'''
		self.categories = [
			{"id":"show_all","name":"ALL"},
			{"id":"show_30401","name":"American Football"},
			{"id":"show_30402","name":"- NCAAF"},
			{"id":"show_30403","name":"- NFL"},
			{"id":"show_30404","name":"Baseball"},
			{"id":"show_30405","name":"Basketball"},
			{"id":"show_30406","name":"- NBA"},
			{"id":"show_30407","name":"- NCAAB"},
			{"id":"show_30408","name":"Boxing + MMA"},
			{"id":"show_30409","name":"Cricket"},
			{"id":"show_30410","name":"Golf"},
			{"id":"show_30411","name":"Ice Hockey"},
			{"id":"show_30412","name":"Motor Sports"},
			{"id":"show_30413","name":"- Formula 1"},
			{"id":"show_30414","name":"- Nascar"},
			{"id":"show_30415","name":"Olympics"},
			{"id":"show_30416","name":"Other Sports"},
			{"id":"show_30417","name":"Rugby"},
			{"id":"show_30418","name":"Tennis"},
			{"id":"show_30419","name":"TV Shows"},
			{"id":"show_30420","name":"World Football"},
			{"id":"show_30421","name":"Wrestling"}
		]
		self.catsub = { 'American Football':('- NCAAF','- NFL'),
					'Basketball':('- NBA','- NCAAB'),
					'Motor Sports':('- Formula 1','- Nascar'),
					'TV Shows':('- General TV'),
					}

		for c in self.categories:
			item = xbmcgui.ListItem(c['name'])
			item.setProperty('category',c['name'])
			stat = util.getSetting(c['id'],bool)
			if stat == 'true':
				self.category.append(c['name'])
			item.setProperty('selected',stat)
			item.setProperty('id',c['id'])
			item.setProperty('color',self.getGifPath(c['name']))
			items.append(item)
		self.categoryList.reset()
		self.categoryList.addItems(items)
		self.categoryCount = len(items)

	def refresh(self):
		pos = self.programsList.getSelectedPosition()
		oldSize = self.programsList.size()
		if not self.showList(): return
		size = self.programsList.size()
		if size != oldSize: return
		if size and pos < size: self.programsList.selectItem(pos)

	def updateItemData(self,item,program):
		startOfDay = timeutils.startOfDayLocalTimestamp()
		timeInDay = self.viewManager.timeInDay()
		start = program.epg.start
		stop = program.epg.stop

		localTZ = timeutils.LOCAL_TIMEZONE
		nowDT = timeutils.nowUTC()

		dt = datetime.datetime.fromtimestamp(program.start, tz=localTZ)
		if dt.day == nowDT.day:
			timeDisp = datetime.datetime.strftime(dt, util.TIME_DISPLAY)
		else:
			timeDisp = datetime.datetime.strftime(dt, '%a {0}'.format(util.TIME_DISPLAY))

		if util.getSetting('12_hour_times') == 'true':
			if len(str(timeDisp).split(' ')) > 2:
				t = str(timeDisp).split(' ', 1)[1]
				temp = dt.strftime('%b %d')
				disp_time = str(temp) + ', ' + str(t)
			else:
				t = str(timeDisp)
				disp_time = 'Today, ' + t
		else:
			if len(str(timeDisp).split(' ')) > 1:
				t = str(timeDisp).split(' ', 1)[1]
				temp = dt.strftime('%b %d')
				disp_time = str(temp) + ', ' + str(t)
			else:
				t = str(timeDisp)
				disp_time = 'Today, ' + t
		item.setLabel2(disp_time)
		sort = (((start * 1440) + stop ) * 100) + program.channel
		item.setProperty('old','')
		if stop <= timeInDay:
			item.setProperty('old','old')
			item.setProperty('playing','')
		elif start <= timeInDay:
			prog = ((timeInDay - start)/float(program.epg.duration))*100
			prog = int(prog - (prog % 5))
			tex = 'progress_line/{0}.png'.format(prog)
			item.setProperty('playing',tex)
			self.progressItems.append(item)
		item.setProperty('sort',str(sort))

	def showList(self):
		categories = self.category
		if self.viewManager.search_key == '':
			self.setProperty('category','ALL')
			if not self.categoryCount == len(categories):
				self.setProperty('category','FILTERED')
		oldItems = []
		items = []
		channelsNow = []
		self.progressItems = []
		startOfDay = timeutils.startOfDayLocalTimestamp()
		timeInDay = self.viewManager.timeInDay()
		for channel in settings.EVENTS_CHANNELS:
			if not 'programs' in channel: continue
			for program in channel['programs']:
				if not self.viewManager.search_key == '' and not self.viewManager.search_key.lower() in program.title.lower():
					continue
				start = program.epg.start
				stop = program.epg.stop
				old = False
				suitableCat = False

				if categories is None:
					suitableCat = True
				elif not program.subcategory:
					if program.category in categories:
						suitableCat = True
				elif program.category in categories and program.subcategory in categories:
					suitableCat = True

				if suitableCat == True and (start >= self.viewManager.lowerLimit or stop > self.viewManager.lowerLimit) and start < self.viewManager.upperLimit:
					localTZ = timeutils.LOCAL_TIMEZONE
					nowDT = timeutils.nowUTC()

					dt = datetime.datetime.fromtimestamp(program.start, tz=localTZ)
					if dt.day == nowDT.day:
						timeDisp = datetime.datetime.strftime(dt, util.TIME_DISPLAY)
					else:
						timeDisp = datetime.datetime.strftime(dt, '%a {0}'.format(util.TIME_DISPLAY))

					if util.getSetting('12_hour_times') == 'true':
						if len(str(timeDisp).split(' ')) > 2:
							t = str(timeDisp).split(' ',1)[1]
							temp = dt.strftime('%b %d')
							disp_time = str(temp) + ', ' + str(t)
						else:
							t = str(timeDisp)
							disp_time = 'Today, ' + t
					else:
						if len(str(timeDisp).split(' ')) > 1:
							t = str(timeDisp).split(' ',1)[1]
							temp = dt.strftime('%b %d')
							disp_time = str(temp) + ', ' + str(t)
						else:
							t = str(timeDisp)
							disp_time = 'Today, ' + t
					item = kodigui.ManagedListItem(program.title,disp_time,iconImage=channel['logo'],data_source=program)
					sort = (((start * 1440) + stop ) * 100) + program.channel
					if stop <= timeInDay:
						item.setProperty('old','old')
						old = True
					elif start <= timeInDay:
						prog = ((timeInDay - start)/float(program.epg.duration))*100
						prog = int(prog - (prog % 5))
						tex = 'progress_line/{0}.png'.format(prog)

						item.setProperty('playing',tex)
						self.progressItems.append(item)
					item.setProperty('sort',str(sort))
					item.setProperty('channel',str(channel['ID']))
					item.setProperty('duration',program.displayDuration)
					item.setProperty('quality',program.epg.quality)
					item.setProperty('color',program.epg.colorGIF)
					item.setProperty('pid',program.pid)
					item.setProperty('flag','flags/{0}.png'.format(program.language))
					# item.setProperty('Channel', program.channelName)
					item.setProperty('ChannelNumberLabel', channel['ID'])
					item.setProperty('Title', program.title)
					item.setProperty('Plot', program.description)
					item.setProperty('Duration', str(program.duration))
					infolabels = {
						# 'Channel': program.channel,
						# 'ChannelName': program.channelName,
						# 'ChannelNumberLabel': int(channel['ID']),
						'Mediatype': 'tvshow',
						'Title': program.title,
						'Genre': program.category,
						'Plot': program.description or program.title,
						'Plotoutline': program.description or program.title,
						'originaltitle': None,
						'tvshowtitle': None,
						'episode': None,
						'season': None,
						'year': None,
						# 'EpgEventTitle': program.title,
						'Duration': program.duration,  # todo not working yet
						# 'StartTime': program.start,
						# 'EndTime': program.stop,
						'Studio': '{0} ({1})'.format(program.network, program.channelName)
					}
					item.setInfo('video', infolabels)
					if old:
						oldItems.append(item)
					else:
						items.append(item)
		items.sort(key=lambda x: int(x.getProperty('sort')))
		oldItems.sort(key=lambda x: int(x.getProperty('sort')))
		items = oldItems + items
		self.programsList.reset()
		if not items: return False
		self.programsList.addItems(items)

		self.programsList.selectItem(len(items)-1)

		for i in range(len(items)):
			if not items[i].getProperty('old'):
				self.programsList.selectItem(i)
				break
		self.viewManager.search_key = ''
		return True


	def getSelectedChannel(self):
		item = self.programsList.getSelectedItem()
		if not item: return None
		return item.dataSource.channelParent

	def getSelectedProgram(self):
		item = self.programsList.getSelectedItem()
		if not item: return None
		return item.dataSource

	def initSettings(self): pass

	def getSettingsState(self):
		state = [   util.getSetting('12_hour_times',False),
					util.getSetting('gmt_offset',0),
					util.getSetting('schedule_plus_limiter',3),
					util.getSetting('schedule_minus_limiter',2),
					util.getSetting('show_all',True)
		]

		for i in range(30401,30422):
			state.append(util.getSetting('show_{0}'.format(i),True))
		return state

	def updateSettings(self,state):
		self.fillCategories()
		self.setWindowProperties()
		if state != self.getSettingsState():
			self.refresh()

	def onClosed(self):
		settings.CRON.cancelReceiver(self)



