#!/usr/bin/env python3

'''Pane module.'''

import curses
import locale
import mpd
import os
import threading
import time

from ncmpy import lrc
from ncmpy import ttplyrics

from ncmpy.config import *
from ncmpy.util import *

class Pane():
    '''Base class of all panes.'''

    def __init__(self, win, main):
        '''
        Initialize a pane.

        win - A curses.window instance.
        main - A Ncmpy instance.
        '''

        self.win = win
        self.main = main
        self.mpc = main.mpc
        self.board = main.board
        self.height, self.width = self.win.getmaxyx()

    def update_data(self):
        '''Update data.'''

        self.status = self.main.status
        self.stats = self.main.stats
        self.currentsong = self.main.currentsong

    def round1(self, c):
        '''Round one.'''

        pass

    def round2(self):
        '''Round two.'''

        pass

    def update_win(self):
        '''Update window.'''

        pass

    def resize_win(self):
        '''Resize window.'''

        pass

class BarPane(Pane):
    '''Bar pane.'''

    def __init__(self, win, main):
        Pane.__init__(self, win, main)

    def bar_resize_win(self, y, x):
        '''Resize bar window.'''

        self.win.resize(1, self.main.width)
        self.height, self.width = self.win.getmaxyx()
        self.win.mvwin(y, x)

class BlockPane(Pane):
    '''Block pane.'''

    def __init__(self, win, main):
        Pane.__init__(self, win, main)

    def block_resize_win(self):
        '''Resize block window.'''

        self.win.resize(self.main.height - 4, self.main.width)
        self.height, self.width = self.win.getmaxyx()
        self.win.mvwin(2, 0)

    def resize_win(self):
        self.block_resize_win()

class ScrollPane(BlockPane):
    '''Scroll pane.'''

    def __init__(self, win, main):
        BlockPane.__init__(self, win, main)

        # Number of lines in total.
        self.num = 0
        # Beginning line.
        self.beg = 0

    def line_down(self):
        if self.beg < self.num - self.height:
            self.beg += 1

    def line_up(self):
        if self.beg > 0:
            self.beg -= 1

    def page_down(self):
        self.beg = min(self.beg + self.height, self.num - self.height)

    def page_up(self):
        self.beg = max(self.beg - self.height, 0)

    def locate(self, pos):
        '''Select pos, and put in the center.'''

        if pos >= self.height // 2:
            self.beg = pos - self.height // 2
        else:
            self.beg = 0

