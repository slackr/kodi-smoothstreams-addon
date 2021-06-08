from __future__ import absolute_import, division, unicode_literals
import sys,os,requests

from lib import util
from lib import settings
from lib.smoothstreams import chanutils, timeutils, schedule, authutils, skinutils, proxyutils, messageutils
import gc
import atexit
import threading
import time
import requests

import xbmc, xbmcvfs
import xbmcgui

from lib.smoothstreams import threadutils
from lib import background, kodigui



BACKGROUND = None


def waitForThreads():
	util.DEBUG_LOG('Main: Checking for any remaining threads')
	while len(threading.enumerate()) > 1:
		for t in threading.enumerate():
			if t != threading.currentThread():
				if t.isAlive():
					util.DEBUG_LOG('Main: Waiting on: {0}...'.format(t.name))
					if isinstance(t, threading._Timer):
						t.cancel()
						t.join()
					elif isinstance(t, threadutils.KillableThread):
						t.kill(force_and_wait=True)
					else:
						t.join()


@atexit.register
def realExit():
	util.LOG('REALLY FINISHED %s' % xbmc.LOGINFO)



def start():
	settings.init()
	try:
		url = 'https://guide.smoothstreams.tv/'
		headers = {'User-Agent': util.USER_AGENT}
		res = requests.get(url, headers=headers, timeout=5)
		if not res.status_code // 100 == 2:
			util.ERROR('SS servers are not responding')
			util.notify('SmoothStreams Error', 'SS servers are not responding')
		util.setGlobalProperty('running', '1')
		with util.Cron(5) as settings.CRON:
			settings.BACKGROUND = background.BackgroundWindow.create(function=_main)
			settings.BACKGROUND.modal()
			del settings.BACKGROUND
	except requests.exceptions.RequestException as e:
		util.ERROR('Please check your internet connection and try again')
		util.notify('SmoothStreams Error', 'Please check your internet connection and try again')
	finally:
		util.setGlobalProperty('running', '')
		xbmcgui.Window(10000).setProperty('script.smoothstreams-v3.service.started', '')


def _main():
	# util.DEBUG_LOG('[ STARTED: {0} -------------------------------------------------------------------- ]'.format(util.ADDON.getAddonInfo('version')))
	# util.DEBUG_LOG('USER-AGENT: {0}'.format(plex.defaultUserAgent()))
	background.setSplash()
	background.setSplashText("Downloading EPG")
	try:

		try:
			# 	set colours
			skinutils.setColours()
			settings.EPGTYPE = util.getSetting('guide_source', 'sports').lower()
			if xbmc.getInfoLabel('Window(10000).Property(script.smoothstreams-v3.service.started)') == '2':
				util.DEBUG_LOG("Service start")
				xbmcgui.Window(10000).setProperty('script.smoothstreams-v3.service.started', '1')

			# Check for service.py operating
			flag1 = os.path.join(util.PROFILE, 'serviceOperating')
			while True:
				if not os.path.exists(flag1): break

			schedule.cleanup()
			schedule.Download()
			messageutils.versionNotification()

			# create initial lists
			startOfDay = timeutils.startOfDayLocalTimestamp()
			background.setSplashText("Logging in")
			time1 = time.time()
			authutils.load_token()
			authutils.check_token()
			hash = settings.TOKEN['hash']
			time2 = time.time()
			util.LOG("look here login, login: %s" % (time2 - time1))
			if not hash: raise UnboundLocalError('Auth failed, exiting')
			if False:#util.getSetting('impatient','') == 'true':
				from lib.smoothstreams import player
				profile_file = os.path.join(util.PROFILE, 'last_chan')
				try:
					with open(profile_file, 'r') as fp:
						settings.CURCHAN = int(fp.read())
				except:
					settings.CURCHAN = 1

				# player = player.OSDHandler(impatient=True)
				import ssmain
				b = threading.Thread(target=ssmain.impatient, args=(settings.CURCHAN,))
				# b = threading.Thread(target=player.OSDHandler(impatient=True).play, args=(settings.CURCHAN,))
				b.start()

			settings.SCHEDULE = schedule.Schedule(False)



			background.setSplashText("Parsing EPG")

			# if not settings.CHANNELS:
			settings.SCHEDULE.epg(startOfDay)
			background.setSplashText("Creating Playlists")

			from lib.ssmain import main

			util.DEBUG_LOG("Time point 2")
			# background.setSplash(False)
			background.setSplashText("Launching Add-on")
			main()
		except:
			util.ERROR()

		finally:
			settings.BACKGROUND.activate()
			gc.collect(2)

	except:
		util.ERROR()
	finally:
		background.setSplashText("Closing Add-on")
		util.DEBUG_LOG('Main: SHUTTING DOWN...')
		xbmcgui.Window(10000).setProperty('script.smoothstreams-v3.service.started', '')
		# background.setShutdown()
		# player.shutdown()
		# util.CRON.stop()
		# backgroundthread.BGThreader.shutdown()
		# waitForThreads()
		# background.setBusy(False)
		background.setSplash(False)

		util.DEBUG_LOG('FINISHED')


		kodigui.MONITOR = None
		# util.shutdown()

		gc.collect(2)



if __name__ == '__main__':
	util.DEBUG_LOG("Time point 1")
	arg = None

	if len(sys.argv) > 1: arg = sys.argv[1] or False
	util.LOG(arg)
	if arg == 'REFRESH_SCHEDULE':
		from lib import smoothstreams
		from lib import util
		util.LOG("default.py forcing refresh")
		schedule.purge()
		schedule.Download().sscachejson(force=True)
	elif arg == 'ABOUT':
		from lib import util
		util.about()
	elif arg == "PROXY":
		prox = proxyutils.Proxy()
		prox.enableAddons()
		prox.updatePVRSettings()
		prox.dl_epg()
		prox.restartAddon()
	elif arg == 'DOWNLOAD_CALLBACK':
		from lib.smoothstreams import player
		player.downloadCallback(sys.argv[2])
	elif arg == 'REFRESH_HASH':
		from lib import util
		hashFile = os.path.join(xbmcvfs.translatePath(util.ADDON.getAddonInfo('profile')),'hash')
		if os.path.exists(hashFile):
			os.remove(hashFile)
		from lib.smoothstreams import authutils
		authutils.load_token()
		authutils.check_token(True)
		credentials = settings.TOKEN
		try:
			hash = credentials['hash']
		except:
			hash = ''
			util.ERROR("WARNING, Hash Failed")
		with open(hashFile,'w') as f:

			f.write(str(hash))
	elif arg == 'SERVICE_START':
		xbmcgui.Window(10000).setProperty('script.smoothstreams-v3.service.started', '2')
		start()
	else:
		if not xbmc.getInfoLabel('Window(10000).Property(script.smoothstreams-v3.service.started)'):
			# Prevent add-on updates from starting a new version of the addon
			xbmcgui.Window(10000).setProperty('script.smoothstreams-v3.service.started', '1')
			start()
		else:
			util.LOG("Already running! %s" % xbmc.getInfoLabel('Window(10000).Property(script.smoothstreams-v3.service.started)'))
