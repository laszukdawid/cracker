import asyncio
from typing import Dict, List, Optional

import requests
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer, QMediaPlaylist

from cracker.speaker import FROGGER_LANGUAGES
from cracker.text_parser import TextParser
from cracker.utils import get_logger

from .abstract_speaker import AbstractSpeaker


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

    def __init__(self, player):
        self.player = player
        self.playlist = QMediaPlaylist(self.player)
        self.playlist.setPlaybackMode(QMediaPlaylist.Sequential)

    def __del__(self):
        self.stop_text()

    def read_text(self, text: str, **config) -> None:
        self._logger.debug("Reading text: %s", text)
        text = self.clean_text(text)
        text = TextParser.escape_tags(text)
        split_text = TextParser.split_text_per_sentence(text)

        self._logger.debug("Requesting from local server")
        asyncio.run(self._read_text(split_text, **config))
        return

    async def _read_text(self, parted_text: List[str], **config) -> None:
        filenames: Dict[int, Optional[str]] = {i: None for i in range(len(parted_text))}
        condition = asyncio.Condition()

        async def ask(i, text, voice, condition, fnames: Dict[int, Optional[str]]):
            self._logger.debug(f"asking [{i}]: {text}")
            await asyncio.sleep(0.1 * i)  # To make sure that it's in order
            response = requests.get(self.URL, params={"text": text, "voice": voice})

            if response.status_code != 200:
                raise Exception(f"Error: Unexpected response {response}")
            filename = response.json()["filename"]

            async with condition:
                fnames[i] = filename
                condition.notify_all()

        def mediaChangeHook(status: int, playlist: QMediaPlaylist, player: QMediaPlayer):
            if status != QMediaPlayer.EndOfMedia:
                return
            # If no playlist set -> set it and play
            if player.playlist() is None:
                self._logger.debug("Setting playlist")
                playlist.setCurrentIndex(0)
                player.setPlaylist(playlist)
                player.play()

            # If already playing playlist -> play next
            elif player.playlist().currentIndex() < player.playlist().mediaCount() - 1:
                player.playlist().next()

            # If finished playing playlist -> reset
            else:
                self._logger.debug("Reseting playlist")
                playlist.clear()
                player.mediaStatusChanged.disconnect()

        async def monitor(d_fnames: Dict[int, Optional[str]], condition, player: QMediaPlayer):
            current_media = 0

            while True:
                # Break whole loop if all workers have finished
                if all([f is not None for f in d_fnames.values()]):
                    self._logger.debug("All files have been downloaded")
                    break

                async with condition:
                    await condition.wait()
                    if player.state() == player.StoppedState:
                        self._logger.debug(f"Currently playing media num {current_media}")
                        media = QMediaContent(QUrl.fromLocalFile(d_fnames[current_media]))
                        player.setMedia(media)
                        player.play()
                        current_media += 1

            # When finished updating filenames, the remaining files are added to the playlist
            playlist = QMediaPlaylist()
            for idx in range(current_media, len(d_fnames)):
                # Add only the files that haven't been listened to yet
                filename = d_fnames.get(idx)
                if filename is None:
                    break
                playlist.addMedia(QMediaContent(QUrl.fromLocalFile(filename)))

            # Update hook to play next file when current one finishes, and reset playlist when finished
            player.mediaStatusChanged.connect(lambda status: mediaChangeHook(status, playlist, player))
            current_media = 0

        cors = []
        for i, text in enumerate(parted_text):
            cors.append(ask(i, text, voice=config["voice"], condition=condition, fnames=filenames))

        cors.append(monitor(filenames, condition, self.player))
        await asyncio.wait(cors)

    def play_file_first(self, filepath):
        self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(filepath)))

        self.player.setPlaylist(self.playlist)

        if self.player.state() != self.player.PlayingState:
            self.player.play()

    def play_file(self, filepath):
        self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(filepath)))

        # self.player.setPlaylist(self.playlist)

        if self.player.state() != self.player.PlayingState:
            self.player.play()

    def play_files(self, filepaths):
        playlist = QMediaPlaylist(self.player)
        for filepath in filepaths:
            url = QUrl.fromLocalFile(filepath)
            playlist.addMedia(QMediaContent(url))
        self.player.setPlaylist(playlist)
        self.player.play()

    def stop_text(self):
        self.player.stop()

    def pause_text(self):
        if self.player.state() == self.player.PausedState:
            self.player.play()
        else:
            self.player.pause()

    def ask(self, text: str, voice: str):
        """Connect to local server on host localhost:5002 and extract wav from stream"""
        response = requests.get(self.URL, params={"text": text, "voice": voice})

        if response.status_code != 200:
            raise Exception(f"Error: Unexpected response {response}")
        return response.json()["filename"]