class CursedPane(BlockPane):
    '''Pane with cursor.'''

    def __init__(self, win, main):
        BlockPane.__init__(self, win, main)

        # Number of lines in total.
        self.num = 0
        # Beginning line.
        self.beg = 0
        # Selected line.
        self.sel = 0
        # Current line.
        self.cur = 0

    def line_down(self):
        if self.sel < self.num - 1:
            self.sel += 1
            if self.sel - self.beg == self.height:
                self.beg += 1

    def line_up(self):
        if self.sel > 0:
            self.sel -= 1
            if self.sel - self.beg == -1:
                self.beg -= 1

    def page_down(self):
        if self.sel < self.num - self.height:
            self.sel += self.height
            self.beg = min(self.beg + self.height, self.num - self.height)
        else:
            self.sel = self.num - 1
            self.beg = max(self.num - self.height, 0)

    def page_up(self):
        if self.sel < self.height:
            self.sel = 0
            self.beg = 0
        else:
            self.sel -= self.height
            self.beg = max(self.beg - self.height, 0)

    def select_top(self):
        self.sel = self.beg

    def select_middle(self):
        self.sel = min(self.beg + self.height // 2, self.num - 1)

    def select_bottom(self):
        self.sel = min(self.beg + self.height - 1, self.num - 1)

    def to_first(self):
        self.beg = 0
        self.sel = 0

    def to_last(self):
        self.beg = max(self.num - 1, 0)
        self.sel = max(self.num - 1, 0)

    def locate(self, pos):
        '''Select pos, and put in the center.'''

        if pos >= self.height // 2:
            self.beg = pos - self.height // 2
        else:
            self.beg = 0
        self.sel = pos

    def clamp(self, n):
        '''Clamp value into range [0, num).'''

        return max(min(n, self.num - 1), 0)

    def block_resize_win(self):
        BlockPane.block_resize_win(self)
        self.sel = min(self.sel, self.beg + self.height - 1)

    def search(self, panename, c):
        '''Search in panes.'''

        if panename == 'Queue':
            items = self.queue
        elif panename in ['Database', 'Artist-Album', 'Search']:
            items = self.items

        if self.main.search and self.main.search_di:
            di = {
                    ord('/') : 1,
                    ord('?') : -1,
                    ord('n') : self.main.search_di,
                    ord('N') : -self.main.search_di
                    }[c]
            has_match = False

            for i in [k % len(items) \
                    for k in range(self.sel + di, self.sel + di + di * len(items), di)]:
                item = items[i]

                if panename in ['Queue', 'Search']:
                    title = get_tag('title', item) or os.path.basename(item['file'])
                elif panename == 'Database':
                    title = list(item.values())[0]
                elif panename == 'Artist-Album':
                    if self._type in ['artist', 'album']:
                        title = item
                    elif self._type == 'song':
                        title = get_tag('title', item) or os.path.basename(item['file'])

                if title.find(self.main.search) != -1:
                    has_match = True
                    if di == 1 and i <= self.sel:
                        self.board['msg'] = 'search hit BOTTOM, continuing at TOP'
                    elif di == -1 and i >= self.sel:
                        self.board['msg'] = 'search hit TOP, continuing at BOTTOM'
                    self.locate(i)
                    break

            if not has_match:
                self.board['msg'] = 'Pattern not found: {}'.format(self.main.search)

class MenuPane(BarPane):
    '''Display pane name, play mode and volume.'''

    BLANK = ' ' * 5

    def __init__(self, win, main):
        BarPane.__init__(self, win, main)
        self.win.attron(curses.A_BOLD)

    def build_menu_str(self):
        title_str = self.main.tpanename
        mode_str = ('[con]' if int(self.status['consume']) else self.BLANK) + \
                ('[ran]' if int(self.status['random']) else self.BLANK) + \
                ('[rep]' if int(self.status['repeat']) else self.BLANK) + \
                ('[sin]' if int(self.status['single']) else self.BLANK)
        vol_str = 'Volume: ' + self.status['volume'] + '%'

        state_str = '{}    {}'.format(mode_str, vol_str)
        title_len = self.width - len(state_str)
        menu_str = title_str.ljust(title_len) + state_str

        return menu_str

    def update_win(self):
        menu_str = self.build_menu_str()

        # Must use insstr instead of addstr, because addstr cannot draw the last character (will
        # raise an exception). The same applies to other panes.
        self.win.erase()
        self.win.insstr(0, 0, menu_str)
        self.win.noutrefresh()

    def resize_win(self):
        self.bar_resize_win(0, 0)

class LinePane(BarPane):
    '''Horizontal line.'''

    def __init__(self, win, main):
        BarPane.__init__(self, win, main)

    def update_win(self):
        self.win.erase()
        self.win.insstr(0, 0, self.width * '-')
        self.win.noutrefresh()

    def resize_win(self):
        self.bar_resize_win(1, 0)

class ProgressPane(BarPane):
    '''Show playing progress.'''

    def __init__(self, win, main):
        BarPane.__init__(self, win, main)

    def build_prog_str(self):
        '''Build progress str.'''

        state = self.status.get('state')
        if state == 'stop':
            return '-' * self.width
        else:
            tm = self.status.get('time')
            elapsed, total = tm.split(':')
            pos = int((float(elapsed) / float(total)) * (self.width - 1))
            return '=' * pos + '0' + '-' * (self.width - pos - 1)

    def update_win(self):
        prog_str = self.build_prog_str()

        self.win.erase()
        self.win.insstr(0, 0, prog_str)
        self.win.noutrefresh()

    def resize_win(self):
        self.bar_resize_win(self.main.height - 2, 0)

class StatusPane(BarPane):
    '''Show playing status, elapsed/total time.'''

    state_name = {
            'play' : 'Playing',
            'stop' : 'Stopped',
            'pause' : 'Paused',
            }

    def __init__(self, win, main):
        BarPane.__init__(self, win, main)
        self.win.attron(curses.A_BOLD)

    def build_title_str(self):
        '''Build title str.'''

        state = self.status.get('state')
        song = self.currentsong
        title = song and (song.get('title') or os.path.basename(song.get('file'))) or ''
        return '{} > {}'.format(self.state_name[state], title)

    def build_tm_str(self):
        '''Build tm str.'''

        tm = self.status.get('time') or '0:0'
        elapsed, total = map(int, tm.split(':'))
        elapsed_mm, elapsed_ss, total_mm, total_ss = \
                elapsed // 60, elapsed % 60, total // 60, total % 60
        return '[{0}:{1:02d} ~ {2}:{3:02d}]'.format(elapsed_mm, elapsed_ss, total_mm, total_ss)

    def update_win(self):
        # Use two strs because it's difficult to calculate display length of unicode characters.
        title_str = self.build_title_str()
        tm_str = self.build_tm_str()

        self.win.erase()
        self.win.insstr(0, 0, title_str)
        self.win.insstr(0, self.width - len(tm_str), tm_str)
        self.win.noutrefresh()

    def resize_win(self):
        self.bar_resize_win(self.main.height - 1, 0)

class MessagePane(BarPane):
    '''Show message and get user input.'''

    def __init__(self, win, main):
        BarPane.__init__(self, win, main)
        self.msg = None
        self.timeout = 0

    def getstr(self, prompt):
        '''Get user input with prompt <prompt>.'''

        curses.nocbreak()
        curses.echo()
        curses.curs_set(1)
        self.win.move(0, 0)
        self.win.clrtoeol()
        self.win.addstr('{}: '.format(prompt), curses.A_BOLD)
        s = self.win.getstr(0, len(prompt) + 2)
        curses.curs_set(0)
        curses.noecho()
        curses.cbreak()
        return s.decode()

    def update_win(self):
        msg = self.board.get('msg')
        if msg:
            self.msg = msg
            self.timeout = 10   # Magic!

        # TODO. Use a real timer.
        if self.timeout > 0:
            self.win.erase()
            self.win.insstr(0, 0, self.msg, curses.A_BOLD)
            self.win.noutrefresh()
            self.timeout -= 1

    def resize_win(self):
        self.bar_resize_win(self.main.height - 1, 0)

class HelpPane(ScrollPane):
    '''Help.'''

    def __init__(self, win, main):
        ScrollPane.__init__(self, win, main)
        self.lines = [
                ('group', 'Global', None),
                ('hline', None, None),
                ('item', 'F1', 'Help'),
                ('item', 'F2', 'Queue'),
                ('item', 'F3', 'Database'),
                ('item', 'F4', 'Lyrics'),
                ('item', 'F5', 'Artist-Album'),
                ('item', 'F6', 'Search'),
                ('item', 'F7', 'Info'),
                ('item', 'F8', 'Output'),
                ('blank', None, None),
                ('item', 'q', 'quit'),
                ('blank', None, None),

                ('group', 'Playback', None),
                ('hline', None, None),
                ('item', 'Space', 'Play/Pause'),
                ('item', 's', 'Stop'),
                ('item', '>', 'next song'),
                ('item', '<', 'previous song'),
                ('blank', None, None),
                ('item', 'u', 'consume mode'),
                ('item', 'i', 'random mode'),
                ('item', 'o', 'repeat mode'),
                ('item', 'p', 'single mode'),
                ('blank', None, None),
                ('item', '9', 'volume down'),
                ('item', '0', 'volume up'),
                ('blank', None, None),
                ('item', 'left', 'seek +1'),
                ('item', 'right', 'seek -1'),
                ('item', 'down', 'seek -1%'),
                ('item', 'up', 'seek +1%'),
                ('blank', None, None),

                ('group', 'Movement', None),
                ('hline', None, None),
                ('item', 'j', 'go one line down'),
                ('item', 'k', 'go one line up'),
                ('item', 'f', 'go one page down'),
                ('item', 'b', 'go one page up'),
                ('item', 'g', 'go to top of list'),
                ('item', 'G', 'go to bottom of list'),
                ('item', 'H', 'go to top of screen'),
                ('item', 'M', 'go to middle of screen'),
                ('item', 'L', 'go to bottom of screen'),
                ('blank', None, None),
                ('item', '/', 'search down'),
                ('item', '?', 'search up'),
                ('item', 'n', 'next match'),
                ('item', 'N', 'previous match'),
                ('blank', None, None),

                ('group', 'Queue', ''),
                ('hline', None, None),
                ('item', 'Enter', 'Play'),
                ('item', 'l', 'select and center current song'),
                ('item', '\'', 'toggle auto center'),
                ('item', ';', 'locate selected song in database'),
                ('blank', None, None),
                ('item', 'x', 'remove song rating'),
                ('item', '1', 'rate selected song as     *'),
                ('item', '2', 'rate selected song as    **'),
                ('item', '3', 'rate selected song as   ***'),
                ('item', '4', 'rate selected song as  ****'),
                ('item', '5', 'rate selected song as *****'),
                ('blank', None, None),
                ('item', 'J', 'Move down selected song'),
                ('item', 'K', 'Move up selected song'),
                ('item', 'e', 'shuffle queue'),
                ('item', 'c', 'clear queue'),
                ('item', 'a', 'add all songs from database'),
                ('item', 'd', 'delete selected song from queue'),
                ('item', 'S', 'save queue to playlist'),
                ('item', 'O', 'load queue from playlist'),
                ('blank', None, None),

                ('group', 'Database', ''),
                ('hline', None, None),
                ('item', 'Enter', 'open directory / play song / load playlist'),
                ('item', '\'', 'go to parent directory'),
                ('item', '"', 'go to root directory'),
                ('item', 'a', 'append song to queue recursively'),
                ('item', ';', 'locate selected song in queue'),
                ('item', 'U', 'update database'),
                ('blank', None, None),

                ('group', 'Lyrics', ''),
                ('hline', None, None),
                ('item', 'l', 'center current line'),
                ('item', '\'', 'toggle auto center'),
                ('item', 'K', 'save lyrics'),
                ('blank', None, None),

                ('group', 'Artist-Album', ''),
                ('hline', None, None),
                ('item', 'Enter', 'open level / play song'),
                ('item', '\'', 'go to parent level'),
                ('item', '"', 'go to root level'),
                ('item', 'a', 'append song to queue recursively'),
                ('item', ';', 'locate selected song in queue'),
                ('blank', None, None),

                ('group', 'Search', ''),
                ('hline', None, None),
                ('item', 'B', 'start a database search, syntax = <tag_name>:<tag_value>'),
                ('item', 'Enter', 'play song'),
                ('item', 'a', 'append song to queue'),
                ('item', ';', 'locate selected song in queue'),
                ('blank', None, None),

                ('group', 'Info', ''),
                ('hline', None, None),
                ('blank', None, None),

                ('group', 'Output', ''),
                ('hline', None, None),
                ('item', 't', 'toggle output'),
                ('blank', None, None),
                ]
        self.num = len(self.lines)

    def round1(self, c):
        if c == ord('j'):
            self.line_down()
        elif c == ord('k'):
            self.line_up()
        elif c == ord('f'):
            self.page_down()
        elif c == ord('b'):
            self.page_up()

    def update_win(self):
        self.win.erase()
        for i in range(self.beg, min(self.beg + self.height, self.num)):
            line = self.lines[i]
            if line[0] == 'group':
                self.win.insstr(i - self.beg, 6, line[1], curses.A_BOLD)
            elif line[0] == 'hline':
                self.win.attron(curses.A_BOLD)
                self.win.hline(i - self.beg, 3, '-', self.width - 6)
                self.win.attroff(curses.A_BOLD)
            elif line[0] == 'item':
                self.win.insstr(i - self.beg, 0, line[1].rjust(20) + ' : ' + line[2])
            elif line[0] == 'blank':
                pass
        self.win.noutrefresh()

class QueuePane(CursedPane):
    '''Queue = current playlist.'''

    def __init__(self, win, main):
        CursedPane.__init__(self, win, main)

        # Playlist version.
        self.pl_version = -1

        # Auto center current song.
        self.auto_center = False

    def update_data(self):
        CursedPane.update_data(self)

        # Fetch playlist if version is different.
        if self.pl_version != int(self.status['playlist']):
            self.queue = self.mpc.playlistinfo()
            self.num = len(self.queue)
            self.beg = self.clamp(self.beg)
            self.sel = self.clamp(self.sel)

            for song in self.queue:
                if conf.enable_rating:
                    try:
                        rating = int(self.mpc.sticker_get(\
                                'song', song['file'], 'rating').split('=',1)[1])
                    except mpd.CommandError:
                        rating = 0
                    finally:
                        song['rating'] = rating
                else:
                    song['rating'] = 0

            self.pl_version = int(self.status['playlist'])

        self.cur = ('song' in self.status) and int(self.status['song']) or 0

    def round1(self, c):
        if c == ord('j'):
            self.line_down()
        elif c == ord('k'):
            self.line_up()
        elif c == ord('f'):
            self.page_down()
        elif c == ord('b'):
            self.page_up()
        elif c == ord('H'):
            self.select_top()
        elif c == ord('M'):
            self.select_middle()
        elif c == ord('L'):
            self.select_bottom()
        elif c == ord('g'):
            self.to_first()
        elif c == ord('G'):
            self.to_last()
        elif c == ord('l'):
            self.locate(self.cur)
        elif c == ord('a'):
            self.mpc.add('')
        elif c == ord('c'):
            self.mpc.clear()
            self.num = self.beg = self.sel = self.cur = 0
        elif c == ord('d'):
            if self.num > 0:
                self.main.pending.append('deleteid({})'.format(self.queue[self.sel]['id']))
                self.queue.pop(self.sel)
                if self.sel < self.cur:
                    self.cur -= 1
                self.num -= 1
                self.beg = self.clamp(self.beg)
                self.sel = self.clamp(self.sel)
                self.cur = self.clamp(self.cur)
        elif c == ord('J'):
            if self.sel + 1 < self.num:
                self.main.pending.append('swap({}, {})'.format(self.sel, self.sel + 1))
                self.queue[self.sel], self.queue[self.sel + 1] = \
                        self.queue[self.sel + 1], self.queue[self.sel]
                if self.cur == self.sel:
                    self.cur += 1
                elif self.cur == self.sel + 1:
                    self.cur -= 1
                self.line_down()
        elif c == ord('K'):
            if self.sel > 0:
                self.main.pending.append('swap({}, {})'.format(self.sel, self.sel - 1))
                self.queue[self.sel - 1], self.queue[self.sel] = \
                        self.queue[self.sel], self.queue[self.sel - 1]
                if self.cur == self.sel - 1:
                    self.cur += 1
                elif self.cur == self.sel:
                    self.cur -= 1
                self.line_up()
        elif c == ord('e'):
            self.mpc.shuffle()
        elif c == ord('\n'):
            self.mpc.playid(self.queue[self.sel]['id'])
        elif c in range(ord('1'), ord('5') + 1):
            if conf.enable_rating:
                rating = c - ord('0')
                if 0 <= self.cur and self.cur < len(self.queue):
                    song = self.queue[self.cur]
                    self.mpc.sticker_set('song', song['file'], 'rating', rating)
                    song['rating'] = rating
        elif c == ord('x'):
            if conf.enable_rating:
                if 0 <= self.cur and self.cur < len(self.queue):
                    song = self.queue[self.cur]
                    try:
                        self.mpc.sticker_delete('song', song['file'], 'rating')
                    except mpd.CommandError as e:
                        self.board['msg'] = str(e)
                    else:
                        song['rating'] = 0
        elif c in [ord('/'), ord('?'), ord('n'), ord('N')]:
            self.search('Queue', c)
        elif c == ord('\''):
            self.auto_center = not self.auto_center
        elif c == ord(';'):
            self.board['database-locate'] = self.queue[self.sel]['file']

        # Record selected song in board.
        if self.num > 0:
            self.board['queue-selected'] = self.queue[self.sel]

    def round2(self):
        uri = self.board.get('queue-locate')
        if uri:
            for i in range(len(self.queue)):
                if uri == self.queue[i]['file']:
                    self.locate(i)
                    break
            else:
                self.board['msg'] = 'Not found in playlist'

        # Auto center.
        if self.auto_center:
            self.locate(self.cur)

    def update_win(self):
        self.win.erase()
        for i in range(self.beg, min(self.beg + self.height, self.num)):
            item = self.queue[i]
            title = get_tag('title', item) or os.path.basename(item['file'])
            rating = item['rating']
            tm = format_time(item['time'])

            if i == self.cur:
                self.win.attron(curses.A_BOLD)
            if i == self.sel:
                self.win.attron(curses.A_REVERSE)
            self.win.hline(i - self.beg, 0, ' ', self.width)
            self.win.addnstr(i - self.beg, 0, title, self.width - 18)
            self.win.addnstr(i - self.beg, self.width - 16, rating * '*', 5)
            self.win.insstr(i - self.beg, self.width - len(tm), tm)
            if i == self.sel:
                self.win.attroff(curses.A_REVERSE)
            if i == self.cur:
                self.win.attroff(curses.A_BOLD)
        self.win.noutrefresh()

class DatabasePane(CursedPane):
    '''All songs/directories/playlists in database.'''

    def __init__(self, win, main):
        CursedPane.__init__(self, win, main)

        # Current dir.
        self.dir = ''
        self.items = self.list_items()

    def list_items(self, keeppos=False):
        '''
        List contents of current dir.

        This method is called when current dir changes (e.g. database update), or new items are
        added or removed (e.g. playlist add/delete).
        '''

        items = self.mpc.lsinfo(self.dir)
        items.insert(0, {'directory' : '..'})
        self.num = len(items)
        if keeppos:
            self.beg = self.clamp(self.beg)
            self.sel = self.clamp(self.sel)
        else:
            self.beg = 0
            self.sel = 0
        return items

    def update_data(self):
        CursedPane.update_data(self)

        if 'database-updated' in self.board:
            self.dir = ''
            self.items = self.list_items()
            self.board['msg'] = 'Database updated.'

    def round1(self, c):
        if c == ord('j'):
            self.line_down()
        elif c == ord('k'):
            self.line_up()
        elif c == ord('f'):
            self.page_down()
        elif c == ord('b'):
            self.page_up()
        elif c == ord('H'):
            self.select_top()
        elif c == ord('M'):
            self.select_middle()
        elif c == ord('L'):
            self.select_bottom()
        elif c == ord('g'):
            self.to_first()
        elif c == ord('G'):
            self.to_last()
        elif c == ord('\''):
            oldroot = self.dir
            self.dir = os.path.dirname(self.dir)
            self.items = self.list_items()
            for i in range(len(self.items)):
                if self.items[i].get('directory') == oldroot:
                    self.locate(i)
                    break
        elif c == ord('"'):
            self.dir = ''
            self.items = self.list_items()
        elif c == ord('\n'):
            item = self.items[self.sel]
            if ('directory' in item):
                uri = item['directory']
                if uri == '..':
                    oldroot = self.dir
                    self.dir = os.path.dirname(self.dir)
                    self.items = self.list_items()
                    for i in range(len(self.items)):
                        if self.items[i].get('directory') == oldroot:
                            self.locate(i)
                            break
                else:
                    self.dir = uri
                    self.items = self.list_items()

            elif ('file' in item):
                uri = item['file']
                songs = self.mpc.playlistfind('file', uri)
                if songs:
                    self.mpc.playid(songs[0]['id'])
                else:
                    self.mpc.add(uri)
                    song = self.mpc.playlistfind('file', uri)[0]
                    self.mpc.playid(song['id'])
            elif ('playlist' in item):
                name = item['playlist']
                try:
                    self.mpc.load(name)
                except mpd.CommandError as e:
                    self.board['msg'] = str(e).rsplit('} ')[1]
                else:
                    self.board['msg'] = 'Playlist {} loaded'.format(name)
        elif c == ord('a'):
            item = self.items[self.sel]
            if ('directory' in item):
                uri = item['directory']
            else:
                uri = item['file']
            if uri == '..':
                self.mpc.add(os.path.dirname(self.dir))
            else:
                self.mpc.add(uri)
        elif c == ord('d'):
            item = self.items[self.sel]
            if ('playlist' in item):
                name = item['playlist']
                try:
                    self.mpc.rm(name)
                except mpd.CommandError as e:
                    self.board['msg'] = str(e).rsplit('} ')[1]
                else:
                    self.board['msg'] = 'Playlist {} deleted'.format(name)
                    self.items = self.list_items(keeppos=True)
        elif c == ord('U'):
            self.mpc.update()
        elif c in [ord('/'), ord('?'), ord('n'), ord('N')]:
            self.search('Database', c)
        elif c == ord(';'):
            # tell QUEUE we want to locate a song
            item = self.items[self.sel]
            if ('file' in item):
                self.board['queue-locate'] = item.get('file')
            else:
                self.board['msg'] = 'No song selected'

        # Record selected song in borard.
        self.board['database-selected'] = self.items[self.sel].get('file')

    def round2(self):
        # if there's a path request, rebuild view, using
        # dirname(path) as display dir, and search for the
        # requested song.
        uri = self.board.get('database-locate')
        if uri:
            self.dir = os.path.dirname(uri)
            self.items = self.list_items()
            for i in range(len(self.items)):
                if self.items[i].get('file') == uri:
                    self.locate(i)
                    break
            else:
                self.board['msg'] = 'Not found in database'

        # if a playlist is saved, rebuild view, keep original positions
        if self.board.get('playlist') == 'saved':
            self.items = self.list_items(keeppos=True)

    def update_win(self):
        self.win.erase()
        for i in range(self.beg, min(self.beg + self.height, self.num)):
            item = self.items[i]
            if ('directory' in item):
                t, uri = 'directory', item['directory']
            elif ('file' in item):
                t, uri = 'file', item['file']
            elif ('playlist' in item):
                t, uri = 'playlist', item['playlist']

            if i == self.sel:
                self.win.attron(curses.A_REVERSE)
            if t == 'directory':
                self.win.attron(curses.color_pair(1) | curses.A_BOLD)
            elif t == 'playlist':
                self.win.attron(curses.color_pair(2) | curses.A_BOLD)
            self.win.hline(i - self.beg, 0, ' ', self.width)
            self.win.insstr(i - self.beg, 0, os.path.basename(uri))
            if t == 'directory':
                self.win.attroff(curses.color_pair(1) | curses.A_BOLD)
            elif t == 'playlist':
                self.win.attroff(curses.color_pair(2) | curses.A_BOLD)
            if i == self.sel:
                self.win.attroff(curses.A_REVERSE)
        self.win.noutrefresh()

class LyricsPane(ScrollPane, threading.Thread):
    '''Display lyrics.'''

    def __init__(self, win, main):
        ScrollPane.__init__(self, win, main)
        threading.Thread.__init__(self, name='lyrics')

        # directory to save lyrics.
        # Make sure have write permission.
        self._lyrics_dir = conf.lyrics_dir

        # new song, maintained by pane
        self._nsong = None
        # old song, maintained by worker
        self._osong = None
        # title of lyrics to fetch
        self._title = None
        # artist of lyrics to fetch
        self._artist = None
        # current lyrics, oneline str
        self._lyrics = '[00:00.00]Cannot fetch lyrics (No artist/title).'
        # current lyrics timestamp as lists, used by main thread only
        self._ltimes = []
        # current lyrics text as lists, used by main thread only
        self._ltexts = []
        # incicate lyrics state: 'local', 'net', 'saved' or False
        self._lyrics_state = False
        # condition variable for lyrics fetching and display
        self._cv = threading.Condition()

        # auto-center
        self.auto_center = True

    def _transtag(self, tag):
        '''Transform tag into format used by lrc engine.'''

        if tag is None:
            return None
        else:
            return tag.replace(' ', '').lower()

    def update_data(self):
        ScrollPane.update_data(self)

        song = self.currentsong

        # Do nothing if cannot acquire lock.
        if self._cv.acquire(blocking=False):
            self._nsong = song.get('file')
            # If currengsong changes, wake up worker.
            if self._nsong != self._osong:
                self._artist = song.get('artist')
                self._title = song.get('title')
                self._cv.notify()
            self._cv.release()

    def _save_lyrics(self):
        if self._artist and self._title and self._cv.acquire(blocking=False):
            with open(os.path.join(self._lyrics_dir, self._artist.replace('/', '_') + \
                    '-' + self._title.replace('/', '_') + '.lrc'), 'wt') as f:
                f.write(self._lyrics)
            self.board['msg'] = 'Lyrics {}-{}.lrc saved.'.format(self._artist, self._title)
            self._lyrics_state = 'saved'
            self._cv.release()
        else:
            self.board['msg'] = 'Lyrics saving failed.'

    def round1(self, c):
        if c == ord('j'):
            self.line_down()
        elif c == ord('k'):
            self.line_up()
        elif c == ord('f'):
            self.page_down()
        elif c == ord('b'):
            self.page_up()
        elif c == ord('l'):
            self.locate(self.cur)
        elif c == ord('\''):
            self.auto_center = not self.auto_center
        elif c == ord('K'):
            self._save_lyrics()

    def _parse_lrc(self, lyrics):
        '''Parse lrc lyrics into ltimes and ltexts.'''

        tags, tms = lrc.parse(lyrics)
        sorted_keys = sorted(tms.keys())
        ltimes = [int(i) for i in sorted_keys]
        ltexts = [tms.get(i) for i in sorted_keys]
        return ltimes, ltexts

    def current_line(self):
        '''Calculate line number of current progress.'''

        cur = 0
        tm = self.status.get('time')
        if tm:
            elapsed = int(tm.split(':')[0])
            while cur < self.num and self._ltimes[cur] <= elapsed:
                cur += 1
            cur -= 1
        return cur

    def round2(self):
        # output 'Updating...' if cannot acquire lock
        if self._cv.acquire(blocking=0):
            # if worker reports lyrics fetched
            if self._lyrics_state in ['local', 'net']:
                # parse lrc (and copy lrc from shared mem to non-shared mem)
                self._ltimes, self._ltexts = self._parse_lrc(self._lyrics)
                self.num, self.beg = len(self._ltimes), 0

                # auto-save lyrics
                if self._lyrics_state == 'net' and self.num > 10:
                    self._save_lyrics()
                else:
                    self._lyrics_state = 'saved'

            self._cv.release()
        else:
            self._ltimes, self._ltexts = [0], ['Updating...']
            # set self.num and self.beg
            self.num, self.beg = 1, 0

        # set self.cur, the highlighted line
        self.cur = self.current_line()

        # auto center
        if self.auto_center:
            self.locate(self.cur)

    def update_win(self):
        self.win.erase()
        attr = curses.A_BOLD | curses.color_pair(3)
        for i in range(self.beg, min(self.beg + self.height, self.num)):
            if i == self.cur:
                self.win.insstr(i - self.beg, 0, self._ltexts[i], attr)
            else:
                self.win.insstr(i - self.beg, 0, self._ltexts[i])
        self.win.noutrefresh()

    def run(self):
        self._cv.acquire()
        while True:
            # wait if currentsong doesn't change
            while self._nsong == self._osong:
                self._cv.wait()

            self._lyrics = '[00:00.00]Cannot fetch lyrics (No artist/title).'
            self._lyrics_state = 'local'

            # fetch lyrics if required information is provided
            if self._artist and self._title:
                # try to fetch from local lrc
                lyrics_file = os.path.join(self._lyrics_dir, self._artist.replace('/', '_') + \
                        '-' + self._title.replace('/', '_') + '.lrc')
                if os.path.isfile(lyrics_file):
                    with open(lyrics_file, 'rt') as f:
                        self._lyrics = f.read()
                    # inform round2: lyrics has been fetched
                    self._lyrics_state = 'local'
                # if local lrc doesn't exist, fetch from Internet
                else:
                    self._lyrics = ttplyrics.fetch_lyrics(self._transtag(self._artist), \
                            self._transtag(self._title))
                    # inform round2: lyrics has been fetched
                    self._lyrics_state = 'net'
            self._osong = self._nsong

class InfoPane(ScrollPane):
    '''Information about songs:

        currently playing
        currently selected in queue
        currently selected in database'''

    def __init__(self, win, main):
        ScrollPane.__init__(self, win, main)
        # current playing
        self._cp = {}
        # selected in queue
        self._siq = {}
        # selected in database
        self._sid = {}
        # database.sel's uri cache
        self._dburi = None
        self.lines = [
                ('group', 'Currently Playing', None),
                ('hline', None, None),
                ('item', 'Title', ''),
                ('item', 'Artist', ''),
                ('item', 'Album', ''),
                ('item', 'Track', ''),
                ('item', 'Genre', ''),
                ('item', 'Date', ''),
                ('item', 'Time', ''),
                ('item', 'File', ''),
                ('blank', None, None),

                ('group', 'Currently Selected in Queue', None),
                ('hline', None, None),
                ('item', 'Title', ''),
                ('item', 'Artist', ''),
                ('item', 'Album', ''),
                ('item', 'Track', ''),
                ('item', 'Genre', ''),
                ('item', 'Date', ''),
                ('item', 'Time', ''),
                ('item', 'File', ''),
                ('blank', None, None),

                ('group', 'Currently Selected in Database', None),
                ('hline', None, None),
                ('item', 'Title', ''),
                ('item', 'Artist', ''),
                ('item', 'Album', ''),
                ('item', 'Track', ''),
                ('item', 'Genre', ''),
                ('item', 'Date', ''),
                ('item', 'Time', ''),
                ('item', 'File', ''),
                ('blank', None, None),

                ('group', 'MPD Statistics', None),
                ('hline', None, None),
                ('item', 'NumberofSongs', ''),
                ('item', 'NumberofArtists', ''),
                ('item', 'NumberofAlbums', ''),
                ('item', 'Uptime', ''),
                ('item', 'Playtime', ''),
                ('item', 'DBPlaytime', ''),
                ('item', 'DBUpdateTime', ''),
                ('blank', None, None),
                ]
        self.lines_d = None
        self._song_key_list = ['Title', 'Artist', 'Album', 'Track', 'Genre', 'Date', 'Time', 'File']
        self._stats_key_list = [\
                'Songs', 'Artists', 'Albums', 'Uptime', 'Playtime', 'DB_Playtime', 'DB_Update']

    def round1(self, c):
        if c == ord('j'):
            self.line_down()
        elif c == ord('k'):
            self.line_up()
        elif c == ord('f'):
            self.page_down()
        elif c == ord('b'):
            self.page_up()

    def round2(self):
        # get song info.

        # cp = currently playing
        # siq = selected in queue
        # sid = selected in database

        # on success, _cp and _siq are nonempty dicts.
        # on failure, _cp and _siq are empty dicts.
        self._cp = self.currentsong
        try:
            self._siq = self.board.get('queue-selected') or {}
        except (mpd.CommandError, IndexError):
            self._siq = {}
        try:
            uri = self.board.get('database-selected')
            if uri and uri != self._dburi and not self.main.idle:
                self._sid = self.mpc.listallinfo(uri)[0]
        except (mpd.CommandError, IndexError):
            self._sid = {}

        # setup sub lists
        cp_list = [('item', k, self._cp.get(k.lower()) or '') for k in self._song_key_list]
        siq_list = [('item', k, self._siq.get(k.lower()) or '') for k in self._song_key_list]
        sid_list = [('item', k, self._sid.get(k.lower()) or '') for k in self._song_key_list]
        stats_list = [('item', k, self.stats.get(k.lower()) or '') for k in self._stats_key_list]

        # convert list (multi-tags)  to str
        for l in (cp_list, siq_list, sid_list):
            for i in range(6):
                l[i] = (l[i][0], l[i][1], \
                        isinstance(l[i][2], str) and l[i][2] or ', '.join(l[i][2]))

        # format time
        for l in (cp_list, siq_list, sid_list):
            l[6] = (l[6][0], l[6][1], format_time(l[6][2]))
        for i in range(3, 6):
            stats_list[i] = (stats_list[i][0], stats_list[i][1], format_time(stats_list[i][2]))
        stats_list[6] = (stats_list[6][0], stats_list[6][1], \
                time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(stats_list[6][2]))))

        # merge into main list
        self.lines[2:10] = cp_list
        self.lines[13:21] = siq_list
        self.lines[24:32] = sid_list
        self.lines[35:42] = stats_list

        # set up options display
        self.lines_d = self.lines[:]
        # breakup file paths
        for k in (31, 20, 9):
            self.lines_d[k:k+1] = [('item', '', '/' + i) for i in self.lines[k][2].split('/')]
            self.lines_d[k] = ('item', 'File', self.lines_d[k][2][1:])

        self.num = len(self.lines_d)

    def update_win(self):
        self.win.erase()
        for i in range(self.beg, min(self.beg + self.height, self.num)):
            line = self.lines_d[i]
            if line[0] == 'group':
                self.win.insstr(i - self.beg, 6, line[1], curses.A_BOLD)
            elif line[0] == 'hline':
                self.win.attron(curses.A_BOLD)
                self.win.hline(i - self.beg, 3, '-', self.width - 6)
                self.win.attroff(curses.A_BOLD)
            elif line[0] == 'item':
                self.win.insstr(i - self.beg, 0, line[1].rjust(20) + ' : ' + line[2])
            elif line[0] == 'blank':
                pass
        self.win.noutrefresh()

