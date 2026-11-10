from unittest.mock import MagicMock, patch

from cracker.speaker.google import Google
from cracker.speaker.polly import Polly


def test_polly_connects_with_configured_profile_and_region():
    client = MagicMock()

    with patch("cracker.speaker.polly.boto3.Session") as session:
        session.return_value.client.return_value = client
        result = Polly._connect_aws("work", "us-west-2")

    session.assert_called_once_with(profile_name="work", region_name="us-west-2")
    session.return_value.client.assert_called_once_with("polly")
    assert result is client


def test_polly_builds_expected_synthesis_request():
    request = Polly.create_speech("<speak>Hello</speak>", "Joanna")

    assert request == {
        "OutputFormat": "mp3",
        "TextType": "ssml",
        "Text": "<speak>Hello</speak>",
        "VoiceId": "Joanna",
    }


def test_polly_fetch_marks_requests_word_marks_and_parses_them():
    polly = object.__new__(Polly)
    client = MagicMock()
    stream = MagicMock()
    stream.read.return_value = (
        b'{"time":0,"type":"word","start":0,"end":5,"value":"Hello"}\n'
        b'{"time":300,"type":"word","start":6,"end":11,"value":"world"}\n'
    )
    client.synthesize_speech.return_value = {"AudioStream": stream}
    polly.client = client

    marks = polly._fetch_marks("<speak>Hello world</speak>", "Joanna")

    assert [(mark.time_ms, mark.value) for mark in marks] == [(0, "Hello"), (300, "world")]
    kwargs = client.synthesize_speech.call_args.kwargs
    assert kwargs["OutputFormat"] == "json"
    assert kwargs["SpeechMarkTypes"] == ["word"]
    assert kwargs["Text"] == "<speak>Hello world</speak>"


def test_polly_fetch_marks_returns_empty_on_error():
    polly = object.__new__(Polly)
    client = MagicMock()
    client.synthesize_speech.side_effect = RuntimeError("boom")
    polly.client = client

    assert polly._fetch_marks("<speak>hi</speak>", "Joanna") == []


def _polly(tmp_path, monkeypatch):
    from cracker.ssml import SSML

    polly = object.__new__(Polly)
    polly.player = MagicMock()
    polly.client = MagicMock()
    polly._connection_error = None
    polly._cached_ssml = SSML()
    polly._cached_segments = []
    polly._cached_voice = ""
    polly._marks_executor = None
    polly._queue = MagicMock()
    polly._show_error_dialog = MagicMock()

    def fake_save(stream, base_filename):
        path = tmp_path / base_filename
        path.write_bytes(stream)
        return str(path)

    monkeypatch.setattr("cracker.speaker.polly.save_mp3", fake_save)
    return polly


def test_polly_read_text_synthesises_in_the_background_with_a_short_first_chunk(tmp_path, monkeypatch):
    polly = _polly(tmp_path, monkeypatch)
    text = "First sentence here. " * 40

    polly.read_text(text, rate="medium", volume="medium", voice="Joanna")

    chunks = polly._queue.start.call_args.args[0]
    assert len(chunks[0]) <= 300 and "".join(chunks) == text
    polly.player.play_segments.assert_not_called()  # the queue starts playback once audio exists


def test_polly_chunk_fetches_audio_and_marks_together(tmp_path, monkeypatch):
    import threading

    polly = _polly(tmp_path, monkeypatch)
    both_running = threading.Barrier(2, timeout=2)

    def synthesize_speech(**request):
        both_running.wait()  # deadlocks unless audio and marks are requested at the same time
        body = (
            b'{"time":0,"type":"word","start":0,"end":2,"value":"Hi"}' if request["OutputFormat"] == "json" else b"mp3"
        )
        return {"AudioStream": MagicMock(read=lambda: body)}

    polly.client.synthesize_speech.side_effect = synthesize_speech

    segment = polly._synthesize_chunk("tok", 0, "Hi", "medium", "medium", "Joanna")

    assert open(segment.path, "rb").read() == b"mp3"
    assert [mark.value for mark in segment.marks] == ["Hi"]
    assert "tok" in segment.path


def test_polly_replays_the_cache_without_synthesising(tmp_path, monkeypatch):
    from cracker.read_along import AudioSegment
    from cracker.ssml import SSML

    polly = _polly(tmp_path, monkeypatch)
    polly._cached_ssml = SSML("cached text", rate="medium", volume="medium")
    polly._cached_voice = "Joanna"
    polly._cached_segments = [AudioSegment(path="cached.mp3")]

    polly.read_text("cached text", rate="medium", volume="medium", voice="Joanna")

    polly.player.play_segments.assert_called_once_with(polly._cached_segments)
    polly._queue.start.assert_not_called()


def test_polly_without_a_connection_explains_and_does_not_synthesise(tmp_path, monkeypatch):
    polly = _polly(tmp_path, monkeypatch)
    polly.client = None
    polly._connection_error = "no profile"

    polly.read_text("hello", rate="medium", volume="medium", voice="Joanna")

    polly._show_error_dialog.assert_called_once()
    polly._queue.start.assert_not_called()


def test_google_uses_explicit_service_account_file():
    player = MagicMock()
    client = MagicMock()

    with patch(
        "google.cloud.texttospeech.TextToSpeechClient.from_service_account_json",
        return_value=client,
    ) as connect:
        speaker = Google(player, "~/.config/google/service-account.json")

    connect.assert_called_once()
    assert connect.call_args.args[0].endswith("/.config/google/service-account.json")
    assert speaker.client is client


def test_google_builds_text_synthesis_request():
    speaker = object.__new__(Google)
    speaker.client = MagicMock()
    voice = MagicMock()

    speaker.ask_google("Hello", voice)

    kwargs = speaker.client.synthesize_speech.call_args.kwargs
    assert kwargs["voice"] is voice
    assert kwargs["input"].text == "Hello"
    assert kwargs["audio_config"].audio_encoding.name == "MP3"
