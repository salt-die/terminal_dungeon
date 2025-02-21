"""Sprite model"""

from dataclasses import dataclass


@dataclass
class Sprite:
    """A sprite for a raycaster.

    Parameters
    ----------
    pos : tuple[float, float]
        Position of sprite on the map.
    texture : int
        Index of sprite texture.
    """
    pos: tuple[float, float]
    texture_index: int