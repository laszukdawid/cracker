# Cracker

Usable GUI for text-to-speech services (mainly AWS Polly and ESpeak).

## Why all of this

### What can you do with it?

I (the author) have difficulty to focus on only reading.
The best way to read is to walk and have white noise in the background but that isn't always possible.
The other best way is to read both with eyes and ears.
When someone reads and I can follow, I don't overly focus on how some words look weird
or continue the line even though there is no text remaining.
When someone reads what I see, it sets the pace and helps me remember/reference more easily.

### Is it only reader?

Text often have footnotes, emoji, and other decorators.
These can be visually pleasing but machine needs simple text.
Cracker also provide text (de)formatters so to simplify text for Speakers.
Examples of deformatters include removal of extensive whitespace, cryptic citation references and wikipedia decorators.

### Is this an active project?

Kind of. I update it as I need it. It hasn't been touched in a while because of plenty of problems
with (Py)Qt on Linux and increased popularity of Electron (see [Pollytron](https://github.com/laszukdawid/pollytron)).
But, things have changed, and Qt is even better (and Electron is meh).
I'm going to update *Cracker* as needed. Anyone and everyone is welcome to contribute or submit features request.

## Installation

It should be enough to checkout this package and install it's dependencies with `pip`

    
```shell
$ git clone git@github.com:laszukdawid/cracker.git
$ cd cracker
$ pip install -e .
```

Now you can launch Cracker. See [Usage](#usage) section below.

### Old instructions but might be necessary

*PyQt5* is used to display GUI. To install PyQt5 head off to their [installation page](http://pyqt.sourceforge.net/Docs/PyQt5/installation.html).
Package is currently heavily favouring Ubuntu as end OS. If you are one of the lucky ones then the installation requires:

```shell
$ sudo sh install.sh
$ pip install -r requirements.txt
```

For other OS you'd need *PyQt5* and *vlc*. 

If you're on Ubuntu you'll most likely need additional `gstreamer` packages. Otherwise you'll see something like `defaultServiceProvider::requestService(): no service found for - "org.qt-project.qt.mediaplayer"`.

## Usage

Since this is a GUI on top of [AWS Polly](https://aws.amazon.com/polly/) it is assumed that one has credentials stored in default directory. This is `~/.aws/credentials` on unix based systems.

Currently reading out is performed by downloading mp3 format of the request and then using `mpg123` to play it. This isn't optimal and should be changed, but, for now, it works.

Suggested execution command

```bash
$ cd cracker
$ python -m cracker.main
```

## Key shortcuts

There's only one global command (read from clipboard).
All commands are expected to be called when Cracker is in focus.

| Action               | Shortcut            | Global |
|----------------------|---------------------|--------|
| Read (clipboard)     | Ctr + Shift + Space | Yes    |
| Read (text area)     | Ctr + Shift + R     | No     |
| Pause / Resume read  | Ctr + Space         | No     |
| Stop reading         | Ctr + Shift + S     | No     |
| Reduce (all active)  | Ctr + R             | No     |
| Reduce (wiki)        | Ctr + Shift + W     | No     |
| Reduce (citation)    | Ctr + Shift + C     | No     |
