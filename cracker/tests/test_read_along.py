from cracker.read_along import (
    EstimateProgressSource,
    MarksProgressSource,
    WordMark,
    align_spoken_to_editor,
    build_session,
    normalize_word,
    parse_speech_marks,
)


def test_normalize_word_strips_edge_punctuation_and_lowercases():
    assert normalize_word("Hello,") == "hello"
    assert normalize_word("(world)") == "world"
    assert normalize_word("it's") == "it's"
    # All-punctuation tokens fall back to the lowercased original.
    assert normalize_word("&") == "&"


def test_parse_speech_marks_keeps_word_marks_in_order():
    data = (
        b'{"time":0,"type":"sentence","value":"Hello world"}\n'
        b'{"time":0,"type":"word","start":0,"end":5,"value":"Hello"}\n'
        b'{"time":312,"type":"word","start":6,"end":11,"value":"world"}\n'
    )
    marks = parse_speech_marks(data)
    assert [(mark.time_ms, mark.value) for mark in marks] == [(0, "Hello"), (312, "world")]


def test_parse_speech_marks_skips_malformed_lines():
    data = b'not json\n\n{"time":10,"type":"word","value":"Hi"}\n{"type":"word"}\n'
    marks = parse_speech_marks(data)
    assert [(mark.time_ms, mark.value) for mark in marks] == [(10, "Hi")]


def test_parse_speech_marks_handles_empty():
    assert parse_speech_marks(b"") == []
    assert parse_speech_marks(None) == []


def test_align_maps_each_spoken_word_to_its_editor_span():
    text = "Hello world again"
    mapping = align_spoken_to_editor(["Hello", "world", "again"], text)
    assert mapping == {0: (0, 5), 1: (6, 5), 2: (12, 5)}


def test_align_skips_editor_words_absent_from_speech():
    # A parser rule removed "bar" before synthesis, so it is spoken as foo/baz.
    text = "foo bar baz"
    mapping = align_spoken_to_editor(["foo", "baz"], text)
    # "baz" must map to the real "baz" span (offset 8), not to "bar".
    assert mapping == {0: (0, 3), 1: (8, 3)}


def test_align_handles_substitution_like_ampersand():
    text = "a & b"
    mapping = align_spoken_to_editor(["a", "and", "b"], text)
    # spoken "and" pairs positionally with the editor "&".
    assert mapping[1] == (2, 1)


def test_align_handles_repeated_words_positionally():
    text = "the cat the dog"
    mapping = align_spoken_to_editor(["the", "cat", "the", "dog"], text)
    assert mapping == {0: (0, 3), 1: (4, 3), 2: (8, 3), 3: (12, 3)}


def test_align_skips_ambiguous_multiword_replacements():
    # A multi-word divergent block is ambiguous; nothing there should map,
    # so an unrelated spoken run never highlights arbitrary editor words.
    mapping = align_spoken_to_editor(["xxx", "yyy", "zzz"], "alpha beta")
    assert mapping == {}


def test_align_still_maps_surrounding_equal_words_when_middle_diverges():
    # "the ... dog" stays anchored; the divergent middle is left unmapped.
    mapping = align_spoken_to_editor(["the", "aaa", "bbb", "dog"], "the ccc ddd dog")
    assert mapping[0] == (0, 3)  # "the"
    assert mapping[3] == (12, 3)  # "dog"
    assert 1 not in mapping and 2 not in mapping


def test_align_handles_empty_inputs():
    assert align_spoken_to_editor([], "some text") == {}
    assert align_spoken_to_editor(["hello"], "") == {}


def test_marks_progress_source_maps_position_to_global_index():
    segments = [[WordMark(0, "a"), WordMark(400, "b")], [WordMark(0, "c")]]
    source = MarksProgressSource(segments)
    assert source.total == 3

    progress = source.progress(segment_index=0, position_ms=450)
    assert progress is not None and progress.word_index == 1 and progress.words_done == 2

    later = source.progress(segment_index=1, position_ms=0)
    assert later is not None and later.word_index == 2

    assert source.progress(segment_index=0, position_ms=-1) is None  # before first mark
    assert source.progress(segment_index=9, position_ms=0) is None  # out of range


def test_estimate_progress_source_advances_with_elapsed():
    source = EstimateProgressSource(total=10, wpm=200)  # total_sec = 3.0
    assert source.progress(elapsed_sec=0.0).words_done == 0
    assert source.progress(elapsed_sec=source.total_sec / 2).words_done == 5
    done = source.progress(elapsed_sec=source.total_sec * 2)
    assert done.fraction == 1.0 and done.word_index == 9 and done.words_done == 10


def test_estimate_progress_source_handles_zero_words():
    source = EstimateProgressSource(total=0, wpm=200)
    progress = source.progress(elapsed_sec=1.0)
    assert progress.word_index is None and progress.words_done == 0


def test_build_session_marks_textarea_maps_editor_spans():
    segments = [[WordMark(0, "Hello"), WordMark(300, "world")]]
    session = build_session(source="textarea", editor_text="Hello world", read_text="", segment_marks=segments, wpm=200)
    assert isinstance(session.progress_source, MarksProgressSource)
    assert session.total == 2
    assert session.word_spans == {0: (0, 5), 1: (6, 5)}


def test_build_session_marks_clipboard_has_no_spans():
    segments = [[WordMark(0, "Hello")]]
    session = build_session(
        source="clipboard", editor_text="ignored", read_text="Hello", segment_marks=segments, wpm=200
    )
    assert session.total == 1 and session.word_spans == {}


def test_build_session_estimate_textarea_uses_editor_tokens():
    session = build_session(source="textarea", editor_text="one two three", read_text="", segment_marks=[], wpm=200)
    assert isinstance(session.progress_source, EstimateProgressSource)
    assert session.total == 3
    assert session.word_spans == {0: (0, 3), 1: (4, 3), 2: (8, 5)}


def test_build_session_estimate_clipboard_counts_read_text():
    session = build_session(
        source="clipboard", editor_text="a b c d e", read_text="alpha beta gamma", segment_marks=[], wpm=200
    )
    assert session.total == 3 and session.word_spans == {}
