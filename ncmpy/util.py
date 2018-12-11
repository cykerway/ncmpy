#!/usr/bin/env python3

'''
util module;
'''

import re

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

def lrc_parse(lrc):

    '''
    parse lrc string;
    '''

    _tag = re.compile(r'\[([a-z][a-z]):(.*)\]')
    _tm = re.compile(r'\[(\d\d):(\d\d).(\d\d)\](.*)')

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
        raise Exception('cannot parse lrc')
    finally:
        return tags, tms

