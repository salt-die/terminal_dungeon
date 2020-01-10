import json
import numpy as np

class Map:
    """
    A helper class for easy loading of maps.

    Each sprite is a dict with keys "pos","image","relative" for position,
    sprite image number, and relative position to player (which will be set
    after first call to cast_sprites in the renderer).
    """
    def __init__(self, file_name):
        self._load(file_name)

    def _load(self, file_name):
        with open(file_name + ".json", 'r') as file:
            map_dict = json.load(file)
            self._map = np.array(map_dict["map"]).T
            self.sprites = map_dict["sprites"]
        for sprite in self.sprites: #lists --> numpy arrays
            sprite["pos"] = np.array(sprite["pos"])

    def __getitem__(self, key):
        return self._map[key]
