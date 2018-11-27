# ncmpy - A curses-based MPD client written in Python

----

**ncmpy** is a curses-based client for the [Music Player Daemon][mpd].

## Features

-   Playback control.
-   Queue control.
-   Song rating.
-   Database control.
-   Auto lyrics fetching and saving.
-   Lyrics highlighting.
-   Artist-Album view.
-   Search by tags.
-   Output control.

## One-Step Install

To install ncmpy, run:

    python2 setup.py install --prefix=/usr

To start ncmpy, run:

    ncmpy

## Configuration Files

System configuration file is /etc/ncmpy.conf.

User configuration file is ~/.config/ncmpy/ncmpy.conf.

Configuration sample is /usr/share/ncmpy/ncmpy.conf.example.

Enjoy!

## License

See LICENSE.

----

## Acknowledgements

Lyrics plugin is adapted from ttplyrics: http://code.google.com/p/ttplyrics/


[mpd]: http://musicpd.org/
