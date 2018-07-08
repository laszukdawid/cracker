import os


def save_mp3(mp3_stream, base_filename, idx=None):
    """Stores downloaded response as an mp3."""
    filename = os.path.abspath(base_filename)
    if idx is not None:
        filename = '-{}.'.format(idx).join(filename.split('.'))
    with open(filename, 'wb') as tmp_file:
        tmp_file.write(mp3_stream)
    return filename
