#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
# LRC engine for ncmpy.
# 
# Copyright (C) 2011 Cyker Way
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

import re

class LRCParseError(Exception):
    pass

_tag = re.compile(r'\[([a-z][a-z]):(.*)\]')
_tm = re.compile(r'\[(\d\d):(\d\d).(\d\d)\](.*)')

def parse(lrc):
    tags = {}
    tms = {}

    try:
        lines = lrc.splitlines()
        for line in lines:
            line = line.strip()
            m = _tag.match(line)
            if m:
                tagkey, tagval = m.groups()
                tags[tagkey] = tagval.strip()
            else:
                # handle multiple tms, like [mm:ss.xx]<mm:ss.xx>...
                matched_tms = []
                m = _tm.match(line)
                while m:
                    mm, ss, xx, line = m.groups()
                    tm = float(mm) * 60 + float(ss) + float(xx) * 0.01
                    matched_tms.append(tm)
                    m = _tm.match(line)
                for tm in matched_tms:
                    tms[tm] = line
    except:
        raise LRCParseError('Cannot Parse')
    finally:
        return tags, tms


def get_title(lrc):
    tags, tms = parse(lrc)
    return tags.get('ti')


def get_artist(lrc):
    tags, tms = parse(lrc)
    return tags.get('ar')


def get_album(lrc):
    tags, tms = parse(lrc)
    return tags.get('al')


def get_by(lrc):
    tags, tms = parse(lrc)
    return tags.get('by')


def get_text(lrc):
    tags, tms = parse(lrc)
    for tm in sorted(tms.keys()):
        yield tms.get(tm)


def compile(lrc):
    return LRC(*parse(lrc))


class LRC():
    def __init__(self, tags, tms):
        self.tags, self.tms = tags, tms
    def parse(self):
        return self.tags, self.tms
    def get_title(self):
        return self.tags.get('ti')
    def get_artist(self):
        return self.tags.get('ar')
    def get_album(self):
        return self.tags.get('al')
    def get_by(self):
        return self.tags.get('by')
    def get_text(self):
        for tm in sorted(self.tms.keys()):
            yield self.tms.get(tm)

def test():
    with open('./test.lrc', 'rt') as f:
        s = f.read()

    print 'module method (no compile)'
    lrc = compile(s)
    print 'artist = ', lrc.get_artist()
    print 'title = ', lrc.get_title()
    print 'album = ', lrc.get_album()
    print 'by = ', lrc.get_by()
    texts = lrc.get_text()
    for text in texts:
        print text

    print 'class method (compile)'
    print 'artist = ', get_artist(s)
    print 'title = ', get_title(s)
    print 'album = ', get_album(s)
    print 'by = ', get_by(s)
    texts = get_text(s)
    for text in texts:
        print text


if __name__ == '__main__':
    test()
