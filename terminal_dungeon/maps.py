import json
from pathlib import Path
import numpy as np

MAP_DIR = Path("terminal_dungeon") / "maps"

class Map:
    """
    A helper class for easy loading of maps.

    Maps with sprites should have corresponding json file with same name as the map and extension `.sprites`.
    Each sprite in the file is a dict with keys "pos", "tex", for position and name of the texture the sprite uses.
    """
    def __init__(self, map_name):
        # Load map
        with open(MAP_DIR / (map_name + ".txt")) as file:
            tmp = file.read()
        self._map = np.array([list(map(int, line)) for line in tmp.splitlines()]).T

        # Load sprites for map
        if (sprites_path := (MAP_DIR / (map_name + ".sprites"))).is_file():
            with open(sprites_path) as file:
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
