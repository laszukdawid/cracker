import sys
import threading
from unittest.mock import MagicMock

import pytest
from PyQt6.QtGui import QClipboard

from cracker import selection_macos
from cracker.selection import ACCESSIBILITY_HINT, SelectionReader

STRING = "public.utf8-plain-text"


class FakeItem:
    def __init__(self, data=None):
        self.data = dict(data or {})

    def types(self):
        return list(self.data)

    def dataForType_(self, pb_type):
        return self.data.get(pb_type)

    def setData_forType_(self, data, pb_type):
        self.data[pb_type] = data
        return True


class FakePasteboard:
    def __init__(self, items):
        self.items = items
        self.count = 1

    def changeCount(self):
        return self.count

    def pasteboardItems(self):
        return self.items

    def stringForType_(self, pb_type):
        for item in self.items:
            if pb_type in item.data:
                return item.data[pb_type]
        return None

    def clearContents(self):
        self.items = []
        self.count += 1

    def writeObjects_(self, items):
        self.items = list(items)
        return True

    def app_copies(self, text):
        self.clearContents()
        self.items = [FakeItem({STRING: text})]


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def _copy(pasteboard, send_copy, timeout=0.6):
    clock = FakeClock()
    return selection_macos.selected_text_from_copy(
        pasteboard,
        STRING,
        make_item=FakeItem,
        send_copy=send_copy,
        timeout=timeout,
        sleep=clock.sleep,
        clock=clock,
    )


def test_copy_returns_selection_and_restores_previous_clipboard():
    previous = {STRING: "previous", "public.rtf": b"{\\rtf1 previous}"}
    pasteboard = FakePasteboard([FakeItem(previous)])

    text = _copy(pasteboard, lambda: pasteboard.app_copies("selected words"))

    assert text == "selected words"
    assert [item.data for item in pasteboard.items] == [previous]


def test_copy_restores_empty_clipboard():
    pasteboard = FakePasteboard([])

    text = _copy(pasteboard, lambda: pasteboard.app_copies("selected"))

    assert text == "selected"
    assert pasteboard.items == []


def test_copy_without_selection_leaves_clipboard_untouched():
    pasteboard = FakePasteboard([FakeItem({STRING: "previous"})])
    before = pasteboard.count

    text = _copy(pasteboard, lambda: None)

    assert text == ""
    assert pasteboard.count == before
    assert pasteboard.items[0].data == {STRING: "previous"}


def test_copy_of_non_text_returns_empty_and_restores():
    pasteboard = FakePasteboard([FakeItem({STRING: "previous"})])

    def copy_image():
        pasteboard.clearContents()
        pasteboard.items = [FakeItem({"public.png": b"png"})]

    text = _copy(pasteboard, copy_image, timeout=0.1)

    assert text == ""
    assert pasteboard.items[0].data == {STRING: "previous"}


def test_copy_restores_clipboard_when_copy_raises():
    pasteboard = FakePasteboard([FakeItem({STRING: "previous"})])

    def copy_then_fail():
        pasteboard.app_copies("selected")
        raise RuntimeError("event post failed")

    with pytest.raises(RuntimeError):
        _copy(pasteboard, copy_then_fail)

    assert pasteboard.items[0].data == {STRING: "previous"}


def test_copy_refuses_when_clipboard_cannot_be_backed_up():
    class PromisedItem(FakeItem):
        def dataForType_(self, pb_type):
            return None

    pasteboard = FakePasteboard([PromisedItem({"com.apple.promise": b""})])
    send_copy = MagicMock()

    with pytest.raises(selection_macos.SelectionError):
        _copy(pasteboard, send_copy)

    send_copy.assert_not_called()


def test_unreadable_clipboard_aborts_before_copy():
    pasteboard = FakePasteboard([FakeItem({STRING: "previous"})])
    pasteboard.pasteboardItems = lambda: None  # what NSPasteboard returns on a read error
    send_copy = MagicMock()

    with pytest.raises(selection_macos.SelectionError):
        _copy(pasteboard, send_copy)

    send_copy.assert_not_called()


