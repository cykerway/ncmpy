#!/usr/bin/env python3
# -*- Mode: python; coding: utf-8; tab-width: 8; indent-tabs-mode: t; -*-
#
# Copyright 2007 Sevenever
# Copyright (C) 2007 Sevenever
# Modified: (2011) Cyker Way
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301  USA.

import sys
import locale
import codecs
from urllib.request import urlopen
from urllib.request import Request
import random
from xml.dom.minidom import parse, parseString

def CodeFunc(Id, data):
    length = len(data)

    tmp2=0
    tmp3=0

    tmp1 = (Id & 0x0000FF00) >> 8							#右移8位后为0x0000015F
                                                            #tmp1 0x0000005F
    if ( (Id & 0x00FF0000) == 0 ):
        tmp3 = 0x000000FF & ~tmp1							#CL 0x000000E7
    else:
        tmp3 = 0x000000FF & ((Id & 0x00FF0000) >> 16)		#右移16位后为0x00000001

    tmp3 = tmp3 | ((0x000000FF & Id) << 8)					#tmp3 0x00001801
    tmp3 = tmp3 << 8										#tmp3 0x00180100
    tmp3 = tmp3 | (0x000000FF & tmp1)						#tmp3 0x0018015F
    tmp3 = tmp3 << 8										#tmp3 0x18015F00
    if ( (Id & 0xFF000000) == 0 ) :
        tmp3 = tmp3 | (0x000000FF & (~Id))					#tmp3 0x18015FE7
    else :
        tmp3 = tmp3 | (0x000000FF & (Id >> 24))			#右移24位后为0x00000000

    #tmp3	18015FE7

    i=length-1
    while(i >= 0):
        char = (data[i])
        if char >= 0x80:
            char = char - 0x100
        tmp1 = (char + tmp2) & 0x00000000FFFFFFFF
        tmp2 = (tmp2 << (i%2 + 4)) & 0x00000000FFFFFFFF
        tmp2 = (tmp1 + tmp2) & 0x00000000FFFFFFFF
        #tmp2 = ((data[i])) + tmp2 + ((tmp2 << (i%2 + 4)) & 0x00000000FFFFFFFF)
        i -= 1

    #tmp2 88203cc2
    i=0
    tmp1=0
    while(i<=length-1):
        char = (data[i])
        if char >= 128:
            char = char - 256
        tmp7 = (char + tmp1) & 0x00000000FFFFFFFF
        tmp1 = (tmp1 << (i%2 + 3)) & 0x00000000FFFFFFFF
        tmp1 = (tmp1 + tmp7) & 0x00000000FFFFFFFF
        #tmp1 = ((data[i])) + tmp1 + ((tmp1 << (i%2 + 3)) & 0x00000000FFFFFFFF)
        i += 1

    #EBX 5CC0B3BA

    #EDX = EBX | Id
    #EBX = EBX | tmp3
    tmp1 = (((((tmp2 ^ tmp3) & 0x00000000FFFFFFFF) + (tmp1 | Id)) & 0x00000000FFFFFFFF) * (tmp1 | tmp3)) & 0x00000000FFFFFFFF
    tmp1 = (tmp1 * (tmp2 ^ Id)) & 0x00000000FFFFFFFF

    if tmp1 > 0x80000000:
        tmp1 = tmp1 - 0x100000000
    return tmp1

def EncodeArtTit(str):
    rtn = ''
    str = str.encode('UTF-16')[2:]
    for i in range(len(str)):
        rtn += '%02x' % (str[i])

    return rtn

def fetch_lyrics(artist, title):
    # fixed headers
    headers =  {'User-agent' : 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)'}

    try:
        url = 'http://ttlrcct2.qianqian.com/dll/lyricsvr.dll?sh?Artist={}&Title={}&Flags=0'.format(
                EncodeArtTit(artist.replace(' ','').lower()),
                EncodeArtTit(title.replace(' ','').lower()),
                )
        req = Request(url, None, headers)
        handle = urlopen(req)
    except IOError:
        return '[00:00.00]Lyrics fetching failed.'
    else:
        dom = parseString(handle.read())
        list = dom.getElementsByTagName('lrc')
        li = []
        for node in list:
            li.append((node.getAttribute('id'),node.getAttribute('artist'),node.getAttribute('title')))

        # only use the first element
        if not li:
            return '[00:00.00]Lyrics not found.'
        li = li[0]

        try:
            url = 'http://ttlrcct2.qianqian.com/dll/lyricsvr.dll?dl?Id=%d&Code=%d&uid=01&mac=%012x' % (
                    int(li[0]),
                    CodeFunc(int(li[0]), (li[1] + li[2]).encode('UTF-8')),
                    random.randint(0,0xFFFFFFFFFFFF)
                    )
            req = Request(url, None, headers)
            handle = urlopen(req)
            # and open it to return a handle on the url
        except IOError:
            return '[00:00.00]Lyrics not found.'
        else:
            return handle.read().decode()

if __name__ == '__main__':
    print(fetch_lyrics(sys.argv[1], sys.argv[2]))

