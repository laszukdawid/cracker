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