@pytest.mark.skipif(sys.platform != "darwin", reason="pynput macOS layout helpers")
@pytest.mark.parametrize(
    "cmd_layout, expected",
    [
        ({8: "c"}, 8),  # QWERTY, and "Dvorak - QWERTY Cmd" which switches to QWERTY under Cmd
        ({8: "j", 0x22: "c"}, 0x22),  # plain Dvorak keeps its layout under Cmd
        ({8: "с"}, 8),  # Cyrillic: no "c", macOS maps Cmd shortcuts to the ANSI key
    ],
)
def test_copy_keycode_uses_the_command_layout(monkeypatch, cmd_layout, expected):
    import contextlib

    from pynput._util import darwin

    monkeypatch.setattr(darwin, "keycode_context", lambda: contextlib.nullcontext((40, b"layout")))

    def keycode_to_string(context, vk, modifier_state=0):
        assert modifier_state == selection_macos.CMD_MODIFIER_STATE
        return cmd_layout.get(vk, "")

    monkeypatch.setattr(darwin, "keycode_to_string", keycode_to_string)

    assert selection_macos.copy_keycode() == expected


@pytest.mark.skipif(sys.platform != "darwin", reason="pynput macOS layout helpers")
@pytest.mark.parametrize("context", [None, (40, None), (40, b"layout")])
def test_unreadable_layout_raises_instead_of_guessing(monkeypatch, context):
    import contextlib

    from pynput._util import darwin

    monkeypatch.setattr(darwin, "keycode_context", lambda: contextlib.nullcontext(context))
    # UCKeyTranslate failing: pynput ignores its status and returns "".
    monkeypatch.setattr(darwin, "keycode_to_string", lambda context, vk, modifier_state=0: "")

    with pytest.raises(selection_macos.SelectionError):
        selection_macos.copy_keycode()


@pytest.mark.skipif(sys.platform != "darwin", reason="pynput macOS layout helpers")
def test_layout_lookup_failure_sends_no_keys(monkeypatch):
    from pynput import keyboard
    from pynput._util import darwin

    def broken_context():
        raise OSError("no layout data")

    monkeypatch.setattr(darwin, "keycode_context", broken_context)
    controller = MagicMock()
    monkeypatch.setattr(keyboard, "Controller", lambda: controller)

    send = selection_macos.copy_shortcut_sender()  # an unreadable layout only fails once the copy is needed
    with pytest.raises(selection_macos.SelectionError):
        send()

    controller.pressed.assert_not_called()
    controller.tap.assert_not_called()


def test_unbuildable_backup_aborts_before_copy():
    class BrokenItem(FakeItem):
        def setData_forType_(self, data, pb_type):
            return False

    pasteboard = FakePasteboard([FakeItem({STRING: "previous"})])
    send_copy = MagicMock()

    with pytest.raises(selection_macos.SelectionError):
        selection_macos.selected_text_from_copy(pasteboard, STRING, make_item=BrokenItem, send_copy=send_copy)

    send_copy.assert_not_called()
    assert pasteboard.items[0].data == {STRING: "previous"}


def test_restore_writes_the_backed_up_items():
    pasteboard = FakePasteboard([FakeItem({STRING: "selected"})])

    selection_macos.restore_pasteboard(pasteboard, [FakeItem({STRING: "previous", "public.rtf": b"rtf"})])

    assert [item.data for item in pasteboard.items] == [{STRING: "previous", "public.rtf": b"rtf"}]


def test_restore_reports_write_failure():
    pasteboard = FakePasteboard([FakeItem({STRING: "selected"})])
    pasteboard.writeObjects_ = lambda items: False

    with pytest.raises(selection_macos.SelectionError):
        selection_macos.restore_pasteboard(pasteboard, [FakeItem({STRING: "previous"})])


def test_copy_keeps_a_newer_copy_made_after_ours():
    class UserCopiesAfterRead(FakePasteboard):
        read_selection = False

        def stringForType_(self, pb_type):
            text = super().stringForType_(pb_type)
            if text == "selected" and not self.read_selection:
                self.read_selection = True
                self.copy_count = self.count
            return text

        def changeCount(self):
            # The user copies something right after Cracker has read the selection.
            if self.read_selection and self.count == self.copy_count:
                self.app_copies("user copy")
            return self.count

    pasteboard = UserCopiesAfterRead([FakeItem({STRING: "previous"})])

    text = _copy(pasteboard, lambda: pasteboard.app_copies("selected"))

    assert text == "selected"
    assert pasteboard.items[0].data == {STRING: "user copy"}