class ArtistAlbumPane(CursedPane):
    '''List artists/albums in database.'''

    def __init__(self, win, main):
        CursedPane.__init__(self, win, main)

        # current displayed dir
        self._type = 'artist'
        self._artist = None
        self._album = None
        self.items = self.build()

    def build(self):
        '''Build view using self._type, self._artist and self._album.

        A view is rebuilt when self._type changes.'''

        if self._type == 'artist':
            view = self.mpc.list('artist')
        elif self._type == 'album':
            view = self._artist and self.mpc.list('album', self._artist) or []
        elif self._type == 'song':
            view = self._album and self.mpc.find('album', self._album) or []

        self.num = len(view)
        self.beg = 0
        self.sel = 0
        return view

    def round1(self, c):
        if c == ord('j'):
            self.line_down()
        elif c == ord('k'):
            self.line_up()
        elif c == ord('f'):
            self.page_down()
        elif c == ord('b'):
            self.page_up()
        elif c == ord('H'):
            self.select_top()
        elif c == ord('M'):
            self.select_middle()
        elif c == ord('L'):
            self.select_bottom()
        elif c == ord('g'):
            self.to_first()
        elif c == ord('G'):
            self.to_last()
        elif c == ord('\''):
            if self._type == 'artist':
                pass
            elif self._type == 'album':
                self._type = 'artist'
                self.items = self.build()
                for i in range(len(self.items)):
                    if self.items[i] == self._artist:
                        self.locate(i)
                        break
            elif self._type == 'song':
                self._type = 'album'
                self.items = self.build()
                for i in range(len(self.items)):
                    if self.items[i] == self._album:
                        self.locate(i)
                        break
        elif c == ord('"'):
            self._type = 'artist'
            self.items = self.build()
        elif c == ord('\n'):
            item = self.items[self.sel]
            if self._type == 'artist':
                self._artist = item
                self._type = 'album'
                self.items = self.build()
            elif self._type == 'album':
                self._album = item
                self._type = 'song'
                self.items = self.build()
            elif self._type == 'song':
                uri = item['file']
                songs = self.mpc.playlistfind('file', uri)
                if songs:
                    self.mpc.playid(songs[0]['id'])
                else:
                    self.mpc.add(uri)
                    song = self.mpc.playlistfind('file', uri)[0]
                    self.mpc.playid(song['id'])
        elif c == ord('a'):
            item = self.items[self.sel]
            if self._type == 'artist':
                self.mpc.findadd('artist', item)
            elif self._type == 'album':
                self.mpc.findadd('album', item)
            elif self._type == 'song':
                self.mpc.add(item['file'])
        elif c in [ord('/'), ord('?'), ord('n'), ord('N')]:
            self.search('Artist-Album', c)
        elif c == ord(';'):
            # tell QUEUE we want to locate a song
            if self._type == 'song':
                item = self.items[self.sel]
                self.board['queue-locate'] = item.get('file')
            else:
                self.board['msg'] = 'No song selected'

    def round2(self):
        if ('database-updated' in self.board):
            self._type = 'artist'
            self.items = self.build()

    def update_win(self):
        self.win.erase()
        for i in range(self.beg, min(self.beg + self.height, self.num)):
            item = self.items[i]

            if self._type in ['artist', 'album']:
                val = item
            elif self._type == 'song':
                val = get_tag('title', item) or os.path.basename(item.get('file'))

            if i == self.sel:
                self.win.attron(curses.A_REVERSE)
            if self._type == 'artist':
                self.win.attron(curses.color_pair(1) | curses.A_BOLD)
            elif self._type == 'album':
                self.win.attron(curses.color_pair(2) | curses.A_BOLD)
            self.win.hline(i - self.beg, 0, ' ', self.width)
            self.win.insstr(i - self.beg, 0, val)
            if self._type == 'artist':
                self.win.attroff(curses.color_pair(1) | curses.A_BOLD)
            elif self._type == 'album':
                self.win.attroff(curses.color_pair(2) | curses.A_BOLD)
            if i == self.sel:
                self.win.attroff(curses.A_REVERSE)
        self.win.noutrefresh()

