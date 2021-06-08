from __future__ import absolute_import, division, unicode_literals
# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon
import os, time
from lib import settings, util
from lib.smoothstreams import schedule, timeutils
from lib import httpserver


def main():
    if xbmc.getInfoLabel('Window(10000).Property(script.smoothstreams-v3.service.started)'):
        # Prevent add-on updates from starting a new version of the addon
        return
    schedule.cleanup()
    if util.getSetting('enable_pvr') == 'true':
        httpserver.http_server(9696)
    if xbmcaddon.Addon().getSetting('kiosk_mode') == 'true':
        xbmc.log('script.smoothstreams-v3: Starting from service (Kiosk Mode)', xbmc.LOGINFO)
        xbmc.executebuiltin('RunScript(script.smoothstreams-v3,SERVICE_START)')
    else:
        util.DEBUG_LOG("time point 0.1")
        settings.init()
        settings.EPGTYPE = util.getSetting('guide_source', 'sports').lower()
        t1 = time.time()
        flag = os.path.join(util.PROFILE, 'serviceOperating')
        with open(flag, 'w') as f_out:
            f_out.write('welp')
        try:
            schedule.Download()
        except:
            util.ERROR('Download Failed')
        try:
            schedule.Schedule().epg(timeutils.startOfDayLocalTimestamp())
        except:
            util.ERROR('Parse Failed')
        os.remove(flag)
        t2 = time.time()
        results = t2 - t1
        util.DEBUG_LOG("Download time is: %s" % results)
        exit()




    # if xbmcaddon.Addon().getSetting('kiosk_mode') == 'true':
    #     xbmc.log('script.smoothstreams-v3: Starting from service (Kiosk Mode)', xbmc.LOGINFO)
    #     xbmc.executebuiltin('RunScript(script.smoothstreams-v3,SERVICE_START)')
    # else:
    #     xbmcgui.Window(10000).setProperty('script.smoothstreams-v3.service.started', '')
    #     exit()


if __name__ == '__main__':
    main()
