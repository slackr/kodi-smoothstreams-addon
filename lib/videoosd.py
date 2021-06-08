from __future__ import absolute_import, division, unicode_literals
import re
import time, datetime
import threading
from. import settings
import xbmc
import xbmcgui
from . import kodigui
from .smoothstreams import timeutils, chanutils, skinutils, schedule, authutils, windowutils
from . import util
from .kodijsonrpc import builtin

from .util import T

KEY_MOVE_SET = frozenset(
    (
        xbmcgui.ACTION_MOVE_LEFT,
        xbmcgui.ACTION_MOVE_RIGHT,
        xbmcgui.ACTION_MOVE_UP,
        xbmcgui.ACTION_MOVE_DOWN
    )
)


class SeekDialog(kodigui.BaseDialog, util.CronReceiver):
    xmlFile = 'script-smoothstreams-v3-video_osd.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    MAIN_BUTTON_ID = 100
    SEEK_IMAGE_ID = 200
    POSITION_IMAGE_ID = 201
    SELECTION_INDICATOR = 202
    BIF_IMAGE_ID = 300
    SEEK_IMAGE_WIDTH = 1920

    INFO_BUTTON_ID = 401
    SHUFFLE_BUTTON_ID = 402
    SETTINGS_BUTTON_ID = 403
    PREV_BUTTON_ID = 404
    SKIP_BACK_BUTTON_ID = 405
    PLAY_PAUSE_BUTTON_ID = 406
    STOP_BUTTON_ID = 407
    SKIP_FORWARD_BUTTON_ID = 408
    NEXT_BUTTON_ID = 409
    PLAYLIST_BUTTON_ID = 410
    EVENTS_PLAYLIST_BUTTON_ID = 411
    EPG_BUTTON_ID = 412

    BIG_SEEK_GROUP_ID = 500
    BIG_SEEK_LIST_ID = 501

    NO_OSD_BUTTON_ID = 800

    BAR_X = 0
    BAR_Y = 921
    BAR_RIGHT = 1920
    BAR_BOTTOM = 969

    HIDE_DELAY = 4  # This uses the Cron tick so is +/- 1 second accurate

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.osdHandler = kwargs.get('osdHandler')
        self.live = True
        self.initialVideoSettings = {}
        self.initialAudioStream = None
        self.initialSubtitleStream = None
        self.bifURL = None
        self.baseURL = None
        self.hasBif = True
        self.channel = 0
        self._duration = 0
        self.offset = 0
        self.selectedOffset = 0
        self.bigSeekOffset = 0
        self.title = ''
        self.title2 = ''
        self.fromSeek = 0
        self.initialized = False
        self.playlistDialog = None
        self.eventsplaylistDialog = None
        self.timeout = None
        self.hasDialog = False
        self.lastFocusID = None
        self.playlistDialogVisible = False
        self._delayedSeekThread = None
        self._delayedSeekTimeout = 0
        self.program = self.osdHandler.getProgram()
        self.secsComplete = 0

    @property
    def player(self):
        return self.osdHandler.player

    def resetTimeout(self):
        self.timeout = time.time() + self.HIDE_DELAY

    def trueOffset(self):
        return self.osdHandler.getRatioComplete(self.channel)

    def onFirstInit(self):
        try:
            self._onFirstInit()
        except RuntimeError:
            util.ERROR(hide_tb=True)
            self.started = False

    def _onFirstInit(self):
        settings.CRON.registerReceiver(self)
        self.resetTimeout()
        self.seekbarControl = self.getControl(self.SEEK_IMAGE_ID)
        self.positionControl = self.getControl(self.POSITION_IMAGE_ID)
        self.bifImageControl = self.getControl(self.BIF_IMAGE_ID)
        self.selectionIndicator = self.getControl(self.SELECTION_INDICATOR)
        self.selectionBox = self.getControl(203)
        self.bigSeekControl = kodigui.ManagedControlList(self, self.BIG_SEEK_LIST_ID, 12)
        self.bigSeekGroupControl = self.getControl(self.BIG_SEEK_GROUP_ID)
        self.initialized = True
        self.setBoolProperty('subtitle.downloads', util.getSetting('subtitle_downloads', False))
        self.updateProperties()
        # self.videoSettingsHaveChanged()
        self.started = True
        self.update()

    def onReInit(self):
        chanutils.createChannelsList()
        self.resetTimeout()

        self.updateProperties()
        # self.videoSettingsHaveChanged()
        self.updateProgress()

    def onAction(self, action):
        try:
            self.resetTimeout()

            controlID = self.getFocusId()
            if action.getId() in KEY_MOVE_SET:
                self.setProperty('mouse.mode', '')
                if not controlID:
                    self.setBigSeekShift()
                    self.setFocusId(400)
                    return
            elif action == xbmcgui.ACTION_MOUSE_MOVE:
                if not self.osdVisible():
                    self.showOSD()
                self.setProperty('mouse.mode', '1')

            # if controlID == self.MAIN_BUTTON_ID:
            # 	if action == xbmcgui.ACTION_MOUSE_MOVE:
            # 		return self.seekMouse(action)
            # 	elif action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_STEP_FORWARD):
            # 		return self.seekForward(10000)
            # 	elif action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_STEP_BACK):
            # 		return self.seekBack(10000)
            # elif action == xbmcgui.ACTION_MOVE_DOWN:
            # 	self.updateBigSeek()

            if controlID == self.NO_OSD_BUTTON_ID:
                if not self.live:
                    if action == xbmcgui.ACTION_MOVE_LEFT:
                        xbmc.executebuiltin('Action(StepBack)')
                    if action == xbmcgui.ACTION_MOVE_RIGHT:
                        xbmc.executebuiltin('Action(StepForward)')
                elif action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOUSE_LEFT_CLICK):
                    self.showOSD()
                    self.setFocusId(400)
                elif action in (
                        xbmcgui.ACTION_NEXT_ITEM,
                        xbmcgui.ACTION_PREV_ITEM,
                        xbmcgui.ACTION_BIG_STEP_FORWARD,
                        xbmcgui.ACTION_BIG_STEP_BACK
                ):
                    self.selectedOffset = self.trueOffset()
                    self.setBigSeekShift()
                    self.updateProgress()
                    self.showOSD()
                    self.setFocusId(400)
                # elif action ==xbmcgui.ACTION_SHOW_INFO:
                # 	xbmc.executebuiltin('Action(CodecInfo)')
                # elif action == xbmcgui.ACTION_SHOW_GUI:
                # 	self.showOSD()
                # elif action == xbmcgui.ACTION_SHOW_PLAYLIST:
                # 	self.showPlaylistDialog()
                # elif action == xbmcgui.ACTION_SHOW_VIDEOMENU:
                # 	xbmc.executebuiltin('ActivateWindow(OSDVideoSettings)')
                # elif action == xbmcgui.ACTION_SHOW_AUDIOMENU:
                # 	xbmc.executebuiltin('ActivateWindow(OSDAudioSettings)')
                elif action.getButtonCode() == 258127:
                    xbmc.executebuiltin('Action(PlayerDebug)')
                elif action.getButtonCode() == 61519:
                    # xbmc.executebuiltin('Action(PlayerProcessInfo)')
                    xbmc.executebuiltin('Action(PlayerProcessInfo)')

            # elif controlID == self.BIG_SEEK_LIST_ID:
            # 	if action in (xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_BIG_STEP_FORWARD):
            # 		return self.updateBigSeek()
            # 	elif action in (xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_BIG_STEP_BACK):
            # 		return self.updateBigSeek()

            if action.getButtonCode() == 61516:
                builtin.Action('CycleSubtitle')
            elif action.getButtonCode() == 61524:
                builtin.Action('ShowSubtitles')
            elif action == xbmcgui.ACTION_NEXT_ITEM or action == xbmcgui.ACTION_PAGE_UP:
                self.osdHandler.next()
                self.setBigSeekShift()
                self.update()
            elif action == xbmcgui.ACTION_PREV_ITEM or action == xbmcgui.ACTION_PAGE_DOWN:
                self.osdHandler.prev()
                self.setBigSeekShift()
                self.update()
            elif action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_STOP):
                if self.osdVisible():
                    self.hideOSD()
                else:
                    self.doClose()
                    self.osdHandler.player.stop()
                return
            if self.checkChannelEntry(action):
                return
        except:
            util.ERROR()

        kodigui.BaseDialog.onAction(self, action)

    def onFocus(self, controlID):
        return

    def onClick(self, controlID):
        if controlID == self.MAIN_BUTTON_ID:
            # todo remove seek
            self.osdHandler.seek(self.selectedOffset)
        elif controlID == self.NO_OSD_BUTTON_ID:
            self.showOSD()
        # elif controlID == self.SETTINGS_BUTTON_ID:
        # 	self.handleDialog(self.showSettings)
        elif controlID == self.INFO_BUTTON_ID:
            xbmc.executebuiltin('Action(PlayerProcessInfo)')
        elif controlID == self.SHUFFLE_BUTTON_ID:
            self.osdHandler.previousChannel()
        elif controlID == self.PREV_BUTTON_ID:
            self.osdHandler.prev()
        elif controlID == self.STOP_BUTTON_ID:
            self.hideOSD()
            self.doClose()
            self.osdHandler.player.stop()
        elif controlID == self.NEXT_BUTTON_ID:
            self.osdHandler.next()
        elif controlID == self.EPG_BUTTON_ID:
            self.showEpgDialog()
        elif controlID == self.PLAYLIST_BUTTON_ID:
            self.showPlaylistDialog()
        elif controlID == self.EVENTS_PLAYLIST_BUTTON_ID:
            self.showEventsPlaylistDialog()
        elif controlID == self.SETTINGS_BUTTON_ID:
            self.handleDialog(self.optionsButtonClicked)
        elif controlID == self.BIG_SEEK_LIST_ID:
            self.bigSeekSelected()
        elif controlID == self.SKIP_BACK_BUTTON_ID:
            self.skipBack()
        elif controlID == self.SKIP_FORWARD_BUTTON_ID:
            self.skipForward()

    # elif controlID == self.INFO_BUTTON_ID:
    # 	xbmc.executebuiltin('Action(CodecInfo)')

    def doClose(self, delete=False):
        # add to hear about leaving playing
        try:
            if self.playlistDialog:
                self.playlistDialog.doClose()
                if delete:
                    del self.playlistDialog
                    self.playlistDialog = None
                    util.garbageCollect()
        finally:
            settings.CRON.cancelReceiver(self)
            kodigui.BaseDialog.doClose(self)

    def doChannelEntry(self, digit):
        window = windowutils.KodiChannelEntry('script-smoothstreams-v3-channel_entry.xml',
                                              util.ADDON.getAddonInfo('path'), 'Main', '1080i', viewManager=self,
                                              digit=digit)
        window.doModal()
        ret = None
        if window.set:
            ret = window.digits
        del window
        return ret

    def checkChannelEntry(self, action):
        if action.getId() >= xbmcgui.REMOTE_0 and action.getId() <= xbmcgui.REMOTE_9:
            targetChannel = self.doChannelEntry(str(action.getId() - 58))
            return True
        return False

    def skipForward(self):
        return

    def skipBack(self):
        return

    def delayedSeek(self):
        return

    def _delayedSeek(self):
        return

    def handleDialog(self, func):
        self.hasDialog = True

        try:
            func()
        finally:
            self.resetTimeout()
            self.hasDialog = False

    def videoSettingsHaveChanged(self):
        changed = False
        return changed

    def repeatButtonClicked(self):
        return

    def shuffleButtonClicked(self):
        return

    def optionsButtonClicked(self):  # Button currently commented out.
        # pass
        from . import dropdown
        options = []

        options.append({'key': 'sstv', 'display': 'SSTV Options'})
        options.append({'key': 'kodi_video', 'display': 'Video Options'})
        options.append({'key': 'kodi_audio', 'display': 'Audio Options'})

        choice = dropdown.showDropdown(options, (600, 1060), close_direction='down', pos_is_bottom=True,
                                       close_on_playback_ended=True)

        if not choice:
            return

        if choice['key'] == 'kodi_video':
            xbmc.executebuiltin('ActivateWindow(OSDVideoSettings)')
        elif choice['key'] == 'kodi_audio':
            xbmc.executebuiltin('ActivateWindow(OSDAudioSettings)')
        elif choice['key'] == 'sstv':
            self.showSettings()

    def subtitleButtonClicked(self):
        return

    def showSettings(self):
        stream = util.getSetting('server_type')
        qual = util.getSetting('high_def')
        region = util.getSetting('server_region', 'North America')
        server = authutils.servers['NA Mix']
        try:
            if region == 'North America':
                server = authutils.servers[util.getSetting('server_r0', 'NA Mix')]
            elif region == 'Europe':
                server = authutils.servers[util.getSetting('server_r1', 'Euro Mix')]
            elif region == 'Asia':
                server = authutils.servers[util.getSetting('server_r2', 'Asia Mix')]
        except:
            # unknown server detected, using NA mix
            util.setSetting('server_region', 'North America')
            util.setSetting('server_r0', 'NA Mix')
            util.setSetting('server_r1', 'Euro Mix')
            util.setSetting('server_r2', 'Asia Mix')
            pass

        util.openSettings()
        skinutils.setColours()
        new_region = util.getSetting('server_region', 'North America')
        new_server = authutils.servers['NA Mix']
        try:
            if new_region == 'North America':
                new_server = authutils.servers[util.getSetting('server_r0', 'NA Mix')]
            elif new_region == 'Europe':
                new_server = authutils.servers[util.getSetting('server_r1', 'Euro Mix')]
            elif new_region == 'Asia':
                new_server = authutils.servers[util.getSetting('server_r2', 'Asia Mix')]
        except:
            pass
        if stream != util.getSetting('server_type') or qual != util.getSetting(
                'high_def') or region != new_region or server != new_server:
            self.osdHandler.restartChannel()
        return

    def setBigSeekShift(self):
        closest = None
        for mli in self.bigSeekControl:
            if mli.dataSource > self.osdHandler.getRatioComplete(self.channel):
                break
            closest = mli
        if not closest:
            return

        self.bigSeekOffset = self.osdHandler.getRatioComplete(self.channel) - closest.dataSource
        pxOffset = int(
            self.osdHandler.getRatioComplete(self.channel) / float(self.osdHandler.getDuration(self.channel)) * 1920)
        self.bigSeekGroupControl.setPosition(-8 + pxOffset, 917)
        self.bigSeekControl.selectItem(closest.pos())

    # xbmc.sleep(100)

    def updateBigSeek(self):
        return

    def bigSeekSelected(self):
        return

    # self.setFocusId(self.MAIN_BUTTON_ID)

    def updateProperties(self, **kwargs):
        if not self.started:
            return

        if self.fromSeek:
            # self.setFocusId(self.MAIN_BUTTON_ID)
            self.fromSeek = 0

        self.setProperty('has.bif', True and '1' or '')
        self.setProperty('video.title', self.title)
        self.setProperty('video.title2', self.title2)
        self.setProperty('is.show', False and '1' or '')
        self.setProperty('time.left', util.timeDisplay(
            int(self.osdHandler.getDuration(self.channel)) - self.osdHandler.getRatioComplete(self.channel)))

        self.updateCurrent()
        # I think this is the coloured bar
        div = int((self.osdHandler.getDuration(self.channel)) / 12)
        items = []
        for x in range(12):
            offset = div * x
            items.append(kodigui.ManagedListItem(data_source=offset))
        self.bigSeekControl.reset()
        self.bigSeekControl.addItems(items)

    def updateCurrent(self):

        ratio = self.osdHandler.getRatioComplete(self.channel) / float(self.osdHandler.getDuration(self.channel))
        w = int(ratio * self.SEEK_IMAGE_WIDTH)
        self.selectionIndicator.setPosition(w, 896)
        self.positionControl.setWidth(w)
        # to = self.trueOffset()
        self.updateProgress()
        prog = settings.CHANNELSLIST[settings.CURCHAN - 1].dataSource
        self.setProperty('PlotOutline', prog.description)
        self.setProperty('Title', prog.title)
        self.setProperty('Genre', prog.category)
        self.setProperty('Fake', prog.fake)
        self.setProperty('StartTime', timeutils.secs2stringLocal_time(prog.start))
        self.setProperty('EndTime', timeutils.secs2stringLocal_time(prog.stop))
        self.setProperty('Duration', timeutils.secs2stringLocal_dur(prog.duration))
        self.setProperty('time.left', timeutils.secs2stringLocal_dur(
            int(self.osdHandler.getDuration(self.channel)) - self.osdHandler.getRatioComplete(self.channel)))
        self.setProperty('time.end', timeutils.secs2stringLocal(self.program.stop))
        self.setProperty('ChannelName', prog.channelName)
        self.setProperty('ChannelNumber', prog.channel_number)
        # self.setProperty('Genre', prog.)
        self.setProperty('time.current', timeutils.secs2stringLocal(timeutils.timeInDayLocalSeconds()))

    def seekForward(self, offset):
        return

    def seekBack(self, offset):
        return

    def seekMouse(self, action):
        return

    def setup(self, duration, channel=0, bif_url=None, title='', title2='', program='', live=True):
        self.title = title
        self.title2 = title2
        self.setProperty('video.title', title)
        self.setProperty('is.show', True and '1' or '')
        self.setProperty('has.playlist', self.osdHandler.playlist and '1' or '')
        self.setProperty('shuffled', (self.osdHandler.playlist) and '1' or '')
        self.channel = channel
        self.offset = 0
        self.live = live
        self._duration = duration
        self.setProperty('bif.image', bif_url if bif_url else self.osdHandler.getIcon(self.program.channelName,
                                                                                      self.program.channel_number))
        self.bifURL = bif_url
        self.hasBif = True
        if self.hasBif:
            self.baseURL = re.sub('/\d+\?', '/{0}?', self.bifURL)
        self.update()
        self.program = program

    def update(self, offset=None, from_seek=False):
        self.updateProgress()

    @property
    def duration(self):
        try:
            return self._duration or int(self.osdHandler.player.getTotalTime() * 1000)
        except RuntimeError:  # Not playing
            return 1

    def updateProgress(self):
        if not self.started:
            self.onFirstInit()

        ratio = self.osdHandler.getRatioComplete(self.channel) / float(self.osdHandler.getDuration(self.channel))
        w = int(ratio * self.SEEK_IMAGE_WIDTH)

        # seek time label
        self.selectionIndicator.setPosition(w, 896)
        if w < 51:
            self.selectionBox.setPosition(-50 + (50 - w), 0)
        elif w > 1869:
            self.selectionBox.setPosition(-100 + (1920 - w), 0)
        else:
            self.selectionBox.setPosition(-50, 0)
        self.setProperty('time.selection',
                         timeutils.secs2stringLocal_time(self.osdHandler.getRatioComplete(self.channel)))

        # todo
        self.setProperty('time.left', timeutils.secs2stringLocal_dur(
            self.osdHandler.getDuration(self.channel) - self.osdHandler.getRatioComplete(self.channel)))
        self.bifImageControl.setPosition(1200, 25)
        self.bigSeekControl.setPosition(0, 0)
        self.getControl(302).setPosition(0, 965)

        # seek bar length (done as width)
        self.seekbarControl.setWidth(w)
        self.seekbarControl.setPosition(0, 1)

    def tick(self, offset=None):
        if not self.initialized:
            return

        if time.time() > self.timeout and not self.hasDialog:
            if not xbmc.getCondVisibility('Window.IsActive(videoosd)') and not self.playlistDialogVisible:
                self.hideOSD()

        self.updateCurrent()

    def showPlaylistDialog(self):
        if self.playlistDialog:
            self.playlistDialog.doClose()
            self.playlistDialogVisible = False
        if not self.playlistDialog:
            self.playlistDialog = PlaylistDialog('script-smoothstreams-v3-video_double_playlist.xml',
                                                 util.ADDON.getAddonInfo('path'), 'Main', '1080i', show=True,
                                                 osdHandler=self.osdHandler, source='channels')

        self.playlistDialogVisible = True
        self.playlistDialog.doModal()
        self.resetTimeout()
        self.playlistDialogVisible = False

    def showEventsPlaylistDialog(self):
        if self.playlistDialog:
            self.playlistDialog.doClose()
            self.playlistDialogVisible = False
        if not self.eventsplaylistDialog:
            self.eventsplaylistDialog = PlaylistDialog('script-smoothstreams-v3-video_current_playlist.xml',
                                                       util.ADDON.getAddonInfo('path'), 'Main', '1080i', show=True,
                                                       osdHandler=self.osdHandler, source='events')

        self.eventsplaylistDialogVisible = True
        self.eventsplaylistDialog.doModal()
        self.resetTimeout()
        self.eventsplaylistDialogVisible = False

    def showEpgDialog(self):
        from . import osdepg
        self.window = osdepg.KodiEPGDialog.create(osdHandler=self.osdHandler, viewManager=self.osdHandler.viewManager)
        self.window.doModal()
        self.window.onClosed()
        del self.window
        self.window = None

    def osdVisible(self):
        return xbmc.getCondVisibility('Control.IsVisible(801)')

    def showOSD(self):
        self.setProperty('show.OSD', '1')
        xbmc.executebuiltin('Dialog.Close(videoosd,true)')
        # if xbmc.getCondVisibility('Player.showinfo'):
        # 	xbmc.executebuiltin('Action(Info)')
        # chanutils.createChannelsList()
        self.setFocusId(self.STOP_BUTTON_ID)

    def hideOSD(self):
        self.setProperty('show.OSD', '')
        self.setFocusId(self.NO_OSD_BUTTON_ID)
        if self.playlistDialog:
            self.playlistDialog.doClose()
            self.playlistDialogVisible = False
        if self.playlistDialog:
            self.playlistDialog.doClose()
            self.playlistDialogVisible = False


