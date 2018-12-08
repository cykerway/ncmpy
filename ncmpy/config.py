#!/usr/bin/env python3

'''
config module;
'''

from os.path import expanduser
from types import SimpleNamespace as namespace
import yaml

from ncmpy.keysym import keysym as ks
from ncmpy.keysym import name2code as n2c

##  config;
conf = namespace()

##  default config values;
conf.mpd_host = 'localhost'
conf.mpd_port = 6600
conf.rate_song = True
conf.lyrics_dir = expanduser('~/.ncmpy/lyrics')

##  read config files;
for fname in [
    expanduser('~/.config/ncmpy/ncmpy.yaml'),
    '/etc/ncmpy/ncmpy.yaml',
]:
    try:
        with open(fname, 'rt') as fp:
            data = yaml.load(fp)
    except:
        continue

    ##  update config values;
    if data.get('mpd_host') is not None:
        conf.mpd_host = data.get('mpd_host')
    if data.get('mpd_port') is not None:
        conf.mpd_port = data.get('mpd_port')
    if data.get('rate_song') is not None:
        conf.rate_song = data.get('rate_song')
    if data.get('lyrics_dir') is not None:
        conf.lyrics_dir = expanduser(data.get('lyrics_dir'))

    ##  update keysyms;
    if data.get('keysym') is not None:
        for sym, name in data.get('keysym').items():
            if hasattr(ks, sym):
                setattr(ks, sym, n2c(name))
            else:
                raise Exception('invalid keysym: {}'.format(sym))

    ##  break after config read;
    break

