#!/usr/bin/env python3

'''
main module;
'''

from curses import wrapper
from threading import Condition
import curses
import locale
import mpd
import select
import signal
import sys

from ncmpy.config import conf
from ncmpy.keysym import keysym as ks
from ncmpy.keysym import keysymgrp as ksg
from ncmpy.pane import ArtistAlbumPane
from ncmpy.pane import BarPane
from ncmpy.pane import DatabasePane
from ncmpy.pane import HelpPane
from ncmpy.pane import InfoPane
from ncmpy.pane import LinePane
from ncmpy.pane import LyricsPane
from ncmpy.pane import MenuPane
from ncmpy.pane import MessagePane
from ncmpy.pane import OutputPane
from ncmpy.pane import ProgressPane
from ncmpy.pane import QueuePane
from ncmpy.pane import SearchPane
from ncmpy.pane import StatusPane
from ncmpy.thread import LyricsThread

class Ncmpy():

    '''
    main class;
    '''

    def _init_mpd(self, host, port):

        ##  connect to mpd;
        self.mpc = mpd.MPDClient()
        self.mpc.connect(host, port)

        ##  fetch server status;
        self.status = self.mpc.status()
        self.stats = self.mpc.stats()
        self.currentsong = self.mpc.currentsong()

    def _init_curses(self, stdscr):

        ##  hide cursor;
        curses.curs_set(0)

        ##  init colors;
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLUE, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)

        ##  force a refresh to avoid problems on first key press;
        stdscr.refresh()

        ##  store main window and its size;
        self.stdscr = stdscr
        self.height, self.width = self.stdscr.getmaxyx()

    def _init_panes(self):

        ##  create panes;
        self.menu_pane = MenuPane(
            'Menu',
            curses.newwin(1, self.width, 0, 0), self)
        self.line_pane = LinePane(
            'Line',
            curses.newwin(1, self.width, 1, 0), self)
        self.progress_pane = ProgressPane(
            'Progress',
            curses.newwin(1, self.width, self.height - 2, 0), self)
        self.status_pane = StatusPane(
            'Status',
            curses.newwin(1, self.width, self.height - 1, 0), self)
        self.message_pane = MessagePane(
            'Message',
            curses.newwin(1, self.width, self.height - 1, 0), self)
        self.help_pane = HelpPane(
            'Help',
            curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.queue_pane = QueuePane(
            'Queue',
            curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.database_pane = DatabasePane(
            'Database',
            curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.lyrics_pane = LyricsPane(
            'Lyrics',
            curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.artist_album_pane = ArtistAlbumPane(
            'Artist-Album',
            curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.search_pane = SearchPane(
            'Search',
            curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.info_pane = InfoPane(
            'Info',
            curses.newwin(self.height - 4, self.width, 2, 0), self)
        self.output_pane = OutputPane(
            'Output',
            curses.newwin(self.height - 4, self.width, 2, 0), self)

        ##  pane list;
        self.panes = [
            self.menu_pane,
            self.line_pane,
            self.progress_pane,
            self.status_pane,
            self.message_pane,
            self.help_pane,
            self.queue_pane,
            self.database_pane,
            self.lyrics_pane,
            self.artist_album_pane,
            self.search_pane,
            self.info_pane,
            self.output_pane,
        ]

        ##  current pane;
        self.cpane = self.queue_pane

        ##  prev pane;
        self.ppane = None

    def _init_threads(self):
        self.lyrics_thread = LyricsThread(self)

    def __init__(self, stdscr):

        ##  loop flag;
        ##
        ##  `True` iff in main loop;
        self.loop = False

        ##  idle flag;
        ##
        ##  `python-mpd2` requires calling `send_idle` before calling `noidle`,
        ##  so we cannot call `noidle` twice; also, we cannot call `send_idle`
        ##  twice, which would reset connection; thus, we must call `send_idle`
        ##  and `noidle` one after the other:
        ##
        ##      send_idle -> noidle -> send_idle -> noidle -> ...
        ##
        ##  the `idle` flag tracks which of these 2 commands was called last;
        ##  note that calling `send_idle` doesnt guarantee mpd server will be
        ##  put in idle state: if there were changes before calling `send_idle`,
        ##  then mpd server will reply with those changes immediately; that is
        ##  to say, `idle == True` doesnt guarantee mpd server is idle; but
        ##  `idle == False` does guarantee mpd server is not idle;
        self.idle = False

        ##  seek flag;
        ##
        ##  for performance reason, we update elapsed time on the client side
        ##  after user pressed a seek key, and only send it to mpd server on the
        ##  next non-seek (including timeout) event;
        ##
        ##  the `seek` flag is `True` iff we have a pending seek: after user
        ##  pressed a seek key and before elapsed time is sent to server;
        self.seek = False

        ##  elapsed time;
        self.elapsed = 0

        ##  total time;
        self.total = 0

        ##  search keyword;
        self.search_kw = ''

        ##  search direction;
        self.search_dr = 0

        ##  pending mpd commands for batch processing;
        self.batch = []

        ##  shared data storage for inter-pane communication;
        self.ipc = {}

        ##  shared data storage for inter-thread communication;
        self.itc = {}

        ##  condition variable for inter-thread communication;
        self.itc_cond = Condition()

        ##  init components;
        self._init_mpd(conf.mpd_host, conf.mpd_port)
        self._init_curses(stdscr)
        self._init_panes()
        self._init_threads()

        ##  start lyrics thread;
        self.lyrics_thread.start()

        ##  setup signal handler;
        signal.signal(signal.SIGWINCH, self.handler)

        ##  initial update;
        self.on_event('timeout')

    def fetch(self):

        '''
        fetch data;
        '''

        self.status = self.mpc.status()
        self.stats = self.mpc.stats()
        self.currentsong = self.mpc.currentsong()

        for pane in self.panes:
            pane.fetch()

    def round0(self):

        '''
        round 0;
        '''

        ##  seek;
        if self.status['state'] in [ 'play', 'pause' ]:

            if self.ch in ksg.seek:
                ##  enter seek mode;
                if not self.seek:
                    self.elapsed, self.total = [
                        int(i) for i in self.status['time'].split(':')
                    ]
                    self.seek = True

                change = {
                    ks.seekb    : - 1,
                    ks.seekf    : + 1,
                    ks.seekbp   : - max(1, self.total // 100),
                    ks.seekfp   : + max(1, self.total // 100),
                }[self.ch]
                self.elapsed = max(0, min(self.total, self.elapsed + change))

            if self.seek:
                ##  overwrite playback time in seek mode;
                self.status['time'] = '{}:{}'.format(self.elapsed, self.total)

                if self.ch not in ksg.local:
                    ##  send seek command to server and leave seek mode;
                    self.mpc.seekid(self.status['songid'], self.elapsed)
                    self.seek = False

        ##  volume control;
        if self.ch == ks.voldn:
            vol = max(0, int(self.status.get('volume', -1)) - 1)
            try:
                self.mpc.setvol(vol)
                self.status['volume'] = str(vol)
            except mpd.CommandError as e:
                self.ipc['msg'] = str(e)
        elif self.ch == ks.volup:
            vol = min(100, int(self.status.get('volume', -1)) + 1)
            try:
                self.mpc.setvol(vol)
                self.status['volume'] = str(vol)
            except mpd.CommandError as e:
                self.ipc['msg'] = str(e)

        ##  playback control;
        elif self.ch == ks.pause:
            self.mpc.pause()
        elif self.ch == ks.stop:
            self.mpc.stop()
        elif self.ch == ks.prev:
            self.mpc.previous()
        elif self.ch == ks.next:
            self.mpc.next()

        ##  mode control;
        elif self.ch == ks.consume:
            self.status['consume'] = str(1 - int(self.status['consume']))
            self.mpc.consume(self.status['consume'])
        elif self.ch == ks.random:
            self.status['random'] = str(1 - int(self.status['random']))
            self.mpc.random(self.status['random'])
        elif self.ch == ks.repeat:
            self.status['repeat'] = str(1 - int(self.status['repeat']))
            self.mpc.repeat(self.status['repeat'])
        elif self.ch == ks.single:
            self.status['single'] = str(1 - int(self.status['single']))
            self.mpc.single(self.status['single'])

        ##  playlist save & load;
        elif self.ch == ks.savepl:
            name = self.message_pane.getstr('Save')
            try:
                self.mpc.save(name)
            except mpd.CommandError as e:
                self.ipc['msg'] = str(e).rsplit('} ')[1]
            else:
                self.ipc['msg'] = 'Playlist {} saved'.format(name)
                self.ipc['playlist'] = 'saved'
        elif self.ch == ks.loadpl:
            name = self.message_pane.getstr('Load')
            try:
                self.mpc.load(name)
            except mpd.CommandError as e:
                self.ipc['msg'] = str(e).rsplit('} ')[1]
            else:
                self.ipc['msg'] = 'Playlist {} loaded'.format(name)

        ##  search items;
        elif self.ch in [ ks.searchdn, ks.searchup ]:
            search_kw = self.message_pane.getstr('Find')
            if search_kw:
                self.search_kw = search_kw
                self.search_dr = {
                    ks.searchdn: + 1,
                    ks.searchup: - 1,
                }[self.ch]

        ##  panes do round0;
        for pane in self.panes:
            pane.round0()

    def round1(self):

        '''
        round 1;
        '''

        ##  pane switch;
        if self.ch == ks.panehelp:
            self.ppane, self.cpane = self.cpane, self.help_pane
        elif self.ch == ks.panequeue:
            self.ppane, self.cpane = self.cpane, self.queue_pane
        elif self.ch == ks.panedatabase:
            self.ppane, self.cpane = self.cpane, self.database_pane
        elif self.ch == ks.panelyrics:
            self.ppane, self.cpane = self.cpane, self.lyrics_pane
        elif self.ch == ks.paneartistalbum:
            self.ppane, self.cpane = self.cpane, self.artist_album_pane
        elif self.ch == ks.panesearch:
            self.ppane, self.cpane = self.cpane, self.search_pane
        elif self.ch == ks.paneinfo:
            if self.cpane != self.info_pane:
                self.ppane, self.cpane = self.cpane, self.info_pane
            elif self.ppane:
                self.ppane, self.cpane = self.cpane, self.ppane
        elif self.ch == ks.paneoutput:
            self.ppane, self.cpane = self.cpane, self.output_pane
        elif 'database-locate' in self.ipc:
            self.cpane = self.database_pane
        elif 'queue-locate' in self.ipc:
            self.cpane = self.queue_pane

        ##  panes do round1;
        for pane in self.panes:
            pane.round1()

    def update(self):

        '''
        update windows;
        '''

        for pane in self.panes:
            ##  update current pane and all bar panes;
            if pane == self.cpane or isinstance(pane, BarPane):
                pane.update()

        curses.doupdate()

    def resize(self):

        '''
        resize windows; called in `SIGWINCH` handler;
        '''

        curses.endwin()
        self.stdscr.refresh()
        self.height, self.width = self.stdscr.getmaxyx()

        for pane in self.panes:
            pane.resize()

    def enter_idle(self):

        '''
        enter idle state;
        '''

        if not self.idle:
            self.mpc.send_idle()
            self.idle = True

    def leave_idle(self):

        '''
        leave idle state;
        '''

        if self.idle:
            self.ipc['idle'] = self.mpc.noidle()
            self.idle = False

    def on_event(self, type_):

        '''
        main loop event handler;

        ## params

        type_:str
        :   event type: timeout, stdin, mpd;
        '''

        if type_ == 'stdin':
            self.ch = self.stdscr.getch()
            if self.ch == ks.quit:
                self.loop = False
                return
            sync = (self.ch not in ksg.local)
        else:
            self.ch = None
            sync = True

        self.ipc.clear()

        if sync:
            self.leave_idle()
            if self.batch:
                self.mpc.command_list_ok_begin()
                for cmd in self.batch:
                    exec('self.mpc.' + cmd)
                self.mpc.command_list_end()
                self.batch.clear()
            self.fetch()

        self.round0()
        self.round1()
        self.update()

        if type_ == 'stdin':
            ##  flush input buffer to discard any typeaheads;
            curses.flushinp()
        else:
            self.enter_idle()

    def main_loop(self):

        '''
        main loop;
        '''

        poll = select.poll()
        poll.register(self.mpc.fileno(), select.POLLIN)
        poll.register(sys.stdin.fileno(), select.POLLIN)

        self.loop = True
        while self.loop:
            try:
                resps = poll.poll(200)
                if not resps:
                    self.on_event('timeout')
                    continue
                for fd, event in resps:
                    if fd == self.mpc.fileno() and event & select.POLLIN:
                        self.on_event('mpd')
                    if fd == sys.stdin.fileno() and event & select.POLLIN:
                        self.on_event('stdin')
            except OSError:
                ##  ignore poll interruption;
                pass

    def handler(self, signum, frame):

        '''signal handler;'''

        if signum == signal.SIGWINCH:
            self.resize()
            ##  consume `KEY_RESIZE`;
            self.stdscr.getch()

def _main(stdscr):

    ##  set locale;
    locale.setlocale(locale.LC_ALL, '')

    ##  start main loop;
    Ncmpy(stdscr).main_loop()

def main():

    '''
    main function;
    '''

    return wrapper(_main)

if __name__ == '__main__':
    main()

