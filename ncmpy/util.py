#!/usr/bin/env python3

'''
util module;
'''

def format_time(tm):

    '''
    convert time from `{seconds}` to `{hh:mm:ss}`;
    '''

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

def lrc_basename(title, artist):
    _title = (title or '').replace('/', '_')
    _artist = (artist or '').replace('/', '_')
    _basename = f'{_artist} - {_title}.lrc'
    return _basename

