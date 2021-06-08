from __future__ import absolute_import, division, unicode_literals
#  contains global variables for use in the addon
def init():
    global CHANNELSLIST, EVENTSLIST, MANAGEDCHANNELSLIST, SCHEDULE, CHANNELS, SCHEDULE1, EVENTS_CHANNELS, CRON, JSON, PREVCHAN, CURCHAN, BACKGROUND, TOKEN, PLAYER, EPGTYPE, CHANAPI
    CHANNELSLIST = None
    EVENTSLIST = None
    MANAGEDCHANNELSLIST = None
    SCHEDULE = None
    CHANNELS = None
    SCHEDULE1 = None
    EVENTS_CHANNELS = None
    CRON = None
    JSON = {'sports' : None, 'full' : None, 'alt' : None}
    PREVCHAN = 1
    CURCHAN = 1
    BACKGROUND = None
    TOKEN = {'hash':None,'expires':None}
    PLAYER = None
    EPGTYPE = 'sports'
    CHANAPI = None