#!/usr/bin/env python3
#
# ncmpy - A curses-based MPD client written in Python.
#
# Copyright (C) 2011-2015 Cyker Way
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
main module;
'''

import curses
import locale
import mpd
import os
import select
import signal
import sys
import time

from ncmpy.config import *
from ncmpy.pane import *
from ncmpy.util import *

class Ncmpy():
    '''Main controller.'''

    def _init_curses(self):
        self.stdscr = curses.initscr()
        curses.start_color()
        curses.use_default_colors()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLUE, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        self.stdscr.keypad(1)
        self.stdscr.leaveok(1)
        # Force a refresh. Otherwise strange things happen on first key press.
        self.stdscr.refresh()

    def _init_mpd(self, host, port):
        self.mpc = mpd.MPDClient()
        self.mpc.connect(host, port)

    def _init_conf(self):
        '''Initialize internal configurations.'''

        # Main configuration.
        self.height, self.width = self.stdscr.getmaxyx()
        self.tpanename = 'Queue'
        self.loop = False
        self.idle = False
        self.seek = False
        self.sync = True
        self.elapsed = 0
        self.total = 0
        self.search = ''
        self.search_di = 0
        self.pending = []

        # No sync keys. These keys don't modify MPD server state and can be handled locally.
        # Therefore we don't sync with MPD server when handling these keys.
        self.nsks = [
                ord('j'), ord('k'), ord('f'), ord('b'),
                ord('H'), ord('M'), ord('L'), ord('g'), ord('G'),
                ord('J'), ord('K'),
                curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT,
                ]

        # User input.
        self.c = None

    def _init_data(self):
        self.status = self.mpc.status()
        self.stats = self.mpc.stats()
        self.currentsong = self.mpc.currentsong()

    def _init_board(self):
        self.board = {}

    def _init_panes(self):
        '''Initialize panes.'''

        self.m = MenuPane(self.stdscr.subwin(1, self.width, 0, 0), self)
        self.t = LinePane(self.stdscr.subwin(1, self.width, 1, 0), self)

        self.p = ProgressPane(self.stdscr.subwin(1, self.width, self.height - 2, 0), self)
        self.s = StatusPane(self.stdscr.subwin(1, self.width, self.height - 1, 0), self)
        self.e = MessagePane(self.stdscr.subwin(1, self.width, self.height - 1, 0), self)

        self.h = HelpPane(curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.q = QueuePane(curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.d = DatabasePane(curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.l = LyricsPane(curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.a = ArtistAlbumPane(curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.r = SearchPane(curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.i = InfoPane(curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.o = OutputPane(curses.newwin(self.height - 4, self.width, 2, 0), self)

        # Pane dict.
        self.pdict = {
                'Menu' : self.m,
                'Title' : self.t,
                'Progress' : self.p,
                'Status' : self.s,
                'Message' : self.e,

                'Help' : self.h,
                'Queue' : self.q,
                'Database' : self.d,
                'Lyrics' : self.l,
                'Artist-Album' : self.a,
                'Search' : self.r,
                'Info' : self.i,
                'Output' : self.o,
                }
        # Pane list.
        self.plist = self.pdict.values()

        # Bar pane dict.
        self.bpdict = {
                'Menu' : self.m,
                'Title' : self.t,
                'Progress' : self.p,
                'Status' : self.s,
                'Message' : self.e,
                }
        # Bar pane list.
        self.bplist = self.bpdict.values()

    def __enter__(self):
        self._init_curses()
        self._init_mpd(conf.mpd_host, conf.mpd_port)
        self._init_conf()
        self._init_data()
        self._init_board()
        self._init_panes()

        # start lyrics daemon thread
        self.l.daemon = True
        self.l.start()

        # initial update
        self.process('timeout')

        return self

    def __exit__(self, type, value, traceback):

        curses.endwin()

    def update_data(self):
        # Update data from MPD.
        self.status = self.mpc.status()
        self.stats = self.mpc.stats()
        self.currentsong = self.mpc.currentsong()

        # Update panes data.
        for pane in self.plist:
            pane.update_data()

    def round1(self, c):
        # Seeking.
        if c in (curses.KEY_LEFT, curses.KEY_RIGHT, curses.KEY_DOWN, curses.KEY_UP):
            if self.status['state'] in ['play', 'pause']:
                if not self.seek:
                    self.seek = True
                    self.elapsed, self.total = [int(i) for i in self.status['time'].split(':')]
                if c == curses.KEY_LEFT:
                    self.elapsed = max(self.elapsed - 1, 0)
                elif c == curses.KEY_RIGHT:
                    self.elapsed = min(self.elapsed + 1, self.total)
                elif c == curses.KEY_DOWN:
                    self.elapsed = max(self.elapsed - max(self.total // 100, 1), 0)
                elif c == curses.KEY_UP:
                    self.elapsed = min(self.elapsed + max(self.total // 100, 1), self.total)
                self.status['time'] = '{}:{}'.format(self.elapsed, self.total)
        else:
            if self.seek:
                if self.status['state'] in ['play', 'pause']:
                    self.mpc.seekid(self.status['songid'], self.elapsed)
                self.seek = False
                self.status['time'] = '{}:{}'.format(self.elapsed, self.total)

        # Volume control.
        if c == ord('9'):
            new_vol = max(int(self.status['volume']) - 1, 0)
            try:
                self.mpc.setvol(new_vol)
                self.status['volume'] = str(new_vol)
            except mpd.CommandError as e:
                self.board['msg'] = str(e)
        elif c == ord('0'):
            new_vol = min(int(self.status['volume']) + 1, 100)
            try:
                self.mpc.setvol(new_vol)
                self.status['volume'] = str(new_vol)
            except mpd.CommandError as e:
                self.board['msg'] = str(e)

        # Playback control.
        elif c == ord(' '):
            self.mpc.pause()
        elif c == ord('s'):
            self.mpc.stop()
        elif c == ord('<'):
            self.mpc.previous()
        elif c == ord('>'):
            self.mpc.next()

        # Mode control.
        elif c == ord('u'):
            self.status['consume'] = 1 - int(self.status['consume'])
            self.mpc.consume(self.status['consume'])
        elif c == ord('i'):
            self.status['random'] = 1 - int(self.status['random'])
            self.mpc.random(self.status['random'])
        elif c == ord('o'):
            self.status['repeat'] = 1 - int(self.status['repeat'])
            self.mpc.repeat(self.status['repeat'])
        elif c == ord('p'):
            self.status['single'] = 1 - int(self.status['single'])
            self.mpc.single(self.status['single'])

        # Playlist save/load.
        elif c == ord('S'):
            name = self.e.getstr('Save')
            try:
                self.mpc.save(name)
            except mpd.CommandError as e:
                self.board['msg'] = str(e).rsplit('} ')[1]
            else:
                self.board['msg'] = 'Playlist {} saved'.format(name)
                self.board['playlist'] = 'saved'
        elif c == ord('O'):
            name = self.e.getstr('Load')
            try:
                self.mpc.load(name)
            except mpd.CommandError as e:
                self.board['msg'] = str(e).rsplit('} ')[1]
            else:
                self.board['msg'] = 'Playlist {} loaded'.format(name)

        # Basic search.
        elif c in [ord('/'), ord('?')]:
            search = self.e.getstr('Find')
            if search:
                self.search = search
                if c == ord('/'):
                    self.search_di = 1
                elif c == ord('?'):
                    self.search_di = -1

        # Top pane do round1 with input char.
        self.pdict[self.tpanename].round1(c)

        # Other panes do round1 without input char.
        for panename in self.pdict:
            if panename != self.tpanename:
                self.pdict[panename].round1(-1)

        # Pane switch.
        if c == curses.KEY_F1:
            self.prevtpanename = self.tpanename
            self.tpanename = 'Help'
        elif c == curses.KEY_F2:
            self.prevtpanename = self.tpanename
            self.tpanename = 'Queue'
        elif c == curses.KEY_F3:
            self.prevtpanename = self.tpanename
            self.tpanename = 'Database'
        elif c == curses.KEY_F4:
            self.prevtpanename = self.tpanename
            self.tpanename = 'Lyrics'
        elif c == curses.KEY_F5:
            self.prevtpanename = self.tpanename
            self.tpanename = 'Artist-Album'
        elif c == curses.KEY_F6:
            self.prevtpanename = self.tpanename
            self.tpanename = 'Search'
        elif c == curses.KEY_F7:
            if self.tpanename == 'Info':
                if self.prevtpanename:
                    self.tpanename, self.prevtpanename = self.prevtpanename, self.tpanename
            else:
                self.prevtpanename = self.tpanename
                self.tpanename = 'Info'
        elif c == curses.KEY_F8:
            self.prevtpanename = self.tpanename
            self.tpanename = 'Output'

    def round2(self):
        if ('database-locate' in self.board):
            self.tpanename = 'Database'

        if ('queue-locate' in self.board):
            self.tpanename = 'Queue'

        for pane in self.plist:
            pane.round2()

    def update_win(self):
        self.pdict[self.tpanename].update_win()

        for pane in self.bplist:
            pane.update_win()

        curses.doupdate()

    def enter_idle(self):
        '''
        Enter idle state. Must be called outside idle state.

        No return value.
        '''

        self.mpc.send_idle()
        self.idle = True

    def leave_idle(self):
        '''
        Leave idle state. Must be called inside idle state.

        Return Value: Events received in idle state.
        '''

        self.mpc.noidle()
        self.idle = False

        try:
            return self.mpc.fetch_idle()
        except mpd.PendingCommandError:
            # Return None if nothing received.
            return None

    def try_enter_idle(self):
        if not self.idle:
            self.enter_idle()

    def try_leave_idle(self):
        if self.idle:
            return self.leave_idle()

    def process(self, fd):
        '''Process timeout/mpd/stdin events. Called in main loop.'''

        # Get input if event is 'stdin'.
        if fd == 'stdin':
            c = self.c = self.stdscr.getch()
            if c == ord('q'):
                self.loop = False
                return
            elif c in self.nsks:
                self.sync = False
            else:
                self.sync = True
        else:
            c = self.c = -1
            self.sync = True

        self.board.clear()

        if self.sync:
            events = self.try_leave_idle()

            if events and 'database' in events:
                self.board['database-updated'] = None

            if self.pending:
                self.mpc.command_list_ok_begin()
                for task in self.pending:
                    exec('self.mpc.' + task)
                self.mpc.command_list_end()
                self.pending = []

            self.update_data()

        self.round1(c)
        self.round2()
        self.update_win()

        if fd == 'stdin':
            curses.flushinp()
        else:
            self.try_enter_idle()

    def resize_win(self):
        '''Reset display. Called in SIGWINCH handler.'''

        curses.endwin()
        self.stdscr.refresh()
        self.height, self.width = self.stdscr.getmaxyx()

        for pane in self.plist:
            pane.resize_win()

    def main_loop(self):
        '''Main loop.'''

        poll = select.poll()
        poll.register(self.mpc.fileno(), select.POLLIN)
        poll.register(sys.stdin.fileno(), select.POLLIN)

        self.loop = True
        while self.loop:
            try:
                responses = poll.poll(200)
                if not responses:
                    self.process('timeout')
                else:
                    for fd, event in responses:
                        if fd == self.mpc.fileno() and event & select.POLLIN:
                            self.process('mpd')
                        elif fd == sys.stdin.fileno() and event & select.POLLIN:
                            self.process('stdin')
            except select.error as e:
                # Ignore poll interruption.
                pass

    def handler(self, signum, frame):
        '''Signal handler.'''

        if signum == signal.SIGWINCH:
            # Resize window.
            self.resize_win()
            # Consume KEY_RESIZE and update.
            self.process('stdin')

def main():

    '''
    main function;
    '''

    try:
        locale.setlocale(locale.LC_ALL,'')

        if not os.path.isdir(conf.lyrics_dir):
            os.makedirs(conf.lyrics_dir)

        with Ncmpy() as ncmpy:
            signal.signal(signal.SIGWINCH, ncmpy.handler)
            ncmpy.main_loop()
    finally:
        curses.endwin()

if __name__ == '__main__':
    main()

