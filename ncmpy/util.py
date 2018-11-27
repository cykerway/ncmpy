#!/usr/bin/env python3

'''Util module.'''

import sys

def printerr(s):
    sys.stderr.write(s + '\n')

def format_time(tm):
    '''Convert time: <seconds> -> <hh:mm:ss>.'''

    if tm.isdigit():
        tm = int(tm)
        h, m, s = tm // 3600, (tm // 60) % 60, tm % 60
        return '{}:'.format(h) * bool(h > 0) + '{:02d}:{:02d}'.format(m, s)
    else:
        return ''

def get_tag(tagname, item):
    tag = item.get(tagname)
    if isinstance(tag, str):
        return tag
    elif isinstance(tag, list):
        return ', '.join(tag)
    else:
        return None

