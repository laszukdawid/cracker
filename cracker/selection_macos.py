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


def selected_text_from_accessibility() -> str:
    ax = _framework("ApplicationServices")
    appkit = _framework("AppKit")
    # On the system-wide element this sets the timeout for every element, so a hung app can't stall us.
    ax.AXUIElementSetMessagingTimeout(ax.AXUIElementCreateSystemWide(), AX_TIMEOUT_S)
    front = appkit.NSWorkspace.sharedWorkspace().frontmostApplication()
    if front is None:
        return ""
    # The system-wide element's focused element fails with kAXErrorCannotComplete on recent macOS.
    app = ax.AXUIElementCreateApplication(front.processIdentifier())
    err, focused = ax.AXUIElementCopyAttributeValue(app, ax.kAXFocusedUIElementAttribute, None)
    if err != ax.kAXErrorSuccess or focused is None:
        return ""
    err, text = ax.AXUIElementCopyAttributeValue(focused, ax.kAXSelectedTextAttribute, None)
    if err != ax.kAXErrorSuccess or not text:
        return ""
    return str(text)


def send_copy_shortcut() -> None:
    """Press Cmd+C in the frontmost app, using the key that types "c" in the current layout."""
    from pynput.keyboard import Controller, Key, KeyCode

    vk = ANSI_C_KEYCODE
    try:
        from pynput._util.darwin import get_unicode_to_keycode_map

        vk = get_unicode_to_keycode_map().get("c", ANSI_C_KEYCODE)
    except Exception:
        pass  # Non-Latin layouts have no "c"; macOS maps Cmd shortcuts to the ANSI key there.

    controller = Controller()
    with controller.pressed(Key.cmd):
        controller.tap(KeyCode.from_vk(vk))


def snapshot_pasteboard(pasteboard: Any) -> PasteboardSnapshot:
    snapshot: PasteboardSnapshot = []
    for item in pasteboard.pasteboardItems() or []:
        data_by_type = {}
        for pb_type in item.types():
            data = item.dataForType_(pb_type)
            if data is not None:
                data_by_type[pb_type] = data
        snapshot.append(data_by_type)
    return snapshot


def restore_pasteboard(pasteboard: Any, snapshot: PasteboardSnapshot, make_item: Callable[[], Any]) -> None:
    pasteboard.clearContents()
    items = []
    for data_by_type in snapshot:
        item = make_item()
        for pb_type, data in data_by_type.items():
            item.setData_forType_(data, pb_type)
        items.append(item)
    if items:
        pasteboard.writeObjects_(items)


def selected_text_from_copy(
    pasteboard: Any,
    string_type: str,
    make_item: Callable[[], Any],
    send_copy: Callable[[], None] = send_copy_shortcut,
    timeout: float = COPY_TIMEOUT_S,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> str:
    """Copy the selection via Cmd+C, read it, then restore the clipboard that was there before."""
    before = pasteboard.changeCount()
    snapshot = snapshot_pasteboard(pasteboard)
    send_copy()

    deadline = clock() + timeout
    text = None
    while clock() < deadline:
        if pasteboard.changeCount() != before:
            # Apps clear the pasteboard before writing, so wait for the string to land.
            text = pasteboard.stringForType_(string_type)
            if text is not None:
                break
        sleep(POLL_INTERVAL_S)

    if pasteboard.changeCount() == before:
        return ""  # Nothing was selected, or the app ignored Cmd+C; the clipboard is untouched.
    restore_pasteboard(pasteboard, snapshot, make_item)
    return str(text) if text else ""


def get_selected_text() -> str:
    text = selected_text_from_accessibility()
    if text.strip():
        return text

    appkit = _framework("AppKit")
    return selected_text_from_copy(
        pasteboard=appkit.NSPasteboard.generalPasteboard(),
        string_type=appkit.NSPasteboardTypeString,
        make_item=lambda: appkit.NSPasteboardItem.alloc().init(),
    )
