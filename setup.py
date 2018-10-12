#!/usr/bin/python2

from setuptools import setup, find_packages
import glob

setup(
    name = 'ncmpy',
    version = '1.4.0',
    author = 'Cyker Way',
    url = 'https://repo.cykerway.com/ncmpy',
    description = 'A curses-based MPD client written in Python.',
    long_description = '''
        ncmpy - A curses-based MPD client written in Python
        ============================

        ncmpy is a curses-based MPD client. Features:

            Playback control.
            Queue control.
            Song rating.
            Database control.
            Auto lyrics fetching and saving.
            Lyrics highlighting.
            Artist-Album view.
            Search by tags.
            Output control.
    ''',
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Topic :: Multimedia :: Sound/Audio :: Players',
        'Programming Language :: Python :: 2.7',
        ],
    requires = ['curses', 'mpd'],
    packages=find_packages(),
    scripts=glob.glob('scripts/*'),
    project_urls={
        'Source': 'https://github.com/cykerway/ncmpy',
    },
)