def test_before_copy_can_abort_without_changes():
    pasteboard = FakePasteboard([FakeItem({STRING: "previous"})])
    send_copy = MagicMock()

    def cancelled():
        raise selection_macos.SelectionCancelled()

    with pytest.raises(selection_macos.SelectionCancelled):
        selection_macos.selected_text_from_copy(
            pasteboard, STRING, make_item=FakeItem, send_copy=send_copy, before_copy=cancelled
        )

    send_copy.assert_not_called()
    assert pasteboard.items[0].data == {STRING: "previous"}


class FakeApp:
    def __init__(self, pid):
        self.pid = pid

    def processIdentifier(self):
        return self.pid


@pytest.mark.skipif(sys.platform != "darwin", reason="pynput macOS layout helpers")
def test_controller_layout_failure_is_reported_only_when_copy_is_needed(monkeypatch):
    from pynput import keyboard

    monkeypatch.setattr(selection_macos, "copy_keycode", lambda: 8)

    def broken_controller():
        raise OSError("layout unavailable during Controller initialization")

    monkeypatch.setattr(keyboard, "Controller", broken_controller)

    send = selection_macos.copy_shortcut_sender()  # must not raise: Accessibility may still work
    with pytest.raises(selection_macos.SelectionError, match="layout unavailable"):
        send()


def _fake_appkit(frontmost_pids):
    pids = iter(frontmost_pids)
    workspace = MagicMock()
    workspace.frontmostApplication.side_effect = lambda: FakeApp(next(pids))
    appkit = MagicMock()
    appkit.NSWorkspace.sharedWorkspace.return_value = workspace
    return appkit


def test_get_selected_text_prefers_accessibility(monkeypatch):
    monkeypatch.setattr(selection_macos, "_framework", lambda name: _fake_appkit([42]))
    monkeypatch.setattr(selection_macos, "selected_text_from_accessibility", lambda pid: f"from ax {pid}")
    copy = MagicMock()
    monkeypatch.setattr(selection_macos, "selected_text_from_copy", copy)

    assert selection_macos.get_selected_text(MagicMock()) == "from ax 42"
    copy.assert_not_called()


def _copy_that_runs_before_copy(**kwargs):
    kwargs["before_copy"]()
    return "copied"


def test_get_selected_text_does_not_copy_after_focus_change(monkeypatch):
    monkeypatch.setattr(selection_macos, "_framework", lambda name: _fake_appkit([42, 7]))
    monkeypatch.setattr(selection_macos, "selected_text_from_accessibility", lambda pid: "")
    monkeypatch.setattr(selection_macos, "selected_text_from_copy", _copy_that_runs_before_copy)

    with pytest.raises(selection_macos.SelectionError):
        selection_macos.get_selected_text(MagicMock())


def test_get_selected_text_skips_copy_when_cancelled(monkeypatch):
    monkeypatch.setattr(selection_macos, "_framework", lambda name: _fake_appkit([42, 42]))
    monkeypatch.setattr(selection_macos, "selected_text_from_accessibility", lambda pid: "")
    monkeypatch.setattr(selection_macos, "selected_text_from_copy", _copy_that_runs_before_copy)

    with pytest.raises(selection_macos.SelectionCancelled):
        selection_macos.get_selected_text(MagicMock(), should_continue=lambda: False)


def test_get_selected_text_copies_when_focus_is_unchanged(monkeypatch):
    monkeypatch.setattr(selection_macos, "_framework", lambda name: _fake_appkit([42, 42]))
    monkeypatch.setattr(selection_macos, "selected_text_from_accessibility", lambda pid: "")
    seen = {}
    monkeypatch.setattr(
        selection_macos, "selected_text_from_copy", lambda **kw: seen.update(kw) or _copy_that_runs_before_copy(**kw)
    )
    send_copy = MagicMock()

    assert selection_macos.get_selected_text(send_copy) == "copied"
    assert seen["send_copy"] is send_copy


def _no_copy():
    return lambda: None


def _reader(platform="darwin", fetch=lambda should_continue, send_copy: "hello", trusted=True, clipboard=None):
    reader = SelectionReader(
        clipboard or MagicMock(),
        platform=platform,
        fetch=fetch,
        prepare_copy=_no_copy,
        is_trusted=lambda prompt: trusted,
        start_thread=lambda target: target(),
    )
    texts, failures = [], []
    reader.textReady.connect(texts.append)
    reader.failed.connect(failures.append)
    return reader, texts, failures


