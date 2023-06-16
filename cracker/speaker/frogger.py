import asyncio
from typing import List, Dict, Optional

import copy
import requests
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlaylist
from PyQt5.QtMultimedia import QMediaPlayer

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
        text = "One. Two. Three. Four."
        text = self.clean_text(text)
        text = TextParser.escape_tags(text)
        split_text = TextParser.split_text_per_sentence(text)

        self._logger.debug("Requesting from local server")
        # filepaths = []
        # TODO: This should obviously be asynchronous!
        asyncio.run(self._read_text(split_text, **config))
        return

    async def _read_text(self, parted_text: List[str], **config) -> None:
        filenames: Dict[int, Optional[str]] = {i: None for i in range(len(parted_text))}
        condition = asyncio.Condition()
        cors = []

        async def ask(i, text, voice, condition, fnames: Dict[int, Optional[str]]):
            print(f"asking [{i}]: {text}")
            await asyncio.sleep(0.1 * i)
            response = requests.get(self.URL, params={"text": text, "voice": voice})

            if response.status_code != 200:
                raise Exception(f"Error: Unexpected response {response}")
            filename = response.json()["filename"]

            async with condition:
                fnames[i] = filename
                condition.notify_all()

        async def monitor(_fnames: Dict[int, Optional[str]], condition, player: QMediaPlayer):
            current_media = 0
            
            def mediaChangeHook(status: int, playlist: QMediaPlaylist, player: QMediaPlayer):
                if status == QMediaPlayer.EndOfMedia:
                    if player.playlist() is None:
                        print("Setting playlist")
                        playlist.setCurrentIndex(0)
                        player.setPlaylist(playlist)
                        player.play()
                    
                    elif player.playlist().currentIndex() < player.playlist().mediaCount() - 1:
                        print(f"Current index {player.playlist().currentIndex()} < {player.playlist().mediaCount() - 1}")
                        player.playlist().next()
                    else:
                        print("Reseting")
                        playlist.clear()
                        player.mediaStatusChanged.disconnect()
                    # player.mediaStatusChanged.connect(lambda status: None)
                    # player.setPlaylist(playlist)
                    # player.play()
                    

            while True:
                # Break whole loop if all workers have finished
                if all([f is not None for f in _fnames.values()]):
                    print("All workers have finished")
                    break

                async with condition:
                    await condition.wait()
                    print(f"Updated fnames: {_fnames}")
                    if player.state() == player.StoppedState:
                        print(f"Playing {current_media}")
                        media = QMediaContent(QUrl.fromLocalFile(_fnames[current_media]))
                        player.setMedia(media)
                        player.play()
                        current_media += 1

            print("current_media: ", current_media)
            print("_fnames: ", _fnames)
            playlist = QMediaPlaylist()
            for idx in range(current_media, len(_fnames)):
                filename = _fnames.get(idx)
                if filename is None:
                    break
                playlist.addMedia(QMediaContent(QUrl.fromLocalFile(filename)))
            # all_content = [QMediaContent(QUrl.fromLocalFile(f)) for f in _fnames[current_media:] if f is not None]
            # print(f"all_content (len={len(all_content)}): {all_content}")
            # for media in all_content:
            #     playlist.addMedia(media)
            player.mediaStatusChanged.connect(lambda status: mediaChangeHook(status, playlist, player))
            current_media = 0


        for i, text in enumerate(parted_text):
            task = ask(i, text, voice=config["voice"], condition=condition, fnames=filenames)
            cors.append(task)

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
