from __future__ import absolute_import, division, unicode_literals
import os, datetime, copy, xbmcgui, xbmc
from . import schedule, timeutils, authutils
from .. import util, kodigui, settings

try:
	import cPickle as pickle
except:
	import pickle

def createList():
	channelsNow = {}
	progressItems = []
	timeInDay = timeutils.timeInDayLocalSeconds()/60
	startOfDay = timeutils.startOfDayLocalTimestamp()
	channels = settings.CHANNELS
	for channel in channels:
		fakeProgram = channel
		elem = {
			'channel': str(channel['ID']),
			'channelName': str(channel['display-name']),
			'name': '',
			'time': startOfDay,
			'runtime': 3600 * 48,
			'version': '',
			'fake': '1',
			'_ssType': 'PROGRAM'
		}
		program = schedule.SSProgram('1', elem, 'No Category', startOfDay, [], str(channel['ID']))
		fakeItem = kodigui.ManagedListItem(channel['display-name'], channel['display-name'], iconImage=channel['logo'], data_source=program)
		color = schedule.SPORTS_TABLE.get('no category', {}).get('color', '808080')
		colorGIF = util.makeColorGif(color, os.path.join(util.COLOR_GIF_PATH, '{0}.gif'.format(color)))
		# todo use program type instead
		fakeItem.setProperty('flag', '')
		fakeItem.setProperty('channel', str(channel['ID']))
		fakeItem.setProperty('fake', '1')

		channelsNow[str(channel['ID'])] = fakeItem

		if not 'programs' in channel: continue
		channel['programs'].sort(key=lambda x: int(float(x.start)))
		for program in channel['programs']:
			indx = channel['programs'].index(program)
			try:
				p2 = channel['programs'][indx + 1]
			except:
				p2 = False

			start = program.epg.start
			stop = program.epg.stop
			old = False
			if 1 == 1:
				item = kodigui.ManagedListItem(channel['display-name'], program.title, thumbnailImage=channel['logo'], iconImage=channel['logo'], data_source=program)

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
				item.setProperty('fake', '')
				infolabels = {
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
					'duration': "%d" % program.duration,  # todo not working yet, seems that its a dynamic variable from the player itself
					'Studio': timeutils.secs2stringLocal_time(program.start)
				}
				item.setInfo('video', infolabels)
				item.setArt({
					'thumb': channel['logo'],
					'poster': channel['logo'],
					'fanart': channel['logo'],
				})
				if p2:
					nDT = datetime.datetime.fromtimestamp(p2.start, tz=localTZ)
					if nDT.day == nowDT.day:
						startDisp = datetime.datetime.strftime(nDT, util.TIME_DISPLAY)
					else:
						startDisp = datetime.datetime.strftime(nDT, '%a {0}'.format(util.TIME_DISPLAY))
					item.setProperty('NextTitle', p2.title)
					item.setProperty('NextStartTime', str(startDisp))
				# sort = (((start * 1440) + stop) * 100) + program.channel
				if stop <= timeInDay:
					item.setProperty('old', 'old')
					old = True
				elif start <= timeInDay:
					prog = ((timeInDay - start) / float(program.epg.duration)) * 100
					# todo kodi v18 fails on progress, could be a kodi issue though
					item.setProperty('Progress', str(prog))
					item.setProperty('EpgEventProgress', str(prog))
					prog = int(prog - (prog % 5))
					tex = 'progress_line/{0}.png'.format(prog)
					item.setProperty('playing', tex)
					progressItems.append(item)
				item.setProperty('channel', str(channel['ID']))
				item.setProperty('duration', program.displayDuration)
				item.setProperty('color', program.epg.colorGIF)
				item.setProperty('pid', program.pid)
				item.setProperty('video', '1')
				item.setProperty('flag', 'flags/{0}.png'.format(program.language))
				if item.getProperty('playing'):
					channelsNow[str(channel['ID'])] = item
					break


	temp = []

	for i in channelsNow:
		temp.append(channelsNow[i])
	channelsNow = temp
	channelsNow.sort(key=lambda x: int(float(x.getProperty('channel'))))
	return channelsNow

