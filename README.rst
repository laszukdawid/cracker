=============
aws-polly-gui
=============
Usable GUI for AWS Polly text-to-speech service.

Installation
============

It should be enough to checkout this package and install it's dependencies with `pip`

.. code-block:: bash
    
    $ pip install -e .

Old instructions but might be necessary
---------------------------------------

*PyQt5* is used to display GUI. To install PyQt5 head off to their `installation page <http://pyqt.sourceforge.net/Docs/PyQt5/installation.html>`_.
Package is currently heavily favouring Ubuntu as end OS. If you are one of the lucky ones then the installation requires:

.. code-block:: bash

    $ sudo sh install.sh
    $ pip install -r requirements.txt

For other OS you'd need *PyQt5* and *vlc*. 

If you're on Ubuntu you'll most likely need additional `gstreamer` packages. Otherwise you'll see something like `defaultServiceProvider::requestService(): no service found for - "org.qt-project.qt.mediaplayer"`.

Usage
=====

Since this is a GUI on top of `AWS Polly <https://aws.amazon.com/polly/>`_ it is assumed that one has credentials stored in default directory. This is `~/.aws/credentials` on unix based systems.

Currently reading out is performed by downloading mp3 format of the request and then using `mpg123` to play it. This isn't optimal and should be changed, but, for now, it works.

Suggested execution command

.. code-block:: bash

    $ cd aws-polly-gui
    $ python -m aws_polly_gui.main

