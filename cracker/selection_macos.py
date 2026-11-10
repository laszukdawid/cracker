"""Read the text selected in the frontmost macOS app.

The Accessibility API is tried first because it leaves the clipboard alone. Apps that
don't expose their selection (many browsers and Electron apps) get a simulated Cmd+C
instead, after which the previous clipboard contents are put back.
"""

import importlib
import time
from typing import Any, Callable

AX_TIMEOUT_S = 0.5
COPY_TIMEOUT_S = 0.6
POLL_INTERVAL_S = 0.02
ANSI_C_KEYCODE = 8

PasteboardSnapshot = list[dict[str, Any]]


def _framework(name: str) -> Any:
    # Imported lazily so the module loads (and type-checks) where pyobjc isn't installed.
    return importlib.import_module(name)


def is_trusted(prompt: bool = False) -> bool:
    """Whether Cracker may use Accessibility; ``prompt`` asks macOS to show the grant dialog."""
    ax = _framework("ApplicationServices")
    return bool(ax.AXIsProcessTrustedWithOptions({ax.kAXTrustedCheckOptionPrompt: prompt}))


def selected_text_from_accessibility(pid: int) -> str:
    """Selected text of the focused element in the app with ``pid``, or "" if it doesn't expose one."""
    ax = _framework("ApplicationServices")
    # On the system-wide element this sets the timeout for every element, so a hung app can't stall us.
    ax.AXUIElementSetMessagingTimeout(ax.AXUIElementCreateSystemWide(), AX_TIMEOUT_S)
    # The system-wide element's focused element fails with kAXErrorCannotComplete on recent macOS.
    app = ax.AXUIElementCreateApplication(pid)
    err, focused = ax.AXUIElementCopyAttributeValue(app, ax.kAXFocusedUIElementAttribute, None)
    if err != ax.kAXErrorSuccess or focused is None:
        return ""
    err, text = ax.AXUIElementCopyAttributeValue(focused, ax.kAXSelectedTextAttribute, None)
    if err != ax.kAXErrorSuccess or not text:
        return ""
    return str(text)


CMD_MODIFIER_STATE = 0x0100 >> 8  # Carbon cmdKey, in UCKeyTranslate's modifier-state units


def copy_keycode() -> int:
    """The key that gives "c" while Cmd is held; layouts such as "Dvorak - QWERTY ⌘" switch keys under Cmd."""
    try:
        from pynput._util.darwin import keycode_context, keycode_to_string

        with keycode_context() as context:
            for vk in [ANSI_C_KEYCODE, *range(128)]:
                if keycode_to_string(context, vk, CMD_MODIFIER_STATE).lower() == "c":
                    return vk
    except Exception:
        pass
    # Non-Latin layouts have no "c"; macOS maps Cmd shortcuts to the ANSI key there.
    return ANSI_C_KEYCODE


def send_copy_shortcut() -> None:
    """Press Cmd+C in the frontmost app."""
    from pynput.keyboard import Controller, Key, KeyCode

    controller = Controller()
    with controller.pressed(Key.cmd):
        controller.tap(KeyCode.from_vk(copy_keycode()))


class SelectionError(Exception):
    """A failure the user should see; the message is shown in the status bar."""


class SelectionCancelled(Exception):
    """The request was cancelled before Cmd+C was sent; nothing was changed."""


def snapshot_pasteboard(pasteboard: Any) -> PasteboardSnapshot:
    """Copy every item and format on the pasteboard, or raise if any can't be read back."""
    items = pasteboard.pasteboardItems()
    if items is None:  # nil means the read failed, not an empty clipboard
        raise SelectionError("couldn't read the clipboard, so it was left alone")
    snapshot: PasteboardSnapshot = []
    for item in items:
        data_by_type = {}
        for pb_type in item.types():
            data = item.dataForType_(pb_type)
            if data is None:
                raise SelectionError("the clipboard holds data that can't be backed up, so it was left alone")
            data_by_type[pb_type] = data
        snapshot.append(data_by_type)
    return snapshot


def prepare_restore_items(snapshot: PasteboardSnapshot, make_item: Callable[[], Any]) -> list[Any]:
    """Build the pasteboard items that put ``snapshot`` back, before anything is changed."""
    items = []
    for data_by_type in snapshot:
        item = make_item()
        for pb_type, data in data_by_type.items():
            if not item.setData_forType_(data, pb_type):
                raise SelectionError("the clipboard holds data that can't be backed up, so it was left alone")
        items.append(item)
    return items


def restore_pasteboard(pasteboard: Any, items: list[Any]) -> None:
    pasteboard.clearContents()
    if items and not pasteboard.writeObjects_(items):
        raise SelectionError("couldn't restore the previous clipboard")


def selected_text_from_copy(
    pasteboard: Any,
    string_type: str,
    make_item: Callable[[], Any],
    send_copy: Callable[[], None] = send_copy_shortcut,
    before_copy: Callable[[], None] = lambda: None,
    timeout: float = COPY_TIMEOUT_S,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> str:
    """Copy the selection via Cmd+C, read it, then restore the clipboard that was there before.

    ``before_copy`` runs right before Cmd+C and may raise to abort with nothing changed. The first
    clipboard change after Cmd+C is taken to be the copy: another copy inside ``timeout`` can't be told
    apart from it, and one that lands after ``timeout`` isn't undone. A copy made after ours is kept.
    """
    before = pasteboard.changeCount()
    items = prepare_restore_items(snapshot_pasteboard(pasteboard), make_item)
    if pasteboard.changeCount() != before:
        raise SelectionError("the clipboard changed while it was being backed up; try again")
    before_copy()

    text = None
    copy_count = None
    try:
        send_copy()
        deadline = clock() + timeout
        while clock() < deadline:
            count = pasteboard.changeCount()
            if count != before:
                # Apps clear the pasteboard before writing, so wait for the string to land.
                text = pasteboard.stringForType_(string_type)
                if text is not None:
                    # Counted before the read, so a copy made after it shows up as a newer count.
                    copy_count = count
                    break
            sleep(POLL_INTERVAL_S)
    finally:
        current = pasteboard.changeCount()
        if current != before and (copy_count is None or current == copy_count):
            restore_pasteboard(pasteboard, items)
    return str(text) if text else ""


def get_selected_text(should_continue: Callable[[], bool] = lambda: True) -> str:
    appkit = _framework("AppKit")
    workspace = appkit.NSWorkspace.sharedWorkspace()
    front = workspace.frontmostApplication()
    if front is None:
        return ""
    pid = front.processIdentifier()

    text = selected_text_from_accessibility(pid)
    if text.strip():
        return text

    def before_copy() -> None:
        if not should_continue():
            raise SelectionCancelled()
        # Earlier steps can take a while; don't send Cmd+C to an app the user has switched to.
        current = workspace.frontmostApplication()
        if current is None or current.processIdentifier() != pid:
            raise SelectionError("the app in front changed before its selection could be copied")

    return selected_text_from_copy(
        pasteboard=appkit.NSPasteboard.generalPasteboard(),
        string_type=appkit.NSPasteboardTypeString,
        make_item=lambda: appkit.NSPasteboardItem.alloc().init(),
        before_copy=before_copy,
    )
