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

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

__all__ = ["read_map", "read_wall_textures", "read_sprite_textures", "Sprite"]


def read_map(path: Path) -> NDArray[np.uint64]:
    """Read a map from a text file.

    Parameters
    ----------
    path : Path
        Path to text file of map.

    Returns
    -------
    NDArray[np.uint64]
        A 2D integer numpy array with nonzero entries representing walls.
    """
    text = path.read_text()
    return np.array([[int(cell) for cell in line] for line in text.splitlines()]).T


def read_wall_textures(*paths: Path) -> list[NDArray[np.uint64]]:
    r"""Read wall textures.

    Parameters
    ----------
    *paths : Path
        Paths to wall textures.

    Returns
    -------
    list[NDArray[np.str_]]
        A list of wall textures.
    """

    def _read_wall(path):
        text = path.read_text()
        return np.array([[int(cell) for cell in line] for line in text.splitlines()]).T

    return [_read_wall(path) for path in paths]


def read_sprite_textures(*paths: Path) -> list[NDArray[np.str_]]:
    r"""Read sprite textures.

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


@dataclass
class Sprite:
    """A sprite for a raycaster.

    Parameter
    ---------
    pos : NDArray[np.float32]
        Position of sprite on the map.
    texture : int
        Index of sprite texture.
    """

    pos: NDArray[np.float32]
    """Position of sprite on the map."""
    texture_index: int
    """Index of sprite texture."""

    def __post_init__(self) -> None:
        self.pos = np.asarray(self.pos)
        self._relative: NDArray[np.float64] = np.zeros(2)
        """Relative distance from camera."""
        self.distance: np.float64 = 0.0
        """Distance from camera."""

    def __lt__(self, other) -> bool:
        """Sprites are ordered by their distance to camera."""
        return self.distance > other.distance

    @classmethod
    def iter_from_json(cls, path: Path) -> Iterator["Sprite"]:
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
            yield cls(**sprite_data)
