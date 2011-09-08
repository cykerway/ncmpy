#!/usr/bin/python2

from distutils.core import setup, Extension
import glob

setup(
    name = 'ncmpy', 
    version = '1.0', 
    author = 'Cyker Way', 
    author_email = 'cykerway@gmail.com', 
    url = 'http://ncmpy.cykerway.com/', 
    description = 'A [Python + Curses]-based MPD client', 
    long_description = '''
        ncmpy - a [Python + Curses]-based MPD client
        ============================

        ncmpy is an MPD client based on Curses. Besides:

            basic playback control, 
            playlist/database management, 
            
        it supports:
        
            song rating, 
            auto lyrics fetching and saving, 
            lyrics highlighting and OSD, 
            searching by tags.
    ''', 
    classifiers = [
        'Development Status :: 5 - Production/Stable', 
        'Intended Audience :: End Users/Desktop', 
        'License :: OSI Approved :: GNU General Public License (GPL)', 
        'Topic :: Multimedia :: Sound/Audio :: Players', 
        'Programming Language :: Python :: 2.7',
        ], 
    license = 'GPL3', 
    requires = ['curses', 'httplib2', 'lxml', 'mpd', 'pyosd'], 
    packages = ['ncmpy'], 
    package_dir = {'ncmpy':'src'}, 
    scripts = ['ncmpy'], 
    data_files = [
        ('share/doc/ncmpy', ['INSTALL', 'README']), 
        ('share/ncmpy', glob.glob('share/*')), 
        ]
    )
