# macOS development

PyQt6 publishes binary wheels for Intel and Apple Silicon macOS. No Homebrew Qt installation is required.

```shell
uv sync --all-extras
make run
```

## Global shortcut permission

The global "read clipboard" shortcut (Ctrl + Shift + Space) listens to the keyboard through `pynput`. macOS
blocks that until the app that launched Cracker is allowed in **System Settings → Privacy & Security →
Input Monitoring** (and **Accessibility** on some macOS versions). When running from a terminal, allow the
terminal app (Terminal, iTerm, Ghostty, ...), then restart it. Without the permission, Cracker still runs and
the in-window shortcuts work; only the global shortcut does nothing.
