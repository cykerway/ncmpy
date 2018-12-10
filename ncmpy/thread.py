#!/usr/bin/env python3

'''
thread module;
'''

from threading import Thread
from os.path import isdir

from ncmpy import ttplyrics
from ncmpy.config import conf

class LyricsThread(Thread):

    '''
    thread fetching lyrics;
    '''

    def __init__(self, ctrl):
        super().__init__()

        self.ctrl = ctrl
        self.itc = self.ctrl.itc
        self.itc_cond = self.ctrl.itc_cond

        ##  daemonize;
        self.daemon = True

    def _fetch_local(self, artist, title):

        '''
        fetch lyrics from local;
        '''

        ##  todo
        return None

    def _fetch_remote(self, artist, title):

        '''
        fetch lyrics from remote;
        '''

        return ttplyrics.fetch_lyrics(artist, title)

    def _fetch_none(self, artist, title):

        '''
        fetch lyrics from nowhere;
        '''

        return '[00:00.00]No lyrics.'

    def run(self):
        self.itc_cond.acquire()
        while True:
            while not self.itc.get('job-lyrics'):
                self.itc_cond.wait()

            job = self.itc.get('job-lyrics')
            song = job.get('song')
            artist = song.get('artist')
            title = song.get('title')

            ##  todo: fetch in background;
            lyrics = None
            lyrics = lyrics or self._fetch_local(artist, title)
            lyrics = lyrics or self._fetch_remote(artist, title)
            lyrics = lyrics or self._fetch_none(artist, title)

            self.itc['res-lyrics'] = {
                'song': song,
                'lyrics': lyrics,
            }
            self.itc['job-lyrics'] = None

#        while True:
#
#            self._lyrics = '[00:00.00]Cannot fetch lyrics (No artist/title).'
#            self._lyrics_state = 'local'
#
#            # fetch lyrics if required information is provided
#            if self._artist and self._title:
#                # try to fetch from local lrc
#                lyrics_file = os.path.join(self._lyrics_dir, self._artist.replace('/', '_') + \
#                        '-' + self._title.replace('/', '_') + '.lrc')
#                if os.path.isfile(lyrics_file):
#                    with open(lyrics_file, 'rt') as f:
#                        self._lyrics = f.read()
#                    # inform round1: lyrics has been fetched
#                    self._lyrics_state = 'local'
#                # if local lrc doesn't exist, fetch from Internet
#                else:
#                    self._lyrics = ttplyrics.fetch_lyrics(self._transtag(self._artist), \
#                            self._transtag(self._title))
#                    # inform round1: lyrics has been fetched
#                    self._lyrics_state = 'net'
#            self._osong = self._nsong

#    def _transtag(self, tag):
#        '''Transform tag into format used by lrc engine.'''
#
#        if tag is None:
#            return None
#        else:
#            return tag.replace(' ', '').lower()

