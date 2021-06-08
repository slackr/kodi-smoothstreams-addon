# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals
import urllib, time, os
import math
import requests
import xbmc, xbmcgui
from lib import util, settings
from lib import downloadregistry
import URLDownloader
from . import timeutils, authutils, chanutils


import base64
import threading

import xbmc
import xbmcgui
from lib import kodijsonrpc
from lib import colors
from lib import videoosd
from lib import util

try:
	import cPickle as pickle
except:
	import pickle

FIVE_MINUTES_MILLIS = 300000


class BasePlayerHandler(xbmc.Player):
	def __init__(self, session_id=None):
		self.player = xbmc.Player()
		self.media = None
		self.baseOffset = 0
		self.timelineType = None
		self.lastTimelineState = None
		self.ignoreTimelines = False
		self.playQueue = None
		self.sessionID = session_id

	def onPrePlayStarted(self):
		pass

	def onPlayBackStarted(self):
		pass

	def onPlayBackPaused(self):
		pass

	def onPlayBackResumed(self):
		pass

	def onPlayBackStopped(self):
		pass

	def onPlayBackEnded(self):
		pass

	def onPlayBackSeek(self, stime, offset):
		pass

	def onPlayBackFailed(self):
		pass

	def onVideoWindowOpened(self):
		pass

	def onVideoWindowClosed(self):
		pass

	def onVideoOSD(self):
		pass

	def onSeekOSD(self):
		pass

	def onMonitorInit(self):
		pass

	def tick(self):
		pass

	def close(self):
		pass

	@property
	def trueTime(self):
		return self.baseOffset + self.player.currentTime

	def getCurrentItem(self):
		if self.player.playerObject:
			return self.player.playerObject.item
		return None

	def shouldSendTimeline(self, item):
		return item.ratingKey and item.getServer()

	def currentDuration(self):
		if self.player.playerObject:
			try:
				return int(self.player.getTotalTime() * 1000)
			except RuntimeError:
				pass

		return 0

	def updateNowPlaying(self, force=False, refreshQueue=False, state=None):
		return


def initPlay(channel,*args,**kwargs):
	util.DEBUG_LOG("disable_osd: %s" % util.getSetting('disable_osd'))
	if util.getSetting('disable_osd') != 'true':
		try:
			viewManager = kwargs['viewManager']
		except:
			viewManager = None
		settings.PLAYER = OSDHandler(viewManager=viewManager)
		settings.PLAYER.play(channel)
	else:
		settings.PREVCHAN = settings.CURCHAN
		settings.CURCHAN = int(channel)
		xbmc.Player().play(item=authutils.getChanUrl(channel), listitem=chanutils.programListItem(channel))


