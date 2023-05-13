import logging
from collections.abc import MutableMapping
from typing import Dict


def get_logger(name: str) -> logging.Logger:
    """Returns a logger with the given name."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def deep_dict_merge(d1: Dict, d2: Dict) -> Dict:
    """
    Update two dicts of dicts recursively,
    if either mapping has leaves that are non-dicts,
    the second's leaf overwrites the first's.

    Source: https://stackoverflow.com/a/24088493/2687601
    """
    for k, v in d1.items():
        if k in d2:
            if all(isinstance(e, MutableMapping) for e in (v, d2[k])):
                d2[k] = deep_dict_merge(v, d2[k])
            # we could further check types and merge as appropriate here.
    d3 = d1.copy()
    d3.update(d2)
    return d3
