#!/usr/bin/python2

from distutils.core import setup, Extension

setup(
        name = 'mpy', 
        version = '1.0', 
        author = 'Cyker Way', 
        author_email = 'cykerway@gmail.com', 
        url = 'http://mpy.cykerway.com/', 
        description = 'A [Python + Curses]-based MPD client', 
        license = 'GPLv3', 
        requires = ['curses', 'httplib2', 'lxml', 'pyosd'], 
        packages = ['mpy'], 
        package_dir = {'mpy':'src'}, 
        scripts = ['mpy'], 
        )