class SearchPane(CursedPane):
    '''Search in the database.'''

    def __init__(self, win, main):
        CursedPane.__init__(self, win, main)

        self.items = []

    def build(self, kw):
        '''Build view using search keywords.'''

        try:
            name, value = kw.split(':', 1)
            view = self.mpc.find(name, value) or []
            if not view:
                self.board['msg'] = 'Nothing found :('
        except:
            view = []
            self.board['msg'] = 'Syntax is <tag_name>:<tag_value>'

        self.num = len(view)
        self.beg = 0
        self.sel = 0
        return view

    def round1(self, c):
        if c == ord('j'):
            self.line_down()
        elif c == ord('k'):
            self.line_up()
        elif c == ord('f'):
            self.page_down()
        elif c == ord('b'):
            self.page_up()
        elif c == ord('H'):
            self.select_top()
        elif c == ord('M'):
            self.select_middle()
        elif c == ord('L'):
            self.select_bottom()
        elif c == ord('g'):
            self.to_first()
        elif c == ord('G'):
            self.to_last()
        elif c == ord('B'):
            self.items = self.build(self.main.e.getstr('Database Search'))
        elif c == ord('\n'):
            item = self.items[self.sel]
            uri = item['file']
            songs = self.mpc.playlistfind('file', uri)
            if songs:
                self.mpc.playid(songs[0]['id'])
            else:
                self.mpc.add(uri)
                song = self.mpc.playlistfind('file', uri)[0]
                self.mpc.playid(song['id'])
        elif c == ord('a'):
            item = self.items[self.sel]
            self.mpc.add(item['file'])
        elif c in [ord('/'), ord('?'), ord('n'), ord('N')]:
            self.search('Search', c)
        elif c == ord(';'):
            # tell QUEUE we want to locate a song
            if self.sel < self.num:
                item = self.items[self.sel]
                self.board['queue-locate'] = item.get('file')
            else:
                self.board['msg'] = 'No song selected'

    def update_win(self):
        self.win.erase()
        for i in range(self.beg, min(self.beg + self.height, self.num)):
            item = self.items[i]

            val = get_tag('title', item) or os.path.basename(item.get('file'))

            if i == self.sel:
                self.win.attron(curses.A_REVERSE)
            self.win.hline(i - self.beg, 0, ' ', self.width)
            self.win.insstr(i - self.beg, 0, val)
            if i == self.sel:
                self.win.attroff(curses.A_REVERSE)
        self.win.noutrefresh()

