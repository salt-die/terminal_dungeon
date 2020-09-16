import json
from pathlib import Path
import numpy as np


class Map:
    """
    A helper class for easy loading of maps.

    Maps with sprites should have corresponding json file with same name as the map and extension `.sprite`.
    Each sprite in the file is a dict with keys "pos", "tex", for position and texture number the sprite uses.
    """
    def __init__(self, map_name):
        # Load map
        map_filename = str(Path("terminal_dungeon", "maps", map_name + ".txt"))
        with open(map_filename, "r") as file:
            tmp = file.read()
        self._map = np.array([list(map(int, line)) for line in tmp.splitlines()]).T

        # Load sprites for map
        sprites_path = Path("terminal_dungeon", "maps", map_name + ".sprites")
        if sprites_path.is_file():
            with open(str(sprites_path), "r") as file:
                sprites = json.load(file)
            self.sprites = [Sprite(**sprite) for sprite in sprites]
        else:
            self.sprites = []

    def __getitem__(self, key):
        # We often would convert key to a tuple with ints when indexing the map elsewhere, so we just moved that logic to here:
        return self._map[int(key[0]), int(key[1])]


class Sprite:
    """Helper class to simplify working with sprites."""
    __slots__ = "pos", "tex", "relative"

    def __init__(self, pos, tex):
        self.pos = np.array(pos)
        self.tex = tex
        self.relative = np.array([0.0, 0.0])

    @property
    def distance(self):
        return self.relative @ self.relative

    def __lt__(self, other):
        # Sprites are sorted in reverse from their distance to player in the renderer.
        return self.distance > other.distance
