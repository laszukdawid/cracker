# Cracker

Usable GUI for text-to-speech services.

## Supported text-to-speech

* ESpeak -- https://en.wikipedia.org/wiki/ESpeak
* AWS Polly -- https://aws.amazon.com/polly/
* Google TextToSpeech -- https://cloud.google.com/text-to-speech/

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

It should be enough to install via `pip`, i.e.

```shell
$ pip install cracker
```

See [Usage](#usage) section below.

### Development

Development requires Python 3.14. The project uses [uv](https://docs.astral.sh/uv/) for dependency management and
reproducible environments, and [Task](https://taskfile.dev/installation/) (`brew install go-task`) to run common commands:

```shell
task install-all
task test
task format-check
task typecheck
task build
```

Run `task check` before opening a pull request to execute Ruff checks, ty type checking, tests, and a package build.
`task` on its own lists every task.
See [Dependency policy](docs/dependencies.md) for version constraints and update procedures.

*PyQt6* is used for the desktop GUI and multimedia playback. Its binary wheels include the corresponding Qt
libraries, so `uv sync` or `pip install cracker` installs the required Python and Qt components.

On Ubuntu, the PulseAudio and Qt X11 compatibility libraries may also be required:

```shell
sudo apt-get install libpulse-mainloop-glib0 libegl1 libxcb-cursor0 libxkbcommon-x11-0
```

See [macOS development notes](docs/macos.md) for the macOS setup.

## Usage

Since this is a GUI on top of [AWS Polly](https://aws.amazon.com/polly/) it is assumed that one has credentials stored in default directory. This is `~/.aws/credentials` on unix based systems.

AWS IAM Identity Center (SSO) profiles can be configured from **Config → Speakers**. Enter the profile, SSO
session, start URL, SSO region, account ID, role, and Polly region, then choose **Save and sign in with SSO**.
Cracker writes the standard AWS shared configuration and starts `aws sso login`; this sign-in action requires
[AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).

Cloud backends download audio to Cracker's cache and play it through Qt Multimedia.

Start it with the `cracker` command after `pip install cracker`, or from a checkout:

```shell
task run             # same as: uv run cracker
task run -- --debug  # same as: uv run cracker --debug
```

## Key shortcuts

Two commands are global and work while another app is in front; the rest need Cracker in focus.
Pressing a global shortcut while Cracker is reading stops it.

On macOS, Qt turns the in-window <kbd>Ctrl</kbd> shortcuts into <kbd>⌘</kbd>. The global shortcuts are read
from the keyboard directly, so they use the real <kbd>Ctrl</kbd> (<kbd>⌃</kbd>) key on every platform.

| Action                 | Windows / Linux      | macOS        | Global |
|------------------------|----------------------|--------------|--------|
| Read clipboard         | Ctrl + Shift + Space | ⌃ ⇧ Space    | Yes    |
| Read selected text     | F6                   | F6 (fn + F6) | Yes    |
| Read text area         | Ctrl + R             | ⌘ R          | No     |
| Read clipboard         | Ctrl + Shift + R     | ⌘ ⇧ R        | No     |
| Pause / resume         | Ctrl + Space         | ⌘ Space ¹    | No     |
| Stop                   | Ctrl + Shift + S     | ⌘ ⇧ S        | No     |
| Reduce wiki citations  | Ctrl + Shift + W     | ⌘ ⇧ W        | No     |
| Reduce citations       | Ctrl + Shift + C     | ⌘ ⇧ C        | No     |
| Save config            | Ctrl + S             | ⌘ S          | No     |
| Quit                   | Ctrl + Q             | ⌘ Q          | No     |

¹ ⌘ Space opens Spotlight by default, so on macOS use the pause button unless that shortcut is changed in
System Settings → Keyboard → Keyboard Shortcuts → Spotlight.

"Reduce" (all active rules) is in the toolbar and menu and has no shortcut.

The global shortcuts can be changed in `~/.config/cracker/settings.yaml` using
[pynput key names](https://pynput.readthedocs.io/en/latest/keyboard.html#pynput.keyboard.Key):

```yaml
shortcuts:
  read_clipboard: [ctrl, shift, space]
  read_selection: [f6]
```

On Linux, "selected text" is the X11/Wayland primary selection. On macOS, see the
[macOS notes](docs/macos.md#reading-selected-text-f6).
