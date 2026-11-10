# macOS development

PyQt6 publishes binary wheels for Intel and Apple Silicon macOS. No Homebrew Qt installation is required.

```shell
uv sync --all-extras
make run
```

## Global shortcut permission

The global shortcuts (Ctrl + Shift + Space and F6) listen to the keyboard through `pynput`. macOS
blocks that until the app that launched Cracker is allowed in **System Settings → Privacy & Security →
Input Monitoring** (and **Accessibility** on some macOS versions). When running from a terminal, allow the
terminal app (Terminal, iTerm, Ghostty, ...), then restart it. Without the permission, Cracker still runs and
the in-window shortcuts work; only the global shortcut does nothing.

## Reading selected text (F6)

F6 reads the text selected in the app in front. It needs the **Accessibility** permission for the app that
launched Cracker; the first press without it opens the macOS prompt. Reading works as soon as it's granted;
restart Cracker so F6 is also kept from the app in front (see below).

- **Function keys:** Mac keyboards send a system action for F6 by default, so press **fn + F6**, or enable
  System Settings → Keyboard → Keyboard Shortcuts → Function Keys → "Use F1, F2, etc. keys as standard
  function keys".
- **How the text is fetched:** Cracker first asks the app for its selection through the Accessibility API, which
  leaves the clipboard alone. Apps that don't answer (many browsers and Electron apps) get a simulated ⌘C;
  Cracker reads the copied text and then puts the previous clipboard back. Clipboard managers may still record
  that copy.
- **The key isn't passed on:** with Accessibility granted, F6 is kept from the app in front, so it doesn't
  trigger that app's own F6 action (Firefox, for example, jumps to the address bar).
