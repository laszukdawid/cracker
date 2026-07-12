import asyncio
from unittest.mock import MagicMock, patch

from cracker.speaker.frogger import Frogger


def test_read_text_downloads_parts_and_plays_them_in_order():
    frogger = object.__new__(Frogger)
    frogger.player = MagicMock()
    frogger.play_files = MagicMock()

    responses = {}
    for text, filename in [("First.", "first.wav"), ("Second.", "second.wav")]:
        response = MagicMock(status_code=200)
        response.json.return_value = {"filename": filename}
        responses[text] = response

    def get_response(url, params, timeout):
        return responses[params["text"]]

    with patch("cracker.speaker.frogger.requests.get", side_effect=get_response) as get:
        asyncio.run(frogger._read_text(["First.", "Second."], voice="English"))

    frogger.play_files.assert_called_once_with(["first.wav", "second.wav"])
    assert get.call_count == 2
    get.assert_any_call(
        frogger.URL,
        params={"text": "First.", "voice": "English"},
        timeout=30,
    )
