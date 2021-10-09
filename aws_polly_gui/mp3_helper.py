import os
from typing import Optional

CACHE_PATH = os.path.expanduser(r"~/.cache/cracker")
try:
    os.makedirs(CACHE_PATH)
except:
    pass


def create_filename(base_filename: str, idx: Optional[int]=None) -> str:
    "Helper function to index file without losing extension"
    if idx is not None:
        filename = '-{}.'.format(idx).join(base_filename.rsplit('.', 1))
        return filename
    else:
        return base_filename


def save_mp3(mp3_stream, base_filename: str) -> str:
    """Stores downloaded response as an mp3.
    
    Returns path to location where the mp3 is stored.
    The path should be absolute path, i.e. `~/.cache` -> `/home/user/.cache`.
    """
    filepath = os.path.join(CACHE_PATH, base_filename)
    with open(filepath, 'wb') as tmp_file:
        tmp_file.write(mp3_stream)
    return filepath
