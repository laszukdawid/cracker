import asyncio
from unittest.mock import MagicMock

import httpx
import pytest

from cracker.speaker.frogger import Frogger, FroggerError


def test_read_text_downloads_parts_and_plays_them_in_order():
    frogger = object.__new__(Frogger)
    frogger.player = MagicMock()
    frogger.play_files = MagicMock()

    filenames = {"First.": "first.wav", "Second.": "second.wav"}

    def respond(request: httpx.Request) -> httpx.Response:
        text = request.url.params["text"]
        return httpx.Response(200, json={"filename": filenames[text]})

    async def run_test():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            await frogger._read_text(["First.", "Second."], voice="English", client=client)

    asyncio.run(run_test())

    frogger.play_files.assert_called_once_with(["first.wav", "second.wav"])


def test_frogger_reports_http_failures():
    frogger = object.__new__(Frogger)

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    async def run_test():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            await frogger._fetch_part(client, 0, "Hello", "English")

    with pytest.raises(FroggerError, match="part 0 failed"):
        asyncio.run(run_test())


def test_frogger_rejects_invalid_responses():
    frogger = object.__new__(Frogger)

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True}, request=request)

    async def run_test():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            await frogger._fetch_part(client, 0, "Hello", "English")

    with pytest.raises(FroggerError, match="invalid response"):
        asyncio.run(run_test())
