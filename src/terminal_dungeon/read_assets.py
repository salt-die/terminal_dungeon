"""Functions for reading assets.

Notes
-----
Map textures are arrays of digits from 0-9 with nonzero digits representing wall
textures.

Wall textures are arrays of digits from 0-9 which determine the shading of the wall
(with 0 darker and 9 brighter).

Sprite textures are any plain ascii art with the caveat that the character "0"
represents a transparent character.
"""

from __future__ import annotations

__all__ = ["read_map", "read_wall_textures", "read_sprite_textures", "iter_from_json"]

import json
from collections.abc import Iterator
from pathlib import Path
import numpy as np
from numpy.typing import NDArray

from .sprite import Sprite


def read_map(path: Path) -> NDArray[np.uint32]:
    """Read a map from a text file.

    Parameters
    ----------
    path : Path
        Path to text file of map.

    Returns
    -------
    NDArray[np.uint32]
        A 2D integer numpy array with nonzero entries representing walls.
    """
    text = path.read_text()
    return np.array(
        [[int(cell) for cell in line] for line in text.splitlines()], dtype=np.uint32
    ).T


def read_wall_textures(*paths: Path) -> list[NDArray[np.uint8]]:
    r"""Read wall textures from text files.

    Wall textures are arrays of digits with low digits representing darker
    "pixels" and higher digits brighter.

    Parameters
    ----------
    *paths : Path
        Paths to wall textures.

    Returns
    -------
    list[NDArray[np.uint8]]
        A list of wall textures.
    """

    def _read_wall(path):
        text = path.read_text()
        return np.array([[int(cell) for cell in line] for line in text.splitlines()]).T

    return [_read_wall(path) for path in paths]


def read_sprite_textures(*paths: Path) -> list[NDArray[np.str_]]:
    r"""Read sprite textures from text files.

    Sprite textures can be any text with the caveat that "0" represents a transparent
    character.

    Parameters
    ----------
    *paths : Path
        Paths to sprite textures.

    Returns
    -------
    list[NDArray[np.str_]]
        A list of sprite textures.
    """

    def _read_sprite(path):
        text = path.read_text()
        return np.array([list(line) for line in text.splitlines()]).T

    return [_read_sprite(path) for path in paths]


def iter_from_json(path: Path) -> Iterator[Sprite]:
    """Yield sprites from a json file.

    Parameters
    ----------
    path : Path
        Path to json.

    Yields
    ------
    Sprite
        A sprite for the caster.
    """
    with open(path) as file:
        data = json.load(file)

    for sprite_data in data:
        pos = tuple(sprite_data["pos"])
        yield Sprite(pos=pos, texture_index=sprite_data["texture_index"])
