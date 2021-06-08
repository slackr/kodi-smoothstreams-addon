
from __future__ import absolute_import, division, unicode_literals
import xbmc, xbmcgui
import os
import datetime
# import threading
import URLDownloader
from .smoothstreams import authutils, schedule, timeutils, skinutils, chanutils, player, windowutils
# from . import smoothstreams
from . import settings, epg, util, kodigui, eventslistpanel, channelslist, eventslistpanel_720
from .downloadregistry import DownloadRegistry

DOWNLOADER = None

# API_LEVEL = 1
#
#
#
# def versionCheck():
# 	old = util.getSetting('API_LEVEL',0)
# 	if API_LEVEL == old: return False
# 	util.setSetting('API_LEVEL',API_LEVEL)
# 	if old == 0:
# 		util.LOG('FIRST RUN')
# 	return False

#==============================================================================
# ViewManager
#==============================================================================
class ViewManager(object):
	def __init__(self):
		self.valid = 1
		self.initialize()
		if self.valid == 1:
			util.openSettings()
		else:
			xbmcgui.Window(10000).setProperty('script.smoothstreams-v3.service.started', '')
			self.start()

	# @util.busyDialog
	def initialize(self):
		self.player = player.OSDHandler(viewManager=self)
		# self.updateChannels()
		#Check for valid credential
		#If user has entered wrong credential then, login will be failed
		# authutils.check_token()
		# vHash = settings.TOKEN['hash']
		# if not vHash: vHash = self.player.getHash()
		# if 'error' in settings.TOKEN:
		# 	xbmcgui.Dialog().ok("Validation",settings.TOKEN['error'])
		# 	self.valid = 1
		# 	settings.TOKEN = None
		# 	authutils.dump_token()
		# 	return

		# if util.getSetting('theme') == 'true':
		self.theme = 'modern'
		# else:
		# 	self.theme = 'classic'

		# self.player.testServers() #Test if auto server is enabled
		self.setutcOffsetMinutes()
		# self.createFav()
		util.DEBUG_LOG('Timezone: {0}'.format(timeutils.LOCAL_TIMEZONE))
		self.initDisplayOffset()
		self.initChannels()
		self._lastStartOfDay = self.startOfDay()
		self.window = None
		self.mode = None
		self.search_key = ''
		self.description = True
		self.loadView()

		if util.getSetting('mode') == 'Last':
			try:
				self.mode = util.getSetting('last_mode')
			except:
				pass
		elif util.getSetting('mode') == 'Events List':
			self.mode = 'CATS'
		elif util.getSetting('mode') == 'EPG':
			self.mode = 'EPG'
		elif util.getSetting('mode') == 'Channels List':
			self.mode = 'CHANNELS'
		elif util.getSetting('mode') == 'Events Panel':
			self.mode = 'PANEL'
		if not self.mode:
			self.mode = "CHANNELS"
		self.valid = 0

	def start(self):
		# if not settings.CRON:
		# 	with util.Cron(5) as settings.CRON:
		# 		self._start()
		# else:
		self._start()
	def _start(self):
		while self.mode:
			if self.mode == 'EPG':
				self.showEPG()
			elif self.mode == 'CATS':
				self.showCats()
			elif self.mode == 'CHANNELS':
				self.showChannels()
			else:
				self.showPanel()
		util.DEBUG_LOG('EXIT')

	def switch(self,mode):
		self.mode = mode
		if self.window: self.window.close()

	def timerCallback(self):
		if not self.window: return
		self.window.timerCallback()

	def reloadChannels(self,force=False):
		schedule.Download()
		self.updateChannels()

	def updateChannels(self):
		settings.SCHEDULE.epg(self.startOfDay())

		self.initChannels()

	def isNewDay(self):
		sod = self.startOfDay()
		if sod == self._lastStartOfDay: return False
		self._lastStartOfDay = sod
		return True

	def setEPGLimits(self):
		self.upperLimit = self.displayOffset + (24 * 60 * util.getSetting("schedule_plus_limiter",3))
		self.lowerLimit = self.displayOffset - (24 * 60 * util.getSetting("schedule_minus_limiter",2))

	def getChannel(self, number):
		if str(number).startswith('0'):
			number = str(number)[1]
		for c in settings.CHANNELS if util.getSetting('mode') == 'EPG' else settings.EVENTS_CHANNELS:
			if number == c.get('ID'):
				return c

	def changeCat(self):
		if util.getSetting('show_all',bool) == 'true':
			categories = ["show_30401","show_30404","show_30405","show_30408","show_30409","show_30410","show_30411","show_30412","show_30415","show_30416","show_30417","show_30418","show_30419","show_30420","show_30421"]
			for cat in categories:
				util.setSetting(cat,'true')

	def showEPG(self):
		util.setSetting('last_mode','EPG')
		self.saveView()
		self.window = epg.KodiEPGDialog('script-smoothstreams-v3-epg.xml',util.ADDON.getAddonInfo('path'),'modern','720p',viewManager=self)
		self.changeCat()
		self.window.doModal()
		self.window.onClosed()
		del self.window
		self.window = None

	def showCats(self):
		util.setSetting('last_mode','CATS')
		self.saveView()
		self.window = eventslistpanel_720.KodiListDialog('script-smoothstreams-v3-category.xml',util.ADDON.getAddonInfo('path'),'modern','720p',viewManager=self)
		self.changeCat()
		self.window.doModal()
		self.window.onClosed()
		del self.window
		self.window = None

	def showPanel(self):
		util.setSetting('last_mode','PANEL')
		self.saveView()
		self.window = eventslistpanel_720.KodiListDialog('script-smoothstreams-v3-panel.xml',util.ADDON.getAddonInfo('path'),'modern','720p',viewManager=self)
		self.changeCat()
		self.window.doModal()
		self.window.onClosed()
		del self.window
		self.window = None

	def showChannels(self):
		util.setSetting('last_mode','CHANNELS')
		self.saveView()
		self.window = channelslist.KodiChannelsListDialog('script-smoothstreams-v3-channels_list.xml',util.ADDON.getAddonInfo('path'),'Main','1080i',viewManager=self)
		self.changeCat()
		self.window.doModal()
		self.window.onClosed()
		del self.window
		self.window = None

	def doChannelEntry(self,digit,size='720p'):
		if size == '1080i':
			window = windowutils.KodiChannelEntry('script-smoothstreams-v3-channel_entry.xml',util.ADDON.getAddonInfo('path'),'Main','1080i',viewManager=self,digit=digit)
		else:
			window = windowutils.KodiChannelEntry('script-smoothstreams-v3-channel_entry.xml',util.ADDON.getAddonInfo('path'),'modern','720p',viewManager=self,digit=digit)
		window.doModal()
		ret = None
		if window.set:
			ret = window.digits
		del window
		return ret

	def checkChannelEntry(self,action,size='720p'):
		if action.getId() >= xbmcgui.REMOTE_0 and action.getId() <= xbmcgui.REMOTE_9:
			self.doChannelEntry(str(action.getId() - 58),size)
			return True
		return False



	def createCategoryFilter(self):
		if util.getSetting('show_all',True): return None

		cats = (    ('American Football',('NCAAF', 'NFL')),
					('Baseball', None),
					('Basketball', ('NBA', 'NCAAB')),
					('Boxing + MMA', None),
					('Cricket', None),
					('Golf', None),
					('Ice Hockey', None),
					('Motor Sports', ('Formula 1', 'Nascar')),
					('Olympics', None),
					('Other Sports', None),
					('Rugby', None),
					('Tennis', None),
					('TV Shows', None),
					('World Football', None),
					('Wrestling', None)
		)
		catFilter = []
		si=0
		for cat, subs in cats:
			si+=1
			if util.getSetting('show_{0}'.format(30400+si),True):
				if subs:
					add = []
					hide1 = False
					for s in subs:
						si+=1
						if util.getSetting('show_{0}'.format(30400+si),True):
							add.append(s)
						else:
							hide1 = True
					if hide1:
						catFilter += add
					else:
						catFilter.append(cat)
				else:
					catFilter.append(cat)
			else:
				if subs: si+=len(subs)
		return catFilter

	def handlePreClose(self):

		if util.getSetting('back_opens_context',False):
			xbmc.executebuiltin('Action(ContextMenu)')
			return True

		# if xbmc.getCondVisibility('Player.HasVideo'):
		# 	if util.getSetting('fullscreen_on_exit',True):
		# 		if util.getSetting('keep_epg_open',False):
		# 			self.fullscreenVideo()
		# 			return True
		#
		# 		self.mode = None
		# 		self.window.close()
		# 		self.fullscreenVideo()
		#
		# 		return False
		if xbmcgui.Dialog().yesno(heading="Close", message="Do you really want to exit?"):
			xbmcgui.Window(10000).setProperty('script.smoothstreams-v3.service.started', '')
			self.mode = None
			return False
		else: return True

	def doContextMenu(self,show_download=True):
		self.window.setProperty('covered','yes')
		try:
			self._doContextMenu(show_download=show_download)
		finally:
			if self.window: self.window.setProperty('covered','')

	def _doContextMenu(self,show_download=True):
		item = self.getSelectedProgramOrChannel()
		d = util.xbmcDialogSelect()
		if not self.search_key == '':
			return

		d.addItem('play_channel','Play Channel')
		d.addItem('search_event','Search by keyword...')
		# d.addItem('favourite','Favourite')
		if show_download:
			if item._ssType == 'PROGRAM':
				if item.isAiring():
					if self.player.canDownload(): d.addItem('download',u'Record:  [B][I]{0}[/I][/B]'.format(item.title))
				else:
					d.addItem('schedule',u'Schedule:  [B][I]{0}[/I][/B]'.format(item.title))
					if self.player.canDownload(): d.addItem('download',u'Record:  [B][I]{0}[/I][/B]'.format(item.channelParent.title))
			else:
				if self.player.canDownload(): d.addItem('download',u'Record:  [B][I]{0}[/I][/B]'.format(item.title))
		if self.player.isDownloading():
			d.addItem('stop_download','Stop Recording')

		if not DownloadRegistry().empty():
			d.addItem('view_recordings','View Recordings')
		d.addItem('changeQuality', 'Change Quality')
		d.addItem('changeView','Change View')
		if self.mode == 'CHANNELS':
			d.addItem('channel_listings', 'Toggle Description')
		d.addItem('settings','Settings')
		if (util.getSetting('back_opens_context',False) or util.getSetting('show_fullscreen_option',False)) and xbmc.getCondVisibility('Player.HasVideo'):
			d.addItem('fullscreen','Fullscreen Video')
		# if util.getSetting('keep_epg_open',False) or util.getSetting('back_opens_context',False):
		d.addItem('exit','Exit')

		selection = d.getResult()
		if selection == None: return
		if selection == 'search_event':
			self.search()
		elif selection == 'channel_listings':
			if self.description:
				self.window.setProperty('description', '')
				self.description = False
			else:
				self.window.setProperty('description', 'true')
				self.description = True
		elif selection == 'download':
			self.record(item)
		elif selection == 'schedule':
			self.scheduleRecording(item)
		elif selection == 'stop_download':
			self.player.stopDownload()
		elif selection == 'view_recordings':
			self.viewRecordings()
		elif selection == 'cat':
			self.switch('CATS')
		elif selection == 'cat':
			self.switch('CHANNELS')
		elif selection == 'epg':
			self.switch('EPG')
		elif selection == 'panel':
			self.switch('PANEL')
		elif selection == 'play_channel':
			self.playChannel()
		elif selection == 'settings':
			self.showSettings()
		elif selection == 'favourite':
			self.favourite()
		elif selection == 'fullscreen':
			xbmc.executebuiltin('Action(FullScreen)')
		elif selection == 'modern' or selection == 'classic':
			self.changeTheme(selection)
		elif selection == 'changeView':
			self.changeView(selection)
		elif selection == 'changeQuality':
			self.changeQuality(selection)
		elif selection == 'exit':
			self.mode = None
			self.window.close()
			# if util.getSetting('fullscreen_on_exit',True): self.fullscreenVideo()

	def changeQuality(self,quality):
		dialog = util.xbmcDialogSelect('Change Quality')
		dialog.addItem(0,'High Definition 720p')
		dialog.addItem(1, 'Medium Definition 540p')
		dialog.addItem(2,'Low Definition 360p')
		result = dialog.getResult()
		util.setSetting('high_def', result)
		return

	def changeView(self,view):
		dialog = util.xbmcDialogSelect('Change View')
		dialog.addItem('channels','Channels List')
		dialog.addItem('epg','EPG')
		dialog.addItem('cat','Events List')
		# if util.getSetting('theme') == 'true':
		dialog.addItem('panel','Events Panel')
		result = dialog.getResult()

		if result == 'cat':
			self.switch('CATS')
		elif result == 'epg':
			self.switch('EPG')
		elif result == 'channels':
			self.switch('CHANNELS')
		elif result == 'panel':
			self.switch('PANEL')
		return

	def saveView(self):
		profile_file = os.path.join(util.PROFILE,'last_mode')
		with open(profile_file, 'w') as f:
			f.write(util.getSetting('last_mode') or "CHANNELS")
		return


	def loadView(self):
		profile_file = os.path.join(util.PROFILE,'last_mode')
		try:
			with open(profile_file,'r') as fp:
				mode = fp.read()
				util.setSetting('last_mode', mode)
		except:
			self.saveView()

	def changeTheme(self,theme):
		self.theme = theme
		util.setSetting('theme',theme)
		self.window.doClose()
		self.mode=None
		#xbmc.executebuiltin("xbmc.RunScript(script.smoothstreams-v3)")
		return

	def createFav(self,name='Default'):
		profile_file = os.path.join(util.PROFILE,'favourite')
		profile_name = os.path.join(util.PROFILE,name)
		default_profile = "show_all:true,show_30401:true,show_30402:true,show_30403:true,show_30404:true,show_30405:true,show_30406:true,show_30407:true,show_30408:true,show_30409:true,show_30410:true,show_30411:true,show_30412:true,show_30413:true,show_30414:true,show_30415:true,show_30416:true,show_30417:true,show_30418:true,show_30419:true,show_30420:true,show_30421:true"

		if not os.path.exists(profile_name):
			with open(profile_file,'a') as fav:
				fav.write(name + ',')

			with open(profile_name, 'w') as new_fav:
				new_fav.write(default_profile)
			util.notify('Favourite List', name + ' list created')
			if name == 'Default':
				util.setSetting('favourite',name)
			return
		if not name == 'Default':
			util.notify('Favourite List', name + ' list exists')

	def deleteFav(self, dialog=None):
		if not dialog:  return
		profile_file = os.path.join(util.PROFILE,'favourite')

		favList = self.listFav(dialog,1)
		for fav in favList:
			if not fav == 'Default':
				dialog.addItem(fav,fav)

		result = dialog.getResult()
		if result:
			if result == util.getSetting('favourite'):
				self.switchFav('Default')
			favList.remove(result)
			with open(profile_file,'w') as favFile:
				favFile.write(','.join(favList) + ',')
			del_profile = os.path.join(util.PROFILE, result)
			xbmc.log(str(del_profile),2)
			os.remove(del_profile)
			util.notify('Favourite List', result + ' list deleted')

	def listFav(self,dialog=None,getList=0):
		if not dialog:  return
		profile_file = os.path.join(util.PROFILE,'favourite')

		with open(profile_file,'r') as fp:
			favList = fp.read().split(',')[0:-1]

		if favList:
			if getList: return favList
			active_fav = util.getSetting('favourite')
			for fav in favList:
				if not fav: continue
				value = fav
				if fav == active_fav:   fav = '[COLOR orange][B]' + fav + '[/B][/COLOR]'

				dialog.addItem(value,fav)
		dialog.addItem('create_favourite','[COLOR blue]Create Favourite List[/COLOR]')
		dialog.addItem('delete_favourite','[COLOR red]Delete Favourite List[/COLOR]')

	def switchFav(self,result):
		default_profile = "show_all:true,show_30401:true,show_30402:true,show_30403:true,show_30404:true,show_30405:true,show_30406:true,show_30407:true,show_30408:true,show_30409:true,show_30410:true,show_30411:true,show_30412:true,show_30413:true,show_30414:true,show_30415:true,show_30416:true,show_30417:true,show_30418:true,show_30419:true,show_30420:true,show_30421:true"

		if not util.getSetting('favourite') == result:
			current_profile_data = ""
			current_profile_file = os.path.join(util.PROFILE,util.getSetting('favourite'))
			for set in default_profile.split(','):
				val = util.getSetting(set.split(':')[0])
				current_profile_data += set.split(':')[0] +":"+val + ","

			#Write existing settings to previous profile file
			with open(current_profile_file, 'w') as c_p_f:
				c_p_f.write(current_profile_data[0:-1])

			util.setSetting('favourite',result)
			current_profile_file = os.path.join(util.PROFILE,util.getSetting('favourite'))
			#Generate new setting from selected profile file
			with open(current_profile_file, 'r') as c_p_f:
				data = c_p_f.read()

			category = []
			for set in data.split(','):
				util.setSetting(set.split(':')[0],set.split(':')[1])
				xbmc.log(str(set),2)
				if set.split(':')[1] == 'true':
					xbmc.log("in if...",2)
					data = [d['name'] for d in self.window.categories if d['id'] == set.split(':')[0]]
					xbmc.log(str(data),2)
					if data:    category.append(data[0])
			xbmc.log(str(category),2)
			self.window.category=category
			#Enable new list
			util.notify('Favourite List', result + ' list enabled.')
			self.window.fillCategories()
			self.window.showList()

		else:
			util.notify('Favourite List', result + ' is already enabled.')
	def favourite(self):
		favList = []
		dialog = util.xbmcDialogSelect('Manage Favourite')
		self.listFav(dialog)
		result = dialog.getResult()

		if result == 'create_favourite':
			keyword = xbmcgui.Dialog().input('Enter Favourite List Name')
			if not keyword: return
			#Create fresh profile for favourite
			self.createFav(keyword)

		elif result == 'delete_favourite':
			deldialog = util.xbmcDialogSelect('Delete Favourite')
			self.deleteFav(deldialog)

		elif result:
			if xbmcgui.Dialog().yesno(
				heading='Favourite List',
				message='Do you want to enable ' + result + ' profile?'
			):
				self.switchFav(result)

	def search(self):
		keyword = xbmcgui.Dialog().input('Enter search keyword')
		if not keyword:
			return
		self.search_key = keyword

		# self.window_search = KodiListDialog('script-smoothstreams-v3-category.xml',util.ADDON.getAddonInfo('path'),'modern','720p',viewManager=self)
		# self.window_search.doModal()
		# self.window_search.onClosed()
		# del self.window_search
		self.switch('CATS')
		# self.search_key = ''
		# self.window_search = None


	def showSettings(self):
		gmtOffsetOld = util.getSetting('gmt_offset',0)
		old12HourTimes = util.getSetting('12_hour_times',False)
		oldLoginPass = (util.getSetting('service',0),util.getSetting('username'),util.getSetting('user_password'))
		state = self.window.getSettingsState()
		oldFULLEPG = util.getSetting('guide_source','sports').lower()

		oldTheme = util.getSetting('theme',False)
		oldMode = util.getSetting('mode')

		util.openSettings()

		self.setEPGLimits()
		skinutils.setColours()
		settingsOffsetHours = util.getSetting('gmt_offset',0)
		if gmtOffsetOld != settingsOffsetHours or old12HourTimes != util.getSetting('12_hour_times',False):
			#self.setutcOffsetMinutes()
			#self.updateChannels()

			self.window.updateSettings(state)

		if oldFULLEPG != util.getSetting('guide_source','sports').lower():
			settings.EPGTYPE = util.getSetting('guide_source','sports').lower()
			self.reloadChannels()
			self.window.updateEPG()

		if oldTheme != util.getSetting('theme',False):
			xbmc.log("Change Theme.....",2)
			self.mode=None
			self.window.close()
			xbmcgui.Dialog().ok("Restart SmoothStreams","Theme has been changed, please restart the addon to take effect.")
			return
		if oldMode != util.getSetting('mode'):
			xbmc.log("Change Mode.....",2)
			modes = {'Events List':'CATS','EPG':'EPG','Events Panel':'PANEL','Channels List':'CHANNELS'}
			self.switch(modes[util.getSetting('mode')])
			return

	def getSelectedProgramOrChannel(self):
		return self.window.getSelectedProgram() or self.window.getSelectedChannel()

	def getCurrentProgramOrChannel(self):
		program = self.window.getSelectedProgram()
		if program and program.isAiring(): return program
		return self.window.getSelectedChannel()

	def record(self,item):
		self.player.download(item)

	def scheduleRecording(self,item):
		self.player.schedule(item)

	def checkRegistry(self,registry):
		key = util.getSetting('sort_recordings_alpha',False) and (lambda x: x.display) or (lambda x: x.ID)
		registry.cleanScheduled()
		return sorted([i for i in registry if i._udType != 'SCHEDULE_ITEM'],key=key,reverse=not util.getSetting('sort_recordings_alpha',False))

	def viewRecordings(self):
		with DownloadRegistry() as registry:
			result = True
			while result != None:
				dialog = util.xbmcDialogSelect('Select Recording')
				missing = False
				for item in self.checkRegistry(registry) + URLDownloader.scheduledItems():
					if not item: continue
					if item.exists():
						rec = ''
						if item.isDownloading(): rec = u'[COLOR FFFF0000]{0}[/COLOR] '.format(unichr(0x2022))
						dialog.addItem(item,u'{0}{1}'.format(rec,item.display))
					elif item._udType == 'SCHEDULE_ITEM':
						dt = datetime.datetime.fromtimestamp(item.start)
						if datetime.datetime.now().strftime('%j') == dt.strftime('%j'):
							dd = dt.strftime(util.TIME_DISPLAY + ' (Today)')
						else:
							dd = dt.strftime(util.TIME_DISPLAY + '(%a)')
						dialog.addItem(item,u'[COLOR FF9999FF]@[/COLOR] {1}:  [I]{0}[/I]'.format(item.display,dd))
					else:
						missing = True
						dialog.addItem(item,u'([COLOR FFFF0000]MISSING[/COLOR]) {0}'.format(item.display))
				dialog.addItem('delete','[B][Delete Recordings][/B]')
				if missing:
					dialog.addItem('remove_missing','[B][Remove Missing Entries][/B]')
				result = dialog.getResult()
				if result == None: return
				if result == 'delete':
					self.deleteRecordings(registry)
					continue
				elif result == 'remove_missing':
					registry.removeMissing()
					continue

				item = result
				if item.exists():
					self.player._playRecording(item)
					return
				elif item._udType == 'SCHEDULE_ITEM':
					self.unScheduleItem(registry,item)
				else:
					delete = xbmcgui.Dialog().yesno(
						heading='Missing',
						message='The recording is missing for this entry. Would you like to delete this entry?',
						nolabel='Keep',
						yeslabel='Delete'
					)
					if delete:
						registry.remove(item)

	def deleteRecordings(self,registry):
		result = True
		while result != None:
			dialog = util.xbmcDialogSelect('Delete Recording')
			key = util.getSetting('sort_recordings_alpha',False) and (lambda x: x.display) or (lambda x: x.ID)
			for item in sorted(registry,key=key,reverse=not util.getSetting('sort_recordings_alpha',False)):
				if item.exists():
					rec = ''
					if item.isDownloading(): rec = u'[COLOR FFFF0000]{0}[/COLOR] '.format(unichr(0x2022))
					dialog.addItem(item,u'Delete: {0}{1}'.format(rec,item.display))
				else:
					dialog.addItem(item,u'Delete: ([COLOR FFFF0000]MISSING[/COLOR]) {0}'.format(item.display))
			dialog.addItem('delete_all','[B][Delete All][/B]')
			result = dialog.getResult()
			if result == None: return
			if result == 'delete_all':
				delete = xbmcgui.Dialog().yesno(
					heading='Delete',
					message='This will PERMANENTLY remove ALL recording files. Are you really sure you want to do this?',
					nolabel='Keep',
					yeslabel='DELETE!'
				)
				if not delete: continue
				delete = xbmcgui.Dialog().yesno(
					heading='Delete',
					message='LAST CHANCE TO CHANGE YOUR MIND! Do you really want to delete ALL recordings?',
					nolabel='Keep',
					yeslabel='DELETE!'
				)
				if not delete: continue
				return registry.deleteAll()
			delete = xbmcgui.Dialog().yesno(
				heading='Delete',
				message='This will PERMANENTLY remove this recording file. Are you sure you would like to delete this recording?',
				nolabel='Keep',
				yeslabel='Delete'
			)
			if delete:
				registry.delete(result)

	def unScheduleItem(self,registry,item):
		delete = xbmcgui.Dialog().yesno(
			heading='Delete',
			message='Are you sure you would like to remove this scheduled recording?',
			nolabel='Keep',
			yeslabel='Remove'
		)
		if delete:
			URLDownloader.unSchedule(item)
			registry.delete(item)

	def playChannel(self):
		channel = self.selectChannel()
		if not channel: return
		chanID = channel['ID']
		player.initPlay(chanID)

	def selectChannel(self):
		d = util.xbmcDialogSelect('Channels')
		for channel in settings.CHANNELS:
			d.addItem(channel,channel['ID'] + ' - ' + channel['display-name'])
		return d.getResult()

	def startOfDay(self):
		return timeutils.startOfDayLocalTimestamp()

	def timeInDay(self):
		return timeutils.timeInDayLocalSeconds()/60

	def getHalfHour(self):
		tid = self.timeInDay()
		return tid - (tid % 30)

	def initDisplayOffset(self):
		timeInDay = self.timeInDay()

		self.displayOffset = (timeInDay - (timeInDay % 30))
		self.setEPGLimits()

	def setutcOffsetMinutes(self):
		settingsOffsetHours = util.getSetting('gmt_offset',0)
		if settingsOffsetHours:
			self.setutcOffsetMinutesFromSettings(settingsOffsetHours)
		else:
			timeutils.setLocalTimezone()

	def setutcOffsetMinutesFromSettings(self, settingsOffsetHours):
		utcOffsetHalfHour = util.getSetting("gmt_offset_half",False)
		dst = util.getSetting("daylight_saving_time",False)

		offset = 0
		# if settingsOffsetHours == 1:
		if settingsOffsetHours < 14:
			offset = 60 * (settingsOffsetHours - 1)
		elif settingsOffsetHours > 13:
			offset = -60 * (settingsOffsetHours - 13)

		if dst:
			offset += 60

		if utcOffsetHalfHour:
			offset += 30

		timeutils.setLocalTimezone(offset)

	def initChannels(self):
		sod = self.startOfDay()
		for channel in settings.CHANNELS:
			for program in channel.get('programs',{}):
				program.update(sod)

	def getProgramByID(self,pid):
		for channel in settings.CHANNELS:
			for program in channel.get('programs',{}):
				if pid == program.pid:
					return program


