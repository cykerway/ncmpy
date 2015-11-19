#!/usr/bin/python2

'''Config module.'''

import os

from ncmpy.util import printerr

# conf files listed in order.
CONFIG_FILES = [
        os.path.expanduser('~/.config/ncmpy/ncmpy.conf'),
        '/etc/ncmpy.conf'
        ]

class Config:
    '''Config class.'''

    def __init__(self):
        self.mpd_host = 'localhost'
        self.mpd_port = 6600
        self.enable_osd = False
        self.enable_rating = True
        self.lyrics_dir = os.path.expanduser('~/.ncmpy/lyrics')

    def read(self):
        '''Read configurations from file.'''

        for filename in CONFIG_FILES:

            if not os.path.isfile(filename):
                continue

            with open(filename, 'rt') as f:
                line_num = 0
                for l in f:
                    line_num += 1

                    if l.startswith('#'):
                        continue

                    try:
                        o, a = map(str.strip, l.split('=', 1))

                        if o == 'MPD_HOST':
                            self.mpd_host = a
                        elif o == 'MPD_PORT':
                            self.mpd_port = int(a)
                        elif o == 'ENABLE_OSD':
                            self.enable_osd = a in ['True', 'true', 'Yes', 'yes', '1']
                        elif o == 'ENABLE_RATING':
                            self.enable_rating = a in ['True', 'true', 'Yes', 'yes', '1']
                        elif o == 'LYRICS_DIR':
                            self.lyrics_dir = os.path.expanduser(a)
                        else:
                            raise
                    except:
                        printerr('Invalid line {} in config file {}'.format(line_num, filename))
            break