class OSDHandler(BasePlayerHandler):
	NO_SEEK = 0
	SEEK_IN_PROGRESS = 2
	SEEK_PLAYLIST = 3
	SEEK_REWIND = 4
	SEEK_POST_PLAY = 5

	MODE_ABSOLUTE = 0
	MODE_RELATIVE = 1

	def __init__(self, session_id=None, impatient=False, *args, **kwargs):
		BasePlayerHandler.__init__(self, session_id)
		try:
			self.viewManager = kwargs['viewManager']
		except:
			self.viewManager = None
		self.dialog = None
		self.impatient = impatient
		if not impatient:
			if not settings.CHANNELSLIST:
				chanutils.createChannelsList()
			self.playlist = settings.CHANNELSLIST
		else:
			# add a pickled fake list here
			self.playlist = chanutils.useFakeList()
			settings.CHANNELSLIST = self.playlist
			# self.playlist = None
		self.playQueue = None
		self.timelineType = 'video'
		self.ended = False
		self.bifURL = ''
		self.title = ''
		self.title2 = ''
		self.reset()

	def playFromProgram(self,program, ID=0):
		channel = program.channel
		if ID:
			channel = ID
		img = util.getIcon(program.channelName,channel)
		if len(channel) == 1: channel = '0' + str(channel)
		url = authutils.getChanUrl(channel)
		item = xbmcgui.ListItem(program.title, path=url)
		item.setArt(({'icon':img, 'thumb':img}))

		# mediatype	string - "video", "movie", "tvshow", "season", "episode" or "musicvideo"

		infolabels = {
			# 'Channel': program.channel,
			# 'ChannelNumberLabel': program.channel_number,
			'Mediatype': 'tvshow',
			'Title': program.title,
			'Genre': program.category,
			'Plot': program.description or program.title,
			'plotoutline': program.description or program.title,
			'originaltitle': None,
			'tvshowtitle': program.channelName,
			'episode': str(timeutils.secs2stringLocal_dur(program.duration)),
			'country': timeutils.secs2stringLocal_time(program.stop),
			'director': timeutils.secs2stringLocal_dur(program.duration),
			'duration': "%d" % program.duration,
			# 'startTime': None,
			# 'endTime': None,
			'Studio': timeutils.secs2stringLocal_time(program.start)
		}
		item.setInfo(type='video', infoLabels=infolabels)
		item.setProperty('IsPlayable', 'true')
		item.setArt({
			'thumb': img,
			'poster': img,
			'fanart': img,
			'cover': img
		})
		self._play(url,item, program, channel)

	def checkURL(self,url):
		return url
		try:
			tm = int(util.getSetting('url_timeout'))
		except:
			tm = 3
		util.DEBUG_LOG("url_timeout is:%s" % tm)
		# test channel is active
		test_url = url
		util.DEBUG_LOG("Checking url: %s" % url)
		if url.startswith('rtmp'):
			# test it as hls as i cannot test rtmp at this time
			test_url = url.replace('rtmp', 'https').replace('.stream', '.stream/playlist.m3u8').replace('3615',
																										'443').replace(
				'3625', '443').replace('3635', '443').replace('3665', '443').replace(' live=1 timeout=20', "")
			util.DEBUG_LOG(test_url)
		t1 = time.time()
		util.DEBUG_LOG("Testing first")
		util.DEBUG_LOG(test_url)
		try:
			response = requests.get(test_url, timeout=1)
			t2 = time.time()
			if response.status_code == 200:
				ping_results = t2 - t1
				util.DEBUG_LOG("Channel appears to be active")
				return url

		except:
			pass

		test_url = test_url.replace('q3.stream', 'q1.stream').replace('q2.stream', 'q1.stream')
		t1 = time.time()
		util.DEBUG_LOG("Testing second")
		util.DEBUG_LOG(test_url)
		try:
			response = requests.get(test_url, timeout=1)
			t2 = time.time()
			if response.status_code == 200:
				ping_results = t2 - t1
				util.DEBUG_LOG("Selected Quality not available, resorting to HD")
				url = url.replace('q3.stream', 'q1.stream').replace('q2.stream', 'q1.stream')
				return url
		except:
			pass

		t1 = time.time()
		util.DEBUG_LOG("Testing third")
		util.DEBUG_LOG(test_url)
		try:
			response = requests.get(test_url, timeout=tm)
			t2 = time.time()
			if response.status_code == 200:
				ping_results = t2 - t1
				util.DEBUG_LOG("Channel appears to be active")
				return url
		except:
			pass

		test_url = test_url.replace('q3.stream', 'q1.stream').replace('q2.stream', 'q1.stream')
		t1 = time.time()
		util.DEBUG_LOG("Testing Fourth")
		util.DEBUG_LOG(test_url)
		try:
			response = requests.get(test_url, timeout=tm)
			t2 = time.time()
			if response.status_code == 200:
				ping_results = t2 - t1
				util.DEBUG_LOG("Selected Quality not available, resorting to HD")
				url = url.replace('q3.stream', 'q1.stream').replace('q2.stream', 'q1.stream')
				return url
		except:
			pass
		return False

	def _play(self,url,item, program, ch):
		output_url = False
		output_url = url
		# if not output_url:
		# 	util.DEBUG_LOG("Channel appears to be dead")
		# 	if xbmcgui.Dialog().yesno("", "Channel appears to be dead, If you see this message repeatedly consider increasing the 'Channel Timeout Time' in the Advanced section of the settings. Would you like to try anyway?"):
		# 		output_url = url.replace('q3.stream', 'q1.stream').replace('q2.stream', 'q1.stream')
		# 	else:
		# 		if self.dialog and not self.player.isPlaying():
		# 			self.dialog.hideOSD()
		# 			d = self.dialog
		# 			self.dialog = None
		# 			d.doClose()
		# 			del d
		# 			util.garbageCollect()
		# 		# self.sessionEnded()
		#
		# if output_url:
		channel = program.channel
		img = util.getIcon(program.channelName, program.channel_number)
		self.setup(program.duration, program.channel_number, img, title=program.title, title2=program.description, seeking=False, live=True)
		self.mode = self.MODE_ABSOLUTE
		self.stopAndWait()  # Stop before setting up the handler to prevent player events from causing havoc
		settings.PREVCHAN = settings.CURCHAN
		settings.CURCHAN = int(ch)
		self.saveChan()
		util.setGlobalProperty('player.islive', '1')
		util.garbageCollect()
		self.player.play(output_url,item,False,0)

	def saveChan(self):
		profile_file = os.path.join(util.PROFILE,'last_chan')
		with open(profile_file, 'w') as f:
			f.write(str(settings.CURCHAN or 1))
		return

	def showMessage(self, heading, message):
		duration = 5
		xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s)' % (heading, message, duration))

	def canDownload(self):
		return URLDownloader.canDownload()

	def getFilename(self,base):
		filename = xbmcgui.Dialog().input(util.T(30104),base)
		if not filename: return
		filename = filename
		return filename

	def getDownloadPath(self):
		if not util.getSetting("download_path"):
			self.showMessage(util.T(30600), util.T(30601))
			util.ADDON.openSettings()

		return util.getSetting("download_path")

	def download(self,item):
		duration = 0
		program = None
		if item._ssType == 'PROGRAM':
			program = item
		else:
			program = item.currentProgram()

		if program and program.isAiring():
			cnum = program.channel if util.getSetting('guide_source','sports').lower() == 'alt' else int(program.channel_number)
			url = authutils.getChanUrl(cnum,force_hls=True,for_download=True)
			duration = program.minutesLeft()
			title = program.title + time.strftime(' - %H:%M:%S'.format(util.TIME_DISPLAY),time.localtime())
		else:
			if program: item = item.channelParent #Selected program but it is not airing, use channel info
			cnum = item['id'] if util.getSetting('guide_source','sports').lower() == 'alt' else item['channel']
			url = authutils.getChanUrl(cnum,force_hls=True,for_download=True)
			title = item['display-name'] + time.strftime(' - %b %d {0}'.format(util.TIME_DISPLAY),time.localtime())

		authutils.check_token()
		filename = self.getFilename(title)
		if not filename: return
		title = filename
		filename = util.cleanFilename(filename) #In case the user added something unsafe
		minutes = xbmcgui.Dialog().numeric(0, util.T(32008), str(math.ceil(float(duration)) or 120))

		if not minutes:
			util.LOG("No duration set, using remaining time.")
			minutes = duration
			# return None
		# url = self.checkURL(url)
		url = url.split("wmsAuthSign",1)[0]
		if len(url) > 10:
			download_path = self.getDownloadPath()
			if download_path:
				callback = 'RunScript(script.smoothstreams-v3,DOWNLOAD_CALLBACK,{download})'
				download = URLDownloader.download(url,download_path,filename,title,int(minutes),util.getSetting('direct_record',True),callback=callback)
				with downloadregistry.DownloadRegistry() as dr:
					dr.add(download)

	def schedule(self,program):
		item = URLDownloader.ScheduleItem()
		filename = self.getFilename(program.title)
		item.display = filename
		item.filename = util.cleanFilename(filename) #In case the user added something unsafe

		minutes = xbmcgui.Dialog().numeric(0, util.T(32008), str(math.ceil(float(program.epg.duration))))
		if not minutes:
			util.LOG("No duration set, using remaining time.")
			minutes = str(math.ceil(float(program.epg.duration)))
			# return None

		item.minutes = int(minutes)
		downloadPath = self.getDownloadPath()
		if not downloadPath: return
		item.targetPath = downloadPath
		item.url = authutils.getChanUrl(int(program.channel_number),force_rtmp=False,for_download=True)
		item.direct = util.getSetting('direct_record',True)
		item.start = program.start
		item.offset = 0
		xbmc.log(str(program.start),2)
		URLDownloader.schedule(item)
		clash = downloadregistry.DownloadRegistry().checkForClash(item.start)
		if clash:
			xbmc.executebuiltin('Notification(SmoothStreams.tv,Scheduled recording clashes with a previous schedule, only one can start at the same time!,5000)')
		else:
			with downloadregistry.DownloadRegistry() as dr:
				dr.add(item)
			xbmc.executebuiltin('Notification(SmoothStreams.tv,Scheduled recording set!,1500)')

	def stopDownload(self):
		URLDownloader.stopDownloading()

	def isDownloading(self):
		return URLDownloader.isDownloading()

	def _playRecording(self,item):
		url = item.path
		title = 'Recording: {0}'.format(item.display)
		item = xbmcgui.ListItem(title)
		item.setInfo('video', {'Title': title, 'Genre': 'Unknown'})
		# todo
		# channel = program.channel
		img = util.getIcon('150','150')
		self.setup(0, 150, img, title=title, title2='', seeking=False, live=False)
		self.mode = self.MODE_ABSOLUTE
		util.setGlobalProperty('player.islive', '')
		self.player.play(url,item,False,0)

	def getIcon(self, name=None, channel=None):
		if not channel:
			channel = settings.CURCHAN
			name = self.playlist[int(channel)-1].dataSource.channelName
		img = util.getIcon(name, channel)
		return img

	def getRatioComplete(self, channel=0):
		if channel == 0:
			channel = settings.CURCHAN
		program = self.playlist[channel-1].dataSource
		ratio = ((timeutils.nowLocalSecs()) - int(program.start))# / float(program.duration))
		return ratio

	def getProgram(self, channel=0):
		if channel == 0:
			channel = settings.CURCHAN
		program = self.playlist[channel-1].dataSource
		return program

	def getDuration(self, channel=0):
		if channel == 0:
			channel = settings.CURCHAN
		program = self.playlist[channel-1].dataSource
		return int(program.duration)

	def stopAndWait(self):
		return
		# todo fix
		if bool(self.getProperty('playing')):
			util.DEBUG_LOG('Player: Stopping and waiting...')
			self.stop()
			while not util.MONITOR.waitForAbort(0.1) and self.isPlaying():
				pass
			util.MONITOR.waitForAbort(0.2)
			util.DEBUG_LOG('Player: Stopping and waiting...Done')

	def onVideoWindowClosed(self):
		self.hideOSD()
		util.DEBUG_LOG('SeekHandler: onVideoWindowClosed')
		self.player.stop()


	def play(self,ch):
		chsan = str(ch)
		if int(ch) < 10: chsan = '0' + str(ch)
		chidx = int(ch) - 1
		item = self.playlist[chidx].dataSource
		self.playFromProgram(item, chsan)

	def restartChannel(self):
		self.play(settings.CURCHAN)

		return True

	def next(self, on_end=False):
		chanTarget = settings.CURCHAN + 1
		if chanTarget == 151: chanTarget = 1

		self.play(chanTarget)

		return True

	def prev(self):
		chanTarget = settings.CURCHAN -1
		if chanTarget == 0: chanTarget = 150

		self.play(chanTarget)
		return True

	def previousChannel(self):
		cur = settings.CURCHAN
		prev = settings.PREVCHAN
		if cur == prev: return True

		self.play(prev)
		return True

	def goToChannel(self, digits):
		if settings.CURCHAN == int(digits): return True
		self.play(int(digits))
		return True

	def onPlayBackError(self):
		util.DEBUG_LOG('SeekHandler: onPlayBackError')
		self.hideOSD(True)


	# functions past here are unmodified and are potentially untested
	def reset(self):
		self.duration = 0
		self.offset = 0
		self.baseOffset = 0
		self.seeking = self.NO_SEEK
		self.seekOnStart = 0
		self.mode = self.MODE_RELATIVE
		self.ended = False

	def setup(self, duration, channel, bif_url, title='', title2='', seeking=NO_SEEK, live=True):
		self.ended = False
		self.channel = channel
		self.seeking = seeking
		self.live = live
		self.duration = duration
		self.bifURL = bif_url
		self.title = title
		self.title2 = title2
		self.getDialog(setup=True)
		self.dialog.setup(self.duration, int(self.channel), self.bifURL, self.title, self.title2, self.playlist[settings.CURCHAN-1].dataSource, self.live)

	def getDialog(self, setup=False):
		if not self.dialog:
			self.dialog = videoosd.SeekDialog.create(show=True, osdHandler=self)

		return self.dialog

	@property
	def trueTime(self):
		if self.mode == self.MODE_RELATIVE:
			return self.baseOffset + self.player.currentTime
		else:
			if self.seekOnStart:
				return self.player.playerObject.startOffset + (self.seekOnStart / 1000)
			else:
				return self.player.currentTime + self.player.playerObject.startOffset

	def shouldShowPostPlay(self):
		if self.playlist and self.playlist.TYPE == 'playlist':
			return False

		if self.player.video.duration.asInt() <= FIVE_MINUTES_MILLIS:
			return False

		return True

	def showPostPlay(self):
		if not self.shouldShowPostPlay():
			return

		self.seeking = self.SEEK_POST_PLAY
		self.hideOSD(delete=True)

		self.player.trigger('post.play', video=self.player.video, playlist=self.playlist, osdHandler=self)

		return True

	def playAt(self, pos):
		if not self.playlist or not self.playlist.setCurrent(pos):
			return False

		self.seeking = self.SEEK_PLAYLIST
		self.player.playVideoPlaylist(self.playlist, osdHandler=self)

		return True

	def onSeekAborted(self):
		if self.seeking:
			self.seeking = self.NO_SEEK
			self.player.control('play')

	def showOSD(self, from_seek=False):
		self.updateOffset()

		if self.dialog:
			self.dialog.update(self.offset, from_seek)
			self.dialog.showOSD()

	def hideOSD(self, delete=False):
		# util.CRON.forceTick()
		if self.dialog:
			self.dialog.hideOSD()
			if delete:
				d = self.dialog
				self.dialog = None
				d.doClose()
				del d
				util.garbageCollect()

	def seek(self, offset, settings_changed=False, seeking=SEEK_IN_PROGRESS):
		return
		self.offset = offset

		if self.mode == self.MODE_ABSOLUTE and not settings_changed:
			util.DEBUG_LOG('New player offset: {0}'.format(self.offset))

			if self.player.playerObject.offsetIsValid(offset / 1000):
				if self.seekAbsolute(offset):
					return

		self.updateNowPlaying(state=self.player.STATE_PAUSED)  # To for update after seek

		self.seeking = self.SEEK_IN_PROGRESS

		util.DEBUG_LOG('New player offset: {0}'.format(self.offset))
		self.player._playVideo(offset, seeking=self.seeking, force_update=settings_changed)

	def fastforward(self):
		util.DEBUG_LOG('SeekHandler: fastForward')
		xbmc.executebuiltin('PlayerControl(forward)')

	def rewind(self):
		util.DEBUG_LOG('SeekHandler: rewind')

		if self.mode == self.MODE_ABSOLUTE:
			xbmc.executebuiltin('PlayerControl(rewind)')
		else:
			self.seek(max(self.trueTime - 30, 0) * 1000, seeking=self.SEEK_REWIND)

	def seekAbsolute(self, seek=None):
		self.seekOnStart = seek or self.seekOnStart
		if self.seekOnStart:
			self.player.control('play')
			seekSeconds = self.seekOnStart / 1000.0
			try:
				if seekSeconds >= self.player.getTotalTime():
					return False
			except RuntimeError:  # Not playing a file
				return False
			self.updateNowPlaying(state=self.player.STATE_PAUSED)  # To for update after seek
			self.player.seekTime(self.seekOnStart / 1000.0)
		return True

	def onPlayBackStarted(self):
		util.DEBUG_LOG('SeekHandler: onPlayBackStarted - mode={0}'.format(self.mode))

		# self.updateNowPlaying(force=True, refreshQueue=True)

	def onPlayBackResumed(self):
		util.DEBUG_LOG('SeekHandler: onPlayBackResumed')

		pass
		# self.updateNowPlaying()
		# self.hideOSD()

	def onPlayBackStopped(self):
		util.DEBUG_LOG('SeekHandler: onPlayBackStopped')
		self.hideOSD(delete=True)

	def onPlayBackEnded(self):
		util.DEBUG_LOG('SeekHandler: onPlayBackEnded')
		try:
			self.play(settings.CURCHAN)
		except:
			pass
		finally:
			self.hideOSD(True)

	def onPlayBackPaused(self):
		util.DEBUG_LOG('SeekHandler: onPlayBackPaused')
		pass
		# self.updateNowPlaying()

	def onPlayBackSeek(self, stime, offset):
		pass
		# if self.seekOnStart:
		# 	if self.dialog:
		# 		self.dialog.tick(stime)
		# 	self.seekOnStart = 0
		# 	return
		#
		# self.updateOffset()
		# self.showOSD(from_seek=True)

	def setSubtitles(self):
		subs = self.player.video.selectedSubtitleStream()
		if subs:
			xbmc.sleep(100)
			self.player.showSubtitles(False)
			path = subs.getSubtitleServerPath()
			if path:
				if self.mode == self.MODE_ABSOLUTE:
					util.DEBUG_LOG('Setting subtitle path: {0}'.format(path))
					self.player.setSubtitles(path)
					self.player.showSubtitles(True)
				else:
					util.DEBUG_LOG('Transcoded. Skipping subtitle path: {0}'.format(path))
			else:
				# u_til.TEST(subs.__dict__)
				# u_til.TEST(self.player.video.mediaChoice.__dict__)
				if self.mode == self.MODE_ABSOLUTE:
					util.DEBUG_LOG('Enabling embedded subtitles at: {0}'.format(subs.typeIndex))
					util.DEBUG_LOG('Kodi reported subtitles: {0}'.format(self.player.getAvailableSubtitleStreams()))
					self.player.setSubtitleStream(subs.typeIndex)
					self.player.showSubtitles(True)
		else:
			self.player.showSubtitles(False)

	def setAudioTrack(self):
		if self.mode == self.MODE_ABSOLUTE:
			track = self.player.video.selectedAudioStream()
			if track:
				try:
					currIdx = kodijsonrpc.rpc.Player.GetProperties(playerid=1, properties=['currentaudiostream'])['currentaudiostream']['index']
					if currIdx == track.typeIndex:
						util.DEBUG_LOG('Audio track is correct index: {0}'.format(track.typeIndex))
						return
				except:
					util.ERROR()

				xbmc.sleep(100)
				util.DEBUG_LOG('Switching audio track - index: {0}'.format(track.typeIndex))
				self.player.setAudioStream(track.typeIndex)

	def updateOffset(self):
		self.offset = int(self.player.getTime() * 1000)

	def initPlayback(self):
		self.seeking = self.NO_SEEK

		if self.mode == self.MODE_ABSOLUTE:
			self.seekAbsolute()

		self.setSubtitles()
		self.setAudioTrack()

	def onPlayBackFailed(self):
		util.DEBUG_LOG('SeekHandler: onPlayBackFailed')
		self.hideOSD(True)

		return True

	# def onSeekOSD(self):
	#     self.dialog.activate()

	def onVideoWindowOpened(self):
		self.getDialog().show()

		# self.initPlayback()

	def onVideoWindowClosed(self):
		self.hideOSD(True)
		util.DEBUG_LOG('SeekHandler: onVideoWindowClosed')

	def onVideoOSD(self):
		# xbmc.executebuiltin('Dialog.Close(seekbar,true)')  # Doesn't work :)
		self.showOSD()

	def tick(self):
		if self.seeking != self.SEEK_IN_PROGRESS:
			self.updateNowPlaying(force=True)

		if self.dialog:
			self.dialog.tick()

	def close(self):
		self.hideOSD(delete=True)

	def sessionEnded(self):
		if self.ended:
			return
		self.ended = True
		util.DEBUG_LOG('Player: Video session ended')
		# self.player.trigger('session.ended', session_id=self.sessionID)
		self.hideOSD(delete=True)

def downloadCallback(data):
	with downloadregistry.DownloadRegistry() as dr:
		dr.updateItem(URLDownloader.Download.deSerialize(data))