def createList2():
	programsList = []
	oldItems = []
	items = []
	channelsNow = []
	progressItems = []
	startOfDay = timeutils.startOfDayLocalTimestamp()
	timeInDay = timeutils.timeInDayLocalSeconds()/60
	for channel in settings.EVENTS_CHANNELS:
		if not 'programs' in channel: continue
		for program in channel['programs']:
			start = program.epg.start
			stop = program.epg.stop
			old = False

			if 1 == 1:
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
					if util.getSetting('last_mode') == 'PANEL':
						tex = 'progress_line/{0}.png'.format(prog)
					else:
						tex = 'progress_circle/{0}.png'.format(prog)
					item.setProperty('playing',tex)
					progressItems.append(item)
				item.setProperty('sort',str(sort))
				item.setProperty('channel',str(channel['ID']))
				item.setProperty('duration',program.displayDuration)
				item.setProperty('quality',program.epg.quality)
				item.setProperty('color',program.epg.colorGIF)
				item.setProperty('pid',program.pid)
				item.setProperty('flag','flags/{0}.png'.format(program.language))
				if old:
					oldItems.append(item)
				else:
					items.append(item)
	items.sort(key=lambda x: int(float(x.getProperty('sort'))))
	# oldItems.sort(key=lambda x: int(x.getProperty('sort')))
	# items = oldItems + items
	#
	# temp = []
	#
	# for i in items:
	# 	temp.append(items[i])
	# programsList = temp
	return items

	
def createFakeList():
	from lib import kodigui
	channelsNow = {}
	startOfDay = timeutils.startOfDayLocalTimestamp()
	channels = settings.CHANNELS
	for channel in channels:
		elem = {
			'channel': str(channel['ID']),
			'channelName': str(channel['display-name']),
			'name': '',
			'time': startOfDay,
			'runtime': 3600 * 48,
			'version': '',
			'fake': '1',
			'logo': channel['logo'],
			'_ssType': 'PROGRAM'
		}
		# program = SSProgram('1', elem, 'No Category', startOfDay, [], str(channel['ID']))
		# fakeItem = kodigui.ManagedListItem(channel['display-name'], channel['display-name'],
		#                                    iconImage=channel['logo'], data_source=program)
		# # todo use program type instead
		# fakeItem.setProperty('flag', '')
		# fakeItem.setProperty('channel', str(channel['ID']))
		# fakeItem.setProperty('fake', '1')

		channelsNow[str(channel['ID'])] = elem

	temp = []


	for i in channelsNow:
		temp.append(channelsNow[i])
	channelsNow = temp
	# channelsNow.sort(key=lambda x: int(x.getProperty('channel')))

	with open(os.path.join(util.PROFILE, 'fake.pickle'), 'wb') as pickle_file:
		pickle.dump(channelsNow, pickle_file, pickle.HIGHEST_PROTOCOL)

def useFakeList():
	from lib import kodigui
	channelsNow = {}
	startOfDay = timeutils.startOfDayLocalTimestamp()
	path = 	adv_file_path = os.path.join(xbmcvfs.translatePath('special://home'), 'addons', util.ADDON_ID , 'resources', 'fake.pickle')
	with open(path, 'rb') as pickle_file:
		channels = pickle.load(pickle_file)
	for elem in channels:
		program = schedule.SSProgram('1', elem, 'No Category', startOfDay, [], elem['channel'])
		fakeItem = kodigui.ManagedListItem(elem['channelName'], elem['channelName'],
		                                   iconImage=elem['logo'], data_source=program)
		fakeItem.setProperty('flag', '')
		fakeItem.setProperty('channel', elem['channel'])
		fakeItem.setProperty('fake', '1')

		channelsNow[elem['channel']] = fakeItem

	temp = []


	for i in channelsNow:
		temp.append(channelsNow[i])
	channelsNow = temp
	channelsNow.sort(key=lambda x: int(float(x.getProperty('channel'))))
	return channelsNow


def createManagedChannelsList(resetPosition=True):
	createFakeList()
	intake = createList()
	exisitngPosition = settings.MANAGEDCHANNELSLIST.getSelectedPosition()
	settings.MANAGEDCHANNELSLIST.reset()
	if not intake: return False
	settings.MANAGEDCHANNELSLIST.addItems(intake)

	settings.MANAGEDCHANNELSLIST.selectItem(len(intake) - 1)
	if resetPosition:
		for i in range(len(intake)):
			if not intake[i].getProperty('old'):
				settings.MANAGEDCHANNELSLIST.selectItem(i)
				break
	else:
		settings.MANAGEDCHANNELSLIST.selectItem(exisitngPosition)
	return True

def createChannelsList():
	createFakeList()
	settings.CHANNELSLIST = createList()

def createEventsList():
	settings.EVENTSLIST = createList2()

def programListItem(channel):
	if not settings.CHANNELSLIST:
		createChannelsList()
	program = settings.CHANNELSLIST[int(channel)-1].dataSource

	img = util.getIcon(program.channelName,channel)
	if len(channel) == 1: channel = '0' + str(channel)
	url = authutils.getChanUrl(channel)
	item = xbmcgui.ListItem(program.title, path=url, thumbnailImage=img, iconImage=img)
	item.setArt({'icon':img, 'thumb':img})

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
	return item