"""Word-timing primitives for the read-along highlight.

Pure logic (no Qt/AWS imports) so it can be unit-tested in isolation:

* :class:`WordMark` / :class:`AudioSegment` carry per-word timing alongside each
  synthesized audio file.
* :func:`parse_speech_marks` turns AWS Polly's newline-delimited "word" speech
  marks into ``WordMark``s.
* :func:`align_spoken_to_editor` maps the *spoken* word sequence (from marks)
  back onto character spans in the *original* editor text, so the GUI can
  highlight the user's real text even though the spoken text was cleaned,
  escaped and SSML-wrapped before synthesis.
"""

import difflib
import json
import re
from dataclasses import dataclass, field
from typing import Protocol

_EDGE = re.compile(r"^\W+|\W+$", re.UNICODE)
_WORD = re.compile(r"\S+")


@dataclass
class WordMark:
    """A single spoken word and when it starts, relative to its segment audio."""

    time_ms: int
    value: str


@dataclass
class AudioSegment:
    """One synthesized audio file plus its (possibly empty) word marks."""

    path: str
    marks: list[WordMark] = field(default_factory=list)


def normalize_word(word: str) -> str:
    """Lower-cases and strips leading/trailing punctuation for matching."""
    stripped = _EDGE.sub("", word)
    return (stripped or word).lower()


def parse_speech_marks(data: bytes | str | None) -> list[WordMark]:
    """Parses Polly's newline-delimited JSON "word" speech marks.

    Malformed lines and non-``word`` marks are skipped rather than raising.
    """
    marks: list[WordMark] = []
    if not data:
        return marks
    text = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError, TypeError:
            continue
        if not isinstance(obj, dict) or obj.get("type") != "word":
            continue
        try:
            marks.append(WordMark(time_ms=int(obj["time"]), value=str(obj["value"])))
        except KeyError, TypeError, ValueError:
            continue
    return marks


def align_spoken_to_editor(spoken_words: list[str], editor_text: str) -> dict[int, tuple[int, int]]:
    """Maps spoken-word index -> (char start, length) in ``editor_text``.

    Uses a sequence alignment so removed/added tokens (parser rules stripping
    citations, ``&`` -> "and", etc.) and repeated words line up positionally
    instead of by naive value matching.
    """
    editor_tokens = [(m.start(), len(m.group()), normalize_word(m.group())) for m in _WORD.finditer(editor_text)]
    spoken_norm = [normalize_word(word) for word in spoken_words]
    editor_norm = [token[2] for token in editor_tokens]

    matcher = difflib.SequenceMatcher(a=spoken_norm, b=editor_norm, autojunk=False)
    mapping: dict[int, tuple[int, int]] = {}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                start, length, _ = editor_tokens[j1 + offset]
                mapping[i1 + offset] = (start, length)
        elif tag == "replace" and (i2 - i1) == 1 and (j2 - j1) == 1:
            # Only map clean 1:1 substitutions (e.g. "and" spoken for "&");
            # larger divergent blocks are ambiguous, so leave them unmapped.
            start, length, _ = editor_tokens[j1]
            mapping[i1] = (start, length)
    return mapping


# --- Progress engine -------------------------------------------------------
# The read-along runtime is driven by a ProgressSource that turns playback
# state into "which spoken word is current". Two implementations unify the
# accurate (Polly speech marks) and estimated (WPM) paths behind one contract,
# so the controller/view stay mode-agnostic.


@dataclass
class Progress:
    """A snapshot of read progress: current word, words started, overall fraction."""

    word_index: int | None
    words_done: int
    fraction: float


class ProgressSource(Protocol):
    total: int

    def progress(self, *, segment_index: int, position_ms: int, elapsed_sec: float) -> "Progress | None": ...


class MarksProgressSource:
    """Accurate progress from Polly per-segment word marks (real audio time)."""

    def __init__(self, segment_marks: list[list[WordMark]]):
        self._segments = segment_marks
        self._offsets: list[int] = []
        running = 0
        for segment in segment_marks:
            self._offsets.append(running)
            running += len(segment)
        self.total = running

    def progress(self, *, segment_index: int, position_ms: int, elapsed_sec: float = 0.0) -> Progress | None:
        if segment_index < 0 or segment_index >= len(self._segments):
            return None
        local = -1
        for offset, mark in enumerate(self._segments[segment_index]):
            if mark.time_ms <= position_ms:
                local = offset
            else:
                break
        if local < 0:
            return None
        index = self._offsets[segment_index] + local
        fraction = (index + 1) / self.total if self.total else 1.0
        return Progress(word_index=index, words_done=index + 1, fraction=fraction)


class EstimateProgressSource:
    """Fallback progress paced by a speed-derived words-per-minute estimate."""

    def __init__(self, total: int, wpm: int):
        self.total = total
        self.total_sec = max(0.6, total / (wpm / 60.0)) if total else 0.6

    def progress(self, *, segment_index: int = -1, position_ms: int = 0, elapsed_sec: float = 0.0) -> Progress:
        fraction = min(1.0, elapsed_sec / self.total_sec) if self.total_sec else 1.0
        index = min(self.total - 1, int(fraction * self.total)) if self.total else None
        return Progress(word_index=index, words_done=int(fraction * self.total), fraction=fraction)


@dataclass
class ReadAlongSession:
    """Everything the runtime needs for one read: context, spans, progress source."""

    source: str
    doc_len: int
    total: int
    word_spans: dict[int, tuple[int, int]]
    progress_source: ProgressSource
    index: int = -1

    def highlight_for(self, word_index: int) -> tuple[int, int] | None:
        return self.word_spans.get(word_index)


def build_session(
    *,
    source: str,
    editor_text: str,
    read_text: str,
    segment_marks: list[list[WordMark]],
    wpm: int,
) -> ReadAlongSession:
    """Builds a session, picking marks vs estimate and resolving editor spans.

    ``source`` is "textarea" (highlight the editor) or "clipboard" (no editor
    spans, but still pace/count by ``read_text``).
    """
    if any(segment_marks):
        spoken = [mark.value for segment in segment_marks for mark in segment]
        total = len(spoken)
        word_spans = align_spoken_to_editor(spoken, editor_text) if source == "textarea" else {}
        progress_source: ProgressSource = MarksProgressSource(segment_marks)
    elif source == "textarea":
        tokens = [(match.start(), len(match.group())) for match in _WORD.finditer(editor_text)]
        word_spans = {index: span for index, span in enumerate(tokens)}
        total = len(tokens)
        progress_source = EstimateProgressSource(total, wpm)
    else:
        word_spans = {}
        total = len(_WORD.findall(read_text))
        progress_source = EstimateProgressSource(total, wpm)

    return ReadAlongSession(
        source=source,
        doc_len=len(editor_text),
        total=total,
        word_spans=word_spans,
        progress_source=progress_source,
    )
