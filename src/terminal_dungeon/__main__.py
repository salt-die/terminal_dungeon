"""Run the included caster example.

Controls
--------
- `wasdqe` or arrow-keys to move
- `t` to toggle textures
- `esc` to exit
"""

from pathlib import Path

from .camera import Camera
from .engine import Engine
from .read_assets import (
    read_map,
    read_sprite_textures,
    read_wall_textures,
    iter_from_json
)

ASSETS = Path(__file__).parent / "assets"
ASSETS = ASSETS.absolute()

camera = Camera(pos=(5, 5))
game_map = read_map(ASSETS / "dungeon.txt")
sprites = [*iter_from_json(ASSETS / "sprites.json")]
wall_textures = read_wall_textures(ASSETS / "wall_1.txt", ASSETS / "wall_2.txt")
sprite_textures = read_sprite_textures(ASSETS / "dragon.txt", ASSETS / "tree.txt")

engine = Engine(
    camera=camera,
    game_map=game_map,
    sprites=sprites,
    wall_textures=wall_textures,
    sprite_textures=sprite_textures,
)

engine.run()