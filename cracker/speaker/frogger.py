import asyncio
from typing import List

import httpx

from cracker.speaker import FROGGER_LANGUAGES
from cracker.text_parser import TextParser
from cracker.utils import get_logger

from .abstract_speaker import AbstractSpeaker


class FroggerError(RuntimeError):
    """Raised when the Frogger service cannot produce an audio file."""


class Frogger(AbstractSpeaker):
    """
    Uses Unix `espeak` command line interfrace.
    """

    _logger = get_logger(__name__)

    MIN_VOLUME, MAX_VOLUME = 0, 200
    RATES = [80, 120, 160, 200, 240]
    VOLUMES = range(100)

    LANGUAGES = FROGGER_LANGUAGES
    URL = "http://localhost:8000/tts"
    TIMEOUT_SECONDS = 30.0

    def __init__(self, player):
        self.player = player

    def __del__(self):
        player = getattr(self, "player", None)
        if player is not None:
            player.stop()

    def read_text(self, text: str, **config) -> None:
        self._logger.debug("Reading text: %s", text)
        text = self.clean_text(text)
        text = TextParser.escape_tags(text)
        split_text = TextParser.split_text_per_sentence(text)

        self._logger.debug("Requesting from local server")
        try:
            asyncio.run(self._read_text(split_text, **config))
        except Exception:
            self._logger.exception("Failed to read text with Frogger")
        return

    async def _fetch_part(self, client: httpx.AsyncClient, index: int, text: str, voice: str) -> str:
        self._logger.debug("Requesting Frogger part %d: %s", index, text)
        try:
            response = await client.get(self.URL, params={"text": text, "voice": voice})
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise FroggerError(f"Frogger request for part {index} failed: {error}") from error

        try:
            filename = response.json()["filename"]
        except (KeyError, TypeError, ValueError) as error:
            raise FroggerError(f"Frogger returned an invalid response for part {index}") from error
        if not isinstance(filename, str) or not filename:
            raise FroggerError(f"Frogger returned an invalid filename for part {index}")
        return filename

    async def _read_text(
        self,
        parted_text: List[str],
        *,
        voice: str,
        client: httpx.AsyncClient | None = None,
        **config,
    ) -> None:
        async def fetch_all(active_client: httpx.AsyncClient) -> list[str]:
            requests_in_order = [
                self._fetch_part(active_client, index, text, voice) for index, text in enumerate(parted_text)
            ]
            return await asyncio.gather(*requests_in_order)

        if client is None:
            async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as active_client:
                filepaths = await fetch_all(active_client)
        else:
            filepaths = await fetch_all(client)
        self.play_files(filepaths)

    def play_files(self, filepaths):
        self.player.play_files(filepaths)

    def stop_text(self):
        self.player.stop()

    def pause_text(self):
        if self.player.playbackState() == self.player.PlaybackState.PausedState:
            self.player.play()
        else:
            self.player.pause()
