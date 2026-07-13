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


def test_polly_read_text_cleans_partial_files_on_failure(tmp_path, monkeypatch):
    from cracker.ssml import SSML

    polly = object.__new__(Polly)
    polly.player = MagicMock()
    polly._cached_ssml = SSML()
    polly._cached_segments = []
    polly._cached_voice = ""

    # Force two chunks so the first is written before the second fails.
    monkeypatch.setattr(
        "cracker.speaker.polly.TextParser.split_text",
        staticmethod(lambda text, max_char=3000: iter(["one", "two"])),
    )
    written = []

    def fake_save(stream, base_filename):
        path = tmp_path / base_filename
        path.write_bytes(b"audio")
        written.append(path)
        return str(path)

    monkeypatch.setattr("cracker.speaker.polly.save_mp3", fake_save)

    calls = {"n": 0}

    def fake_ask(ssml_text, voice):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise RuntimeError("boom on the second chunk")
        return {"AudioStream": MagicMock(read=lambda: b"audio")}

    polly.ask_polly = fake_ask
    polly._fetch_marks = MagicMock(return_value=[])

    polly.read_text("one two", rate="medium", volume="medium", voice="Joanna")

    assert written and not any(path.exists() for path in written)  # partial file removed
    assert polly._cached_segments == []
    polly.player.play_segments.assert_not_called()


def test_polly_read_text_invalidates_cache_on_synthesis_failure():
    from cracker.read_along import AudioSegment
    from cracker.ssml import SSML

    polly = object.__new__(Polly)
    polly.player = MagicMock()
    # A prior successful read left a cache pointing at deterministic temp files.
    polly._cached_ssml = SSML("previous text")
    polly._cached_segments = [AudioSegment(path="tmp-0.mp3")]
    polly._cached_voice = "Joanna"
    polly.ask_polly = MagicMock(side_effect=RuntimeError("boom"))

    polly.read_text("brand new text", rate="medium", volume="medium", voice="Joanna")

    # Cache invalidated so a later read can't replay possibly-overwritten files.
    assert polly._cached_segments == []
    assert polly._cached_voice == ""
    assert polly._cached_ssml == SSML()
    polly.player.play_segments.assert_not_called()


def test_google_uses_explicit_service_account_file():
    player = MagicMock()
    client = MagicMock()

    with patch(
        "cracker.speaker.google.texttospeech.TextToSpeechClient.from_service_account_json",
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
