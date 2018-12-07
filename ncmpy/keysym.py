#!/usr/bin/env python3

'''
keysym module;
'''

from types import SimpleNamespace as namespace
import curses

##  keyname to keycode mapping;
##
##  keynames are used in config files;
keyname = namespace()

keyname.space           =   ord(' ')
keyname.enter           =   ord('\n')
keyname.left            =   curses.KEY_LEFT
keyname.right           =   curses.KEY_RIGHT
keyname.down            =   curses.KEY_DOWN
keyname.up              =   curses.KEY_UP
keyname.f1              =   curses.KEY_F1
keyname.f2              =   curses.KEY_F2
keyname.f3              =   curses.KEY_F3
keyname.f4              =   curses.KEY_F4
keyname.f5              =   curses.KEY_F5
keyname.f6              =   curses.KEY_F6
keyname.f7              =   curses.KEY_F7
keyname.f8              =   curses.KEY_F8

##  keysym to keycode mapping;
##
##  keysyms represent semantics;
keysym = namespace()

keysym.voldn            =   ord('9')
keysym.volup            =   ord('0')
keysym.pause            =   ord(' ')
keysym.stop             =   ord('s')
keysym.next             =   ord('>')
keysym.prev             =   ord('<')
keysym.consume          =   ord('u')
keysym.random           =   ord('i')
keysym.repeat           =   ord('o')
keysym.single           =   ord('p')
keysym.savepl           =   ord('S')
keysym.loadpl           =   ord('O')
keysym.searchdn         =   ord('/')
keysym.searchup         =   ord('?')
keysym.searchnext       =   ord('n')
keysym.searchprev       =   ord('N')
keysym.quit             =   ord('q')
keysym.linedn           =   ord('j')
keysym.lineup           =   ord('k')
keysym.pagedn           =   ord('f')
keysym.pageup           =   ord('b')
keysym.top              =   ord('H')
keysym.mid              =   ord('M')
keysym.bot              =   ord('L')
keysym.first            =   ord('g')
keysym.last             =   ord('G')
keysym.locate           =   ord('l')
keysym.add              =   ord('a')
keysym.clear            =   ord('c')
keysym.delete           =   ord('d')
keysym.swapdn           =   ord('J')
keysym.swapup           =   ord('K')
keysym.shuffle          =   ord('e')
keysym.play             =   ord('\n')
keysym.unrate           =   ord('x')
keysym.rate1            =   ord('1')
keysym.rate2            =   ord('2')
keysym.rate3            =   ord('3')
keysym.rate4            =   ord('4')
keysym.rate5            =   ord('5')
keysym.lock             =   ord('\'')           ##  autocenter
keysym.dblocate         =   ord(';')            ##  database-locate
keysym.parent           =   ord('\'')
keysym.root             =   ord('"')
keysym.update           =   ord('U')
keysym.savelyrics       =   ord('K')
keysym.search           =   ord('B')
keysym.toggle           =   ord('t')
keysym.seekb            =   curses.KEY_LEFT
keysym.seekf            =   curses.KEY_RIGHT
keysym.seekbp           =   curses.KEY_DOWN
keysym.seekfp           =   curses.KEY_UP
keysym.panehelp         =   curses.KEY_F1
keysym.panequeue        =   curses.KEY_F2
keysym.panedatabase     =   curses.KEY_F3
keysym.panelyrics       =   curses.KEY_F4
keysym.paneartistalbum  =   curses.KEY_F5
keysym.panesearch       =   curses.KEY_F6
keysym.paneinfo         =   curses.KEY_F7
keysym.paneoutput       =   curses.KEY_F8

##  keysym groups;
keysymgrp = namespace()

##  rate keysyms;
keysymgrp.rate = [
    keysym.rate1, keysym.rate2, keysym.rate3, keysym.rate4, keysym.rate5,
]
##  seek keysyms;
keysymgrp.seek = [
    keysym.seekb, keysym.seekf, keysym.seekbp, keysym.seekfp,
]
##  local keysyms; these keysyms dont modify mpd server state and are handled
##  locally; dont sync with mpd server when handling these keysyms;
keysymgrp.local = [
    ##  these keysyms are truly-local; they really dont send command to server;
    keysym.linedn, keysym.lineup, keysym.pagedn, keysym.pageup,
    keysym.top, keysym.mid, keysym.bot,
    keysym.first, keysym.last,
    ##  these keysyms are pseudo-local; they actually send command to server,
    ##  but not immediately after we press them;
    keysym.seekb, keysym.seekf, keysym.seekbp, keysym.seekfp,
    keysym.swapdn, keysym.swapup,
]
##  search keysyms;
keysymgrp.search = [
    keysym.searchdn, keysym.searchup, keysym.searchnext, keysym.searchprev,
]

def name2code(name):

    '''
    convert keyname to keycode;
    '''

    if hasattr(keyname, name):
        return getattr(keyname, name)
    else:
        return ord(name)

def code2name(code):

    '''
    convert keycode to keyname;
    '''

    for name_, code_ in vars(keyname).items():
        if code_ == code:
            return name_
    return chr(code)

