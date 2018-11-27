#!/usr/bin/env python3

'''Config module.'''

import os
import sys

from ncmpy.util import printerr

class Config:
    '''Config class.'''

    def __init__(self):
        self.mpd_host = 'localhost'
        self.mpd_port = 6600
        self.enable_rating = True
        self.lyrics_dir = os.path.expanduser('~/.ncmpy/lyrics')

        for filename in (
                os.path.expanduser('~/.config/ncmpy/ncmpy.conf'),
                '/etc/ncmpy/ncmpy.conf',
                ):

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
                        elif o == 'ENABLE_RATING':
                            self.enable_rating = a in ['True', 'true', 'Yes', 'yes', '1']
                        elif o == 'LYRICS_DIR':
                            self.lyrics_dir = os.path.expanduser(a)
                        else:
                            raise
                    except:
                        printerr('Invalid line {} in config file {}'.format(line_num, filename))
                        sys.exit(1)
            break

# Global configuration.
conf = Config()