class OutputPane(CursedPane):
    '''Output pane.'''

    def __init__(self, win, main):
        CursedPane.__init__(self, win, main)
        self.outputs = []

    def update_data(self):
        CursedPane.update_data(self)

        self.outputs = self.mpc.outputs()
        self.num = len(self.outputs)
        self.beg = self.clamp(self.beg)
        self.sel = self.clamp(self.sel)

    def round1(self, c):
        if c == ord('j'):
            self.line_down()
        elif c == ord('k'):
            self.line_up()
        elif c == ord('f'):
            self.page_down()
        elif c == ord('b'):
            self.page_up()
        elif c == ord('t'):
            output = self.outputs[self.sel]
            output_id = int(output['outputid'])
            output_enabled = int(output['outputenabled'])
            if output_enabled:
                self.mpc.disableoutput(output_id)
                self.outputs[self.sel]['outputenabled'] = '0'
            else:
                self.mpc.enableoutput(output_id)
                self.outputs[self.sel]['outputenabled'] = '1'

    def update_win(self):
        self.win.erase()

        for i in range(self.beg, min(self.beg + self.height, self.num)):
            item = self.outputs[i]

            if i == self.sel:
                self.win.attron(curses.A_REVERSE)

            enabled_str = '[{}]'.format('o' if int(item['outputenabled']) else 'x')
            name_str = item['outputname']
            item_str = '{} {}'.format(enabled_str, name_str)

            self.win.hline(i - self.beg, 0, ' ', self.width)
            self.win.insstr(i - self.beg, 0, item_str)

            if i == self.sel:
                self.win.attroff(curses.A_REVERSE)

        self.win.noutrefresh()