def test_reader_emits_selected_text_on_macos():
    reader, texts, failures = _reader()

    reader.request()

    assert texts == ["hello"]
    assert failures == []


def test_reader_asks_for_accessibility_when_untrusted():
    fetch = MagicMock()
    reader, texts, failures = _reader(fetch=fetch, trusted=False)

    reader.request()

    assert texts == []
    assert failures == [ACCESSIBILITY_HINT]
    fetch.assert_not_called()


def test_reader_reports_fetch_errors_and_recovers():
    calls = []

    def fetch(should_continue, send_copy):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")
        return "second"

    reader, texts, failures = _reader(fetch=fetch)

    reader.request()
    reader.request()

    assert failures == ["Couldn't read the selected text: boom"]
    assert texts == ["second"]


def test_reader_drops_result_cancelled_by_stop():
    pending = []
    reader = SelectionReader(
        MagicMock(),
        platform="darwin",
        fetch=lambda should_continue, send_copy: "late text",
        prepare_copy=_no_copy,
        is_trusted=lambda prompt: True,
        start_thread=pending.append,
    )
    texts = []
    reader.textReady.connect(texts.append)

    reader.request()
    reader.cancel()
    pending[0]()

    assert texts == []


def test_reader_reports_errors_even_after_cancel():
    pending = []

    def fetch(should_continue, send_copy):
        raise selection_macos.SelectionError("couldn't restore the previous clipboard")

    reader = SelectionReader(
        MagicMock(),
        platform="darwin",
        fetch=fetch,
        prepare_copy=_no_copy,
        is_trusted=lambda prompt: True,
        start_thread=pending.append,
    )
    failures = []
    reader.failed.connect(failures.append)

    reader.request()
    reader.cancel()
    pending[0]()

    assert failures == ["Couldn't read the selected text: couldn't restore the previous clipboard"]


def test_reader_tells_fetch_to_stop_after_cancel():
    pending, seen = [], []
    reader = SelectionReader(
        MagicMock(),
        platform="darwin",
        fetch=lambda should_continue, send_copy: seen.append(should_continue()) or "",
        prepare_copy=_no_copy,
        is_trusted=lambda prompt: True,
        start_thread=pending.append,
    )

    reader.request()
    reader.shutdown()
    pending[0]()

    assert seen == [False]


def test_reader_swallows_cancelled_fetch_silently():
    def fetch(should_continue, send_copy):
        raise selection_macos.SelectionCancelled()

    reader, texts, failures = _reader(fetch=fetch)

    reader.request()

    assert texts == failures == []
    assert reader._busy.acquire(blocking=False)


def test_reader_reports_permission_check_errors():
    def broken_check(prompt):
        raise OSError("no AX")

    reader = SelectionReader(MagicMock(), platform="darwin", prepare_copy=_no_copy, is_trusted=broken_check)
    failures = []
    reader.failed.connect(failures.append)

    reader.request()

    assert failures == ["Couldn't read the selected text: no AX"]


def test_reader_reports_thread_start_errors_and_unlocks():
    def no_threads(target):
        raise RuntimeError("can't start thread")

    reader = SelectionReader(
        MagicMock(), platform="darwin", prepare_copy=_no_copy, is_trusted=lambda prompt: True, start_thread=no_threads
    )
    failures = []
    reader.failed.connect(failures.append)

    reader.request()

    assert failures == ["Couldn't read the selected text: can't start thread"]
    assert reader._busy.acquire(blocking=False)


def test_reader_ignores_requests_after_shutdown():
    fetch = MagicMock(return_value="text")
    reader, texts, failures = _reader(fetch=fetch)

    reader.shutdown()
    reader.request()

    fetch.assert_not_called()
    assert texts == failures == []


def test_reader_ignores_request_while_busy():
    pending = []
    reader = SelectionReader(
        MagicMock(),
        platform="darwin",
        fetch=lambda should_continue, send_copy: "text",
        prepare_copy=_no_copy,
        is_trusted=lambda prompt: True,
        start_thread=pending.append,
    )
    texts = []
    reader.textReady.connect(texts.append)

    reader.request()
    reader.request()  # ignored while the first fetch runs, and must not cancel it
    pending[0]()

    assert len(pending) == 1
    assert texts == ["text"]


