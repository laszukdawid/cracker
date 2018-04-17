=============
aws-polly-gui
=============
Usable GUI for AWS Polly text-to-speech service.

Installation
============

*PyQt5* is used to display GUI. To install PyQt5 head off to their `installation page <http://pyqt.sourceforge.net/Docs/PyQt5/installation.html>`_.
If you are trying this on Ubuntu then simple `apt` command should do

    $ sudo apt install python-qt5-dev-tools

For all other components use 

    $ pip install -r requirements.txt


Usage
=====

Since this is a GUI on top of `AWS Polly <https://aws.amazon.com/polly/>`_ it is assumed that one has credentials stored in default directory. This is `~/.aws/credentials` on unix based systems.

Currently reading out is performed by downloading mp3 format of the request and then using `mpg123` to play it. This isn't optimal and should be changed, but, for now, it works.

Suggested execution command

    $ cd aws-polly-gui
    $ python -m aws_polly_gui.main
