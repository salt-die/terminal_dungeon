import json
import numpy as np
from pathlib import Path

class Map:
    """
    A helper class for easy loading of maps.

    Each sprite is a dict with keys "pos","image","relative" for position,
    sprite image number, and relative position to player (which will be set
    after first call to cast_sprites in the renderer).
    """
    def __init__(self, map_name):
        self._load(map_name)

    def _load(self, map_name):
        map_filename = str(Path("terminal_dungeon", "maps", map_name + ".txt"))
        sprites_filename = str(Path("terminal_dungeon", "maps", map_name + ".sprites"))
        
        with open(map_filename, "r") as file:
            tmp = file.read()
        self._map = np.array([[int(c) for c in line] for line in tmp.splitlines()]).T
        
        with open(sprites_filename, "r") as file:
            self.sprites = json.load(file)
        
        for sprite in self.sprites: # lists --> numpy arrays
            sprite["pos"] = np.array(sprite["pos"])

    def __getitem__(self, key):
        return self._map[key]