def test_reader_uses_primary_selection_on_linux():
    clipboard = MagicMock()
    clipboard.supportsSelection.return_value = True
    clipboard.text.return_value = "primary"
    reader, texts, failures = _reader(platform="linux", clipboard=clipboard)

    reader.request()

    clipboard.text.assert_called_once_with(QClipboard.Mode.Selection)
    assert texts == ["primary"]


def test_reader_reports_unsupported_platform():
    clipboard = MagicMock()
    clipboard.supportsSelection.return_value = False
    reader, texts, failures = _reader(platform="win32", clipboard=clipboard)

    reader.request()

    assert texts == []
    assert len(failures) == 1


@pytest.mark.parametrize("names", [[], "f6", ["f6", "nope"], 5, [5], None, ["media_volume_up"]])
def test_parse_hotkey_rejects_bad_names(names):
    from cracker.keylogger import parse_hotkey

    with pytest.raises(ValueError):
        parse_hotkey(names)


def test_when_idle_runs_now_without_a_fetch():
    reader, _, _ = _reader()
    calls = []

    reader.when_idle(lambda: calls.append("read"))

    assert calls == ["read"]


def test_when_idle_waits_for_a_running_fetch_to_finish():
    pending, calls = [], []
    reader = SelectionReader(
        MagicMock(),
        platform="darwin",
        fetch=lambda should_continue, send_copy: calls.append("fetch") or "selected",
        prepare_copy=_no_copy,
        is_trusted=lambda prompt: True,
        start_thread=pending.append,
    )

    reader.request()
    reader.cancel()  # a clipboard read stops the selection read first
    reader.when_idle(lambda: calls.append("read clipboard"))
    assert calls == []
    pending[0]()

    assert calls == ["fetch", "read clipboard"]


def test_when_idle_runs_after_a_cancelled_fetch():
    pending, calls = [], []

    def fetch(should_continue, send_copy):
        raise selection_macos.SelectionCancelled()

    reader = SelectionReader(
        MagicMock(),
        platform="darwin",
        fetch=fetch,
        prepare_copy=_no_copy,
        is_trusted=lambda prompt: True,
        start_thread=pending.append,
    )

    reader.request()
    reader.when_idle(lambda: calls.append("read clipboard"))
    pending[0]()

    assert calls == ["read clipboard"]


def test_when_idle_is_dropped_by_a_later_stop():
    pending, calls = [], []
    reader = SelectionReader(
        MagicMock(),
        platform="darwin",
        fetch=lambda should_continue, send_copy: "selected",
        prepare_copy=_no_copy,
        is_trusted=lambda prompt: True,
        start_thread=pending.append,
    )

    reader.request()
    reader.cancel()
    reader.when_idle(lambda: calls.append("read clipboard"))
    reader.cancel()  # Stop, or a newer read, after the clipboard read was queued
    pending[0]()

    assert calls == []


def test_reader_prepares_the_copy_key_on_the_calling_thread():
    calls = []
    sender = MagicMock()
    pending = []

    def prepare():
        calls.append(("prepare", threading.get_ident()))
        return sender

    def fetch(should_continue, send_copy):
        calls.append(("fetch", send_copy))
        return "text"

    reader = SelectionReader(
        MagicMock(),
        platform="darwin",
        fetch=fetch,
        prepare_copy=prepare,
        is_trusted=lambda prompt: True,
        start_thread=pending.append,
    )
    reader.request()
    assert calls == [("prepare", threading.get_ident())]  # before the worker starts

    worker = threading.Thread(target=pending.pop())
    worker.start()
    worker.join()
    assert calls[1] == ("fetch", sender)


def test_reader_reports_copy_preparation_errors_and_unlocks():
    def broken_prepare():
        raise RuntimeError("no keyboard")

    reader = SelectionReader(
        MagicMock(),
        platform="darwin",
        fetch=MagicMock(),
        prepare_copy=broken_prepare,
        is_trusted=lambda prompt: True,
        start_thread=lambda target: target(),
    )
    failures = []
    reader.failed.connect(failures.append)
    reader.request()

    assert failures and "no keyboard" in failures[0]
    assert not reader._busy.locked()
