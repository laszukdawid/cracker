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


def test_restore_failure_leaves_clipboard_uncleared():
    class BrokenItem(FakeItem):
        def setData_forType_(self, data, pb_type):
            return False

    pasteboard = FakePasteboard([FakeItem({STRING: "selected"})])
    before = pasteboard.count

    with pytest.raises(selection_macos.SelectionError):
        selection_macos.restore_pasteboard(pasteboard, [{STRING: "previous"}], make_item=BrokenItem)

    assert pasteboard.count == before
    assert pasteboard.items[0].data == {STRING: "selected"}


class FakeApp:
    def __init__(self, pid):
        self.pid = pid

    def processIdentifier(self):
        return self.pid


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

    assert selection_macos.get_selected_text() == "from ax 42"
    copy.assert_not_called()


def test_get_selected_text_does_not_copy_after_focus_change(monkeypatch):
    monkeypatch.setattr(selection_macos, "_framework", lambda name: _fake_appkit([42, 7]))
    monkeypatch.setattr(selection_macos, "selected_text_from_accessibility", lambda pid: "")
    copy = MagicMock()
    monkeypatch.setattr(selection_macos, "selected_text_from_copy", copy)

    with pytest.raises(selection_macos.SelectionError):
        selection_macos.get_selected_text()

    copy.assert_not_called()


def _reader(platform="darwin", fetch=lambda: "hello", trusted=True, clipboard=None):
    reader = SelectionReader(
        clipboard or MagicMock(),
        platform=platform,
        fetch=fetch,
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

    def fetch():
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
        fetch=lambda: "late text",
        is_trusted=lambda prompt: True,
        start_thread=pending.append,
    )
    texts = []
    reader.textReady.connect(texts.append)

    reader.request()
    reader.cancel()
    pending[0]()

    assert texts == []


def test_reader_reports_permission_check_errors():
    def broken_check(prompt):
        raise OSError("no AX")

    reader = SelectionReader(MagicMock(), platform="darwin", is_trusted=broken_check)
    failures = []
    reader.failed.connect(failures.append)

    reader.request()

    assert failures == ["Couldn't read the selected text: no AX"]


def test_reader_reports_thread_start_errors_and_unlocks():
    def no_threads(target):
        raise RuntimeError("can't start thread")

    reader = SelectionReader(MagicMock(), platform="darwin", is_trusted=lambda prompt: True, start_thread=no_threads)
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
        fetch=lambda: "text",
        is_trusted=lambda prompt: True,
        start_thread=pending.append,
    )

    reader.request()
    reader.request()

    assert len(pending) == 1


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


@pytest.mark.parametrize("names", [[], "f6", ["f6", "nope"], 5, [5], None])
def test_parse_hotkey_rejects_bad_names(names):
    from cracker.keylogger import parse_hotkey

    with pytest.raises(ValueError):
        parse_hotkey(names)