class PlaylistDialog(kodigui.BaseDialog, util.CronReceiver):
    width = 1920
    height = 1080

    LI_AR16X9_THUMB_DIM = (178, 100)
    LI_SQUARE_THUMB_DIM = (100, 100)

    PLAYLIST_LIST_ID = 101

    def __init__(self, *args, **kwargs):
        kodigui.BaseDialog.__init__(self, *args, **kwargs)
        self.osdHandler = kwargs.get('osdHandler')
        self.source = kwargs.get('source')
        self.selChan = 1

        if self.source == 'channels':
            if not settings.CHANNELSLIST:
                from .smoothstreams import chanutils
                chanutils.createChannelsList()
            self.playlist = settings.CHANNELSLIST
        else:
            if not settings.EVENTSLIST:
                from .smoothstreams import chanutils
                chanutils.createEventsList()
            self.playlist = settings.EVENTSLIST

    def onAction(self, action):
        try:
            controlID = self.getFocusId()
            if self.source == 'channels':
                if controlID == 101 and (action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_DOWN):
                    self.showList2(ch=str(self.getSelectedChannel()['ID']))
                elif controlID == 101 and (action == xbmcgui.ACTION_MOUSE_MOVE):
                    try:
                        id = int(self.getSelectedChannel()['ID'])
                        if id != self.selChan:
                            self.selChan = id
                            self.showList2(ch=str(id))
                    except:
                        a = 1
        except Exception as e:
            util.ERROR(str(e))
            kodigui.BaseDialog.onAction(self, action)
            return
        kodigui.BaseDialog.onAction(self, action)

    def onFirstInit(self):
        self.playlistListControl = kodigui.ManagedControlList(self, self.PLAYLIST_LIST_ID, 6)
        if self.source == 'channels': self.programsList = kodigui.ManagedControlList(self, 102, 11)
        self.fillPlaylist()
        self.updatePlayingItem()
        self.setFocusId(self.PLAYLIST_LIST_ID)
        settings.CRON.registerReceiver(self)
        if self.source == 'channels': self.showList2()

    def onClick(self, controlID):
        if controlID == self.PLAYLIST_LIST_ID:
            self.playlistListClicked()
        else:
            settings.CRON.cancelReceiver(self)
            self.doClose()

    def minute(self):
        if self.source == 'channels':
            chanutils.createChannelsList()
            self.playlist = settings.CHANNELSLIST
        else:
            chanutils.createEventsList()
            self.playlist = settings.EVENTSLIST
        self.fillPlaylist(False)
        self.updatePlayingItem()

    def playlistListClicked(self):
        mli = self.playlistListControl.getSelectedItem()
        if not mli:
            return
        self.osdHandler.goToChannel(mli.dataSource.channel_number)
        self.updatePlayingItem()

    def sessionEnded(self, **kwargs):
        util.DEBUG_LOG('Video OSD: Session ended - closing')
        self.doClose()

    def createListItem(self, pi):
        if pi.type == 'episode':
            return self.createEpisodeListItem(pi)
        elif pi.type in ('movie', 'clip'):
            return self.createMovieListItem(pi)

    def createEpisodeListItem(self, episode):
        mli = kodigui.ManagedListItem(episode.title, label2,
                                      thumbnailImage=episode.thumb.asTranscodedImageURL(*self.LI_AR16X9_THUMB_DIM),
                                      data_source=episode)
        mli.setProperty('track.duration', util.durationToShortText(episode.duration.asInt()))
        mli.setProperty('video', '1')
        mli.setProperty('watched', episode.isWatched and '1' or '')
        return mli

    def createMovieListItem(self, movie):
        localTZ = timeutils.LOCAL_TIMEZONE
        nowDT = timeutils.nowUTC()

        sDT = datetime.datetime.fromtimestamp(movie.start, tz=localTZ)
        eDT = datetime.datetime.fromtimestamp(movie.stop, tz=localTZ)

        if 'SSChannel' in str(type(movie)):
            mli = kodigui.ManagedListItem(movie['display-name'], '',
                                          thumbnailImage=self.osdHandler.getIcon(movie['display-name'], movie['ID']),
                                          data_source=movie)
            mli.setProperty('track.duration', str(''))
            mli.setProperty('ID', int(movie['ID']))
        else:
            if sDT.day == nowDT.day:
                startDisp = datetime.datetime.strftime(sDT, util.TIME_DISPLAY)
            else:
                startDisp = datetime.datetime.strftime(sDT, '%a {0}'.format(util.TIME_DISPLAY))
            if eDT.day == nowDT.day:
                endDisp = datetime.datetime.strftime(eDT, util.TIME_DISPLAY)
            else:
                endDisp = datetime.datetime.strftime(eDT, '%a {0}'.format(util.TIME_DISPLAY))
            mli = kodigui.ManagedListItem(movie.title, movie.description,
                                          thumbnailImage=self.osdHandler.getIcon(movie.channelName,
                                                                                 movie.channel_number),
                                          data_source=movie)
            mli.setProperty('track.duration', str(startDisp + " - " + endDisp))
            mli.setProperty('ID', movie.channel_number)
        mli.setProperty('video', '1')
        mli.setProperty('watched', False and '1' or '')
        return mli

    def playQueueCallback(self, **kwargs):
        mli = self.playlistListControl.getSelectedItem()
        pi = mli.dataSource
        ID = pi['comment'].split(':', 1)[0]
        viewPos = self.playlistListControl.getViewPosition()

        self.fillPlaylist()

        for ni in self.playlistListControl:
            if ni.dataSource['comment'].split(':', 1)[0] == ID:
                self.playlistListControl.selectItem(ni.pos())
                break

        xbmc.sleep(100)

        newViewPos = self.playlistListControl.getViewPosition()
        if viewPos != newViewPos:
            diff = newViewPos - viewPos
            self.playlistListControl.shiftView(diff, True)

    def updatePlayingItem(self):
        playing = settings.CURCHAN
        for mli in self.playlistListControl.items:
            if 'SSChannel' in str(type(mli.dataSource)):
                mli.setProperty('playing', int(mli.dataSource['ID']) == playing and '1' or '')
                if mli.dataSource['ID'] == int(settings.CURCHAN):
                    self.playlistListControl.selectItem(mli)
            else:
                mli.setProperty('playing', int(mli.dataSource.channel_number) == int(playing) and '1' or '')
                if mli.dataSource.channel_number == int(settings.CURCHAN):
                    self.playlistListControl.selectItem(mli)

    def fillPlaylist(self, reset=True):
        exisitngPosition = self.playlistListControl.getSelectedPosition()
        items = []
        for i in self.playlist:
            ds = i.dataSource
            mli = self.createMovieListItem(ds)
            items.append(mli)

        self.playlistListControl.reset()
        self.playlistListControl.addItems(items)
        if reset:
            self.playlistListControl.selectItem(int(settings.CURCHAN) - 1)
        else:
            self.playlistListControl.selectItem(exisitngPosition)

    def showList2(self, resetPosition=True, ch='1'):

        oldItems = []
        items = []
        channelsNow = {}
        self.progressItems2 = []
        timeInDay = timeutils.timeInDayLocalSeconds() / 60
        startOfDay = timeutils.startOfDayLocalTimestamp()

        for channel in settings.CHANNELS:
            if channel['ID'] != ch: continue
            elem = {
                'channel': str(channel['ID']),
                'name': str(channel['display-name']),
                'time': startOfDay,
                'runtime': 3600 * 48,
                'version': '',
                'channelParent': channel,
                '_ssType': 'PROGRAM'
            }
            program = schedule.SSProgram('1', elem, 'No Category', startOfDay, [], str(channel['ID']))

            fakeItem = kodigui.ManagedListItem(channel['display-name'], '', iconImage=channel['logo'],
                                               data_source=program)
            color = schedule.SPORTS_TABLE.get('no category', {}).get('color', '808080')

            fakeItem.setProperty('flag', '')
            fakeItem.setProperty('channel', str(channel['ID']))

            channelsNow[str(channel['ID'])] = []

            if not 'programs' in channel: continue
            channel['programs'].sort(key=lambda x: int(x.start))
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
        mli = self.playlistListControl.getSelectedItem()
        if not mli:
            return
        if 'SSChannel' in str(type(mli.dataSource)): return mli.dataSource
        return mli.dataSource.channelParent
