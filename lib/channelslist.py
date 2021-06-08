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


# ==============================================================================
# KodiListDialog
# ==============================================================================
class KodiChannelsListDialog(BaseWindow, util.CronReceiver):
	def __init__(self, *args, **kwargs):
		self.viewManager = kwargs['viewManager']
		if not settings.SCHEDULE:
			settings.SCHEDULE = schedule.Schedule(False)
		if not settings.CHANNELS:
			settings.SCHEDULE.epg(self.viewManager.startOfDay())

		self.categories = settings.SCHEDULE.categories()
		self.category = []
		self.description = self.viewManager.description
		self.started = False
		self.lastHalfHour = 0
		self.progressItems = []
		self.progressItems2 = []
		self.lastHalfHour = self.viewManager.getHalfHour()
		BaseWindow.__init__(self, *args, **kwargs)

	def onInit(self):
		BaseWindow.onInit(self)
		# disable check to fix return bug, will cause an incvrease in loading time in a small number of cases
		if self.started: return
		self.setWindowProperties()
		self.started = True
		settings.MANAGEDCHANNELSLIST = kodigui.ManagedControlList(self, 50, 11)
		self.programsList = kodigui.ManagedControlList(self, 55, 11)
		self.showList()
		self.showList2()
		self.setFocusId(50)
		self.selChan = 1
		settings.CRON.registerReceiver(self)

	def setWindowProperties(self):
		if self.description:
			self.setProperty('description', 'true')
		else:
			self.setProperty('description', '')
		self.setProperty('version', 'v{0}'.format(util.ADDON.getAddonInfo('version')))
		self.setProperty('epg_type', '{0}'.format(util.getSetting('guide_source', 'Sports')))
		self.setProperty('hide_video_preview', '1')

	def tick(self):
		# self.showList(False)
		self.updateProgressBars()

	def halfHour(self):
		self.showList(False)
		self.showList2(False)
		return True

	def day(self):
		self.viewManager.reloadChannels()
		self.showPrograms()
		return True

	def updateProgressBars(self):
		chanutils.createChannelsList()
		timeInDay = self.viewManager.timeInDay()
		for item in self.progressItems:
			program = item.dataSource
			prog = ((timeInDay - program.epg.start) / float(program.epg.duration)) * 100
			prog = int(prog - (prog % 5))
			tex = 'progress_line/{0}.png'.format(prog)
			item.setProperty('playing', tex)

		for item in self.progressItems2:
			program = item.dataSource
			prog = ((timeInDay - program.epg.start) / float(program.epg.duration)) * 100
			prog = int(prog - (prog % 5))
			tex = 'progress_line/{0}.png'.format(prog)
			item.setProperty('playing', tex)

	def updateEPG(self):
		util.LOG('updateEPG called')
		self.showPrograms()
		self.refresh()

	def updateProgramItems(self):
		self.progressItems = []
		startOfDay = timeutils.startOfDayLocalTimestamp()
		timeInDay = self.viewManager.timeInDay()
		oldItems = []
		items = []

		selected = settings.MANAGEDCHANNELSLIST.getSelectedItem()
		onCurrent = False
		for idx in settings.MANAGEDCHANNELSLIST.getViewRange():
			if not settings.MANAGEDCHANNELSLIST[idx].getProperty('old'):
				onCurrent = True
				break

		oldViewPosition = settings.MANAGEDCHANNELSLIST.getViewPosition()

		for i in range(settings.MANAGEDCHANNELSLIST.size()):
			item = settings.MANAGEDCHANNELSLIST[i]
			pid = item.getProperty('pid')
			program = self.viewManager.getProgramByID(pid)
			self.updateItemData(item, program, startOfDay, timeInDay)
			if item.getProperty('old'):
				oldItems.append(item)
			else:
				items.append(item)

		oldItems.sort(key=lambda x: int(x.getProperty('sort')))
		settings.MANAGEDCHANNELSLIST.replaceItems(oldItems + items)

		if util.getSetting('auto_advance', True) and onCurrent:
			selected = settings.MANAGEDCHANNELSLIST.getSelectedItem()
			if selected and selected.getProperty('old'):
				pos = selected.pos() + 1
				while settings.MANAGEDCHANNELSLIST.positionIsValid(pos):
					item = settings.MANAGEDCHANNELSLIST[pos]
					if not item.getProperty('old'):
						settings.MANAGEDCHANNELSLIST.selectItem(item.pos())
						xbmc.sleep(100)  # Allow Kodi to actually update the position
						viewPosition = settings.MANAGEDCHANNELSLIST.getViewPosition()

						if viewPosition > oldViewPosition:
							diff = viewPosition - oldViewPosition
							settings.MANAGEDCHANNELSLIST.shiftView(diff, True)

						break
					pos += 1
				else:
					settings.MANAGEDCHANNELSLIST.selectItem(settings.MANAGEDCHANNELSLIST.size() - 1)

	def updateProgramItems2(self):
		self.progressItems2 = []
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
			program = self.viewManager.getProgramByID(pid)
			self.updateItemData2(item, program, startOfDay, timeInDay)
			if item.getProperty('old'):
				oldItems.append(item)
			else:
				items.append(item)

		oldItems.sort(key=lambda x: int(x.getProperty('sort')))
		self.programsList.replaceItems(oldItems + items)

		if util.getSetting('auto_advance', True) and onCurrent:
			selected = self.programsList.getSelectedItem()
			if selected and selected.getProperty('old'):
				pos = selected.pos() + 1
				while self.programsList.positionIsValid(pos):
					item = self.programsList[pos]
					if not item.getProperty('old'):
						self.programsList.selectItem(item.pos())
						xbmc.sleep(100)  # Allow Kodi to actually update the position
						viewPosition = self.programsList.getViewPosition()

						if viewPosition > oldViewPosition:
							diff = viewPosition - oldViewPosition
							self.programsList.shiftView(diff, True)

						break
					pos += 1
				else:
					self.programsList.selectItem(self.programsList.size() - 1)

	def onAction(self, action):
		try:
			controlID = self.getFocusId()
			if action == xbmcgui.ACTION_CONTEXT_MENU:
				self.viewManager.doContextMenu(show_download=self.getFocusId() == 50)
			elif action == xbmcgui.ACTION_STOP:
				if self.viewManager.handlePreClose(): return
			elif action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
				if self.viewManager.handlePreClose(): return
			elif action == xbmcgui.ACTION_RECORD:
				self.viewManager.record()
			if controlID == 50 and (action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_DOWN):
				self.showList2(ch=str(self.getSelectedChannel()['ID']))
			elif controlID == 50 and (action == xbmcgui.ACTION_PAGE_UP or action == xbmcgui.ACTION_PAGE_DOWN):
				self.showList2(ch=str(self.getSelectedChannel()['ID']))
			elif controlID == 50 and (action == xbmcgui.ACTION_MOUSE_MOVE):
				try:
					id = int(self.getSelectedChannel()['ID'])
					if id != self.selChan:
						self.selChan = id
						self.showList2(ch=str(id))
				except:
					a = 1

			elif action == xbmcgui.ACTION_MOVE_LEFT and controlID == 60:
				self.setFocusId(50)

			elif action == xbmcgui.ACTION_MOVE_RIGHT and controlID == 9000:
				self.setFocusId(50)

			elif action == xbmcgui.ACTION_MOVE_RIGHT and controlID == 60 and self.description == False:
				self.setFocusId(55)

			if self.viewManager.checkChannelEntry(action, '1080i'):
				return
		except Exception as e:
			util.ERROR(str(e))
			BaseWindow.onAction(self, action)
			return
		BaseWindow.onAction(self, action)

	def onClick(self, controlID):
		if controlID == 50:
			self.programSelected()
		if controlID == 55:
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
		elif controlID == 108:
			if self.description:
				self.setProperty('description', '')
				self.description = False
			else:
				self.setProperty('description', 'true')
				self.description = True

	def programSelected(self):

		# item = settings.MANAGEDCHANNELSLIST.getSelectedItem()

		# if not item: return
		# self.viewManager.player.play(item.dataSource)

		mli = settings.MANAGEDCHANNELSLIST.getSelectedItem()
		if not mli:
			return
		# self.updatePlayingItem()
		ch = mli.dataSource.channel_number
		player.initPlay(ch,viewManager=self.viewManager)

	def showPrograms(self):
		self.showList()
		self.showList2()
		return

	def getGifPath(self, c):
		hexColor = schedule.SPORTS_TABLE.get(c.lower(), {}).get('color', '808080')
		return util.makeColorGif(hexColor, os.path.join(util.COLOR_GIF_PATH, '{0}.gif'.format(hexColor)))

	def refresh(self):
		pos = settings.MANAGEDCHANNELSLIST.getSelectedPosition()
		oldSize = settings.MANAGEDCHANNELSLIST.size()
		if not self.showList(False): return
		size = settings.MANAGEDCHANNELSLIST.size()
		if size != oldSize: return
		if size and pos < size: settings.MANAGEDCHANNELSLIST.selectItem(pos)

		pos = self.programsList.getSelectedPosition()
		oldSize = self.programsList.size()
		if not self.showList2(False): return
		size = self.programsList.size()
		if size != oldSize: return
		if size and pos < size: self.programsList.selectItem(pos)

	def updateItemData(self, item, program, startOfDay, timeInDay):
		start = program.epg.start
		stop = program.epg.stop
		dt = datetime.datetime.fromtimestamp(startOfDay + (start * 60), tz=timeutils.LOCAL_TIMEZONE)
		if start >= 0 and start < 1440:
			timeDisp = datetime.datetime.strftime(dt, util.TIME_DISPLAY)
		else:
			timeDisp = datetime.datetime.strftime(dt, '%a {0}'.format(util.TIME_DISPLAY))
		item.setLabel2(timeDisp)
		sort = (((start * 1440) + stop) * 100) + program.channel
		item.setProperty('old', '')
		if stop <= timeInDay:
			item.setProperty('old', 'old')
			item.setProperty('playing', '')
		elif start <= timeInDay:
			prog = ((timeInDay - start) / float(program.epg.duration)) * 100
			prog = int(prog - (prog % 5))
			tex = 'progress_circle/{0}.png'.format(prog)
			item.setProperty('playing', tex)
			self.progressItems.append(item)
		item.setProperty('sort', str(sort))

	def updateItemData2(self, item, program, startOfDay, timeInDay):
		start = program.epg.start
		stop = program.epg.stop
		dt = datetime.datetime.fromtimestamp(startOfDay + (start * 60), tz=timeutils.LOCAL_TIMEZONE)
		if start >= 0 and start < 1440:
			timeDisp = datetime.datetime.strftime(dt, util.TIME_DISPLAY)
		else:
			timeDisp = datetime.datetime.strftime(dt, '%a {0}'.format(util.TIME_DISPLAY))
		item.setLabel2(timeDisp)
		sort = (((start * 1440) + stop) * 100) + program.channel
		item.setProperty('old', '')
		if stop <= timeInDay:
			item.setProperty('old', 'old')
			item.setProperty('playing', '')
		elif start <= timeInDay:
			prog = ((timeInDay - start) / float(program.epg.duration)) * 100
			prog = int(prog - (prog % 5))
			tex = 'progress_circle/{0}.png'.format(prog)
			item.setProperty('playing', tex)
			self.progressItems2.append(item)
		item.setProperty('sort', str(sort))

	def showList(self, resetPosition=True):
		return chanutils.createManagedChannelsList(resetPosition)

	def showList2(self, resetPosition=True, ch='1'):
		categories = self.category
		if self.viewManager.search_key == '':
			self.setProperty('category', 'ALL')

		oldItems = []
		items = []
		channelsNow = {}
		self.progressItems2 = []
		timeInDay = self.viewManager.timeInDay()
		startOfDay = timeutils.startOfDayLocalTimestamp()

		for channel in settings.CHANNELS:
			if channel['ID'] != ch: continue
			fakeProgram = channel
			elem = {
				'channel': str(channel['ID']),
				'name': str(channel['display-name']),
				'time': startOfDay,
				'runtime': 3600 * 48,
				'version': '',
				'channelParent': channel,
				'_ssType': 'PROGRAM'
			}
			program = schedule.SSProgram('1', elem, 'No Category', startOfDay, categories, str(channel['ID']))

			fakeItem = kodigui.ManagedListItem(channel['display-name'], '', iconImage=channel['logo'],
			                                   data_source=channel)
			color = schedule.SPORTS_TABLE.get('no category', {}).get('color', '808080')
			colorGIF = util.makeColorGif(color,
			                             os.path.join(util.COLOR_GIF_PATH, '{0}.gif'.format(color)))

			fakeItem.setProperty('flag', '')
			fakeItem.setProperty('channel', str(channel['ID']))

			channelsNow[str(channel['ID'])] = []

			if not 'programs' in channel: continue
			channel['programs'].sort(key=lambda x: int(x.start))
			channelListings = False
			for program in channel['programs']:
				indx = channel['programs'].index(program)
				try:
					p2 = channel['programs'][indx + 1]
				except:
					p2 = False
				if not self.viewManager.search_key == '' and not self.viewManager.search_key.lower() in program.title.lower():
					continue
				start = program.epg.start
				stop = program.epg.stop
				old = False
				if 1 == 1:
					item = kodigui.ManagedListItem(channel['display-name'], program.title, iconImage=channel['logo'],
					                               data_source=program)

					localTZ = timeutils.LOCAL_TIMEZONE
					nowDT = timeutils.nowUTC()

					sDT = datetime.datetime.fromtimestamp(program.start, tz=localTZ)
					eDT = datetime.datetime.fromtimestamp(program.stop, tz=localTZ)
					if sDT.day == nowDT.day:
						startDisp = datetime.datetime.strftime(sDT, util.TIME_DISPLAY)
					else:
						startDisp = datetime.datetime.strftime(sDT, '%a {0}'.format(util.TIME_DISPLAY))
					if eDT.day == nowDT.day:
						endDisp = datetime.datetime.strftime(eDT, util.TIME_DISPLAY)
					else:
						endDisp = datetime.datetime.strftime(eDT, '%a {0}'.format(util.TIME_DISPLAY))
					item.setProperty('Channel', program.channelName)
					item.setProperty('ChannelNumberLabel', channel['ID'])
					item.setProperty('Title', program.title)
					item.setProperty('Plot', program.description)
					item.setProperty('Duration', str(program.duration))
					item.setProperty('StartTime', str(startDisp))
					item.setProperty('EndTime', str(endDisp))
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
					if p2:
						nDT = datetime.datetime.fromtimestamp(p2.start, tz=localTZ)
						if nDT.day == nowDT.day:
							startDisp = datetime.datetime.strftime(nDT, util.TIME_DISPLAY)
						else:
							startDisp = datetime.datetime.strftime(nDT, '%a {0}'.format(util.TIME_DISPLAY))
						item.setProperty('NextTitle', p2.title)
						item.setProperty('NextStartTime', str(startDisp))
					sort = (((start * 1440) + stop) * 100) + program.channel
					if stop <= timeInDay:
						item.setProperty('old', 'old')
						old = True
					elif start <= timeInDay:
						prog = ((timeInDay - start) / float(program.epg.duration)) * 100
						# todo kodi v18 fails on progress, could be a kodi issue though
						item.setProperty('Progress', str(prog))
						item.setProperty('EpgEventProgress', str(prog))
						prog = int(prog - (prog % 5))
						tex = 'progress_circle/{0}.png'.format(prog)
						item.setProperty('playing', tex)
						self.progressItems2.append(item)
					item.setProperty('channel', str(channel['ID']))
					item.setProperty('duration', program.displayDuration)
					item.setProperty('color', program.epg.colorGIF)
					item.setProperty('pid', program.pid)
					item.setProperty('flag', 'flags/{0}.png'.format(program.language))
					if not old: channelsNow[str(channel['ID'])].append(item)
			if len(channelsNow[str(channel['ID'])]) == 0:
				channelsNow[str(channel['ID'])].append(fakeItem)
		temp = []

		for i in channelsNow[ch]:
			temp.append(i)
		channelsNow = temp
		# channelsNow.sort(key=lambda x: int(x.getProperty('StartTime')))

		items = oldItems + items
		exisitngPosition = self.programsList.getSelectedPosition()
		self.programsList.reset()
		if not channelsNow: return False
		self.programsList.addItems(channelsNow)

		self.programsList.selectItem(len(channelsNow) - 1)
		if resetPosition:
			for i in range(len(channelsNow)):
				if not channelsNow[i].getProperty('old'):
					self.programsList.selectItem(i)
					break
		else:
			self.programsList.selectItem(exisitngPosition)
		return True

	def getSelectedChannel(self):
		item = settings.MANAGEDCHANNELSLIST.getSelectedItem()
		if not item: return None
		if 'SSChannel' in str(type(item.dataSource)): return item.dataSource
		return item.dataSource.channelParent

	def getSelectedProgram(self):

		item = settings.MANAGEDCHANNELSLIST.getSelectedItem()
		if not item: return None
		return item.dataSource

	def initSettings(self):
		pass

	def getSettingsState(self):
		state = [util.getSetting('12_hour_times', False),
		         util.getSetting('gmt_offset', 0),
		         util.getSetting('schedule_plus_limiter', 3),
		         util.getSetting('schedule_minus_limiter', 2),
		         util.getSetting('show_all', True)
		         ]

		for i in range(30401, 30422):
			state.append(util.getSetting('show_{0}'.format(i), True))
		return state

	def updateSettings(self, state):
		self.setWindowProperties()
		if state != self.getSettingsState():
			self.refresh()

	def onClosed(self):
		settings.CRON.cancelReceiver(self)

