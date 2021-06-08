# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals
from . import viewmanager
from .smoothstreams import player

def main():
    # if epg.versionCheck(): return
    viewmanager.ViewManager()

def impatient(chan):
    try:
        playr = player.OSDHandler(impatient=True)
        playr.play(chan)
    finally:
        viewmanager.ViewManager()