#!/usr/bin/env python3

'''
thread module;
'''

from os.path import isdir
from os.path import join
from threading import Thread

from ncmpy import ttplyrics
from ncmpy.config import conf
from ncmpy.util import lrc_basename

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
        fetch local lyrics;
        '''

        basename = lrc_basename(title, artist)
        lyrics_file = join(conf.lyrics_dir, basename)
        try:
            with open(lyrics_file, 'rt') as fp:
                lyrics = fp.read()
        except FileNotFoundError:
            lyrics = None
        return lyrics

    def _fetch_remote(self, artist, title):

        '''
        fetch remote lyrics;
        '''

        return ttplyrics.fetch_lyrics(artist, title)

    def _fetch_default(self, artist, title):

        '''
        fetch default lyrics;
        '''

        return '[00:00.00]No lyrics.'

    def run(self):
        self.itc_cond.acquire()
        while True:
            while not self.itc.get('job-lyrics'):
                self.itc_cond.wait()

            job = self.itc.get('job-lyrics')

            self.itc_cond.release()

            song = job.get('song')
            artist = song.get('artist')
            title = song.get('title')

            lyrics = None
            lyrics = lyrics or self._fetch_local(artist, title)
            lyrics = lyrics or self._fetch_remote(artist, title)
            lyrics = lyrics or self._fetch_default(artist, title)

            self.itc_cond.acquire()

            self.itc['res-lyrics'] = {
                'song': song,
                'lyrics': lyrics,
            }
            self.itc['job-lyrics'] = None

