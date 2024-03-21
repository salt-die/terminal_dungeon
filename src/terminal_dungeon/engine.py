"""A raycaster game engine."""

import curses
import os
import signal
from collections import defaultdict
from dataclasses import dataclass
from platform import uname
from time import monotonic

import numpy as np
from numpy.typing import NDArray
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from .camera import Camera
from .raycaster import Raycaster
from .read_assets import Sprite

KEY_BINDINGS: dict[str, Key | KeyCode] = {
    "quit": Key.esc,
    "toggle_texture": KeyCode(char="t"),
    "forward_1": Key.up,
    "forward_2": KeyCode(char="w"),
    "backward_1": Key.down,
    "backward_2": KeyCode(char="s"),
    "turn_left_1": Key.left,
    "turn_left_2": KeyCode(char="a"),
    "turn_right_1": Key.right,
    "turn_right_2": KeyCode(char="d"),
    "strafe_left": KeyCode(char="q"),
    "strafe_right": KeyCode(char="e"),
}

_IS_WINDOWS: bool = uname().system == "Windows"


def _move_to(camera: Camera, game_map: NDArray[np.int64], pos: NDArray[np.float32]):
    old_x, old_y = camera.pos
    x, y = pos.tolist()
    if game_map[int(x), int(y)] == 0:
        camera.pos = x, y
    elif game_map[int(x), int(old_y)] == 0:
        camera.pos = x, old_y
    elif game_map[int(old_x), int(y)] == 0:
        camera.pos = old_x, y


@dataclass
class Engine:
    """A raycaster game engine.

    Parameters
    ----------
    camera : Camera
        The camera for the caster.
    game_map : NDArray[np.uint64]
        A 2D integer numpy array with nonzero entries representing walls.
    sprites : list[Sprite]
        A list of sprites.
    wall_textures : list[NDArray[np.uint64]]
        A list of wall textures.
    sprite_textures : list[NDArray[np.str_]]
        A list of sprite textures.
    rotation_speed : float, default: 3.0
        Speed with which the camera rotates.
    translation_speed : float, default: 5.0
        Speed with which the camera translates.
    """

    camera: Camera
    """The camera for the caster."""
    game_map: NDArray[np.uint64]
    """A 2D integer numpy array with nonzero entries representing walls."""
    sprites: list[Sprite]
    """A list of sprites."""
    wall_textures: list[NDArray[np.uint64]]
    """A list of wall textures."""
    sprite_textures: list[NDArray[np.str_]]
    """A list of sprite textures."""
    rotation_speed: float = 3.0
    """Speed with which the camera rotates."""
    translation_speed: float = 5.0
    """Speed with which the camera translates."""

    def run(self) -> None:
        """Run the game engine."""
        curses.wrapper(self._run)

    def _run(self, screen) -> None:
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        screen.attron(curses.color_pair(1))
        screen.nodelay(True)

        camera = self.camera
        strafe_rot = camera.rotation_matrix(3 * np.pi / 2)
        game_map = self.game_map
        caster = Raycaster(self)
        resized: bool = True

        pressed_keys = defaultdict(bool)

        def on_press(key):
            pressed_keys[key] = True

        def on_release(key):
            pressed_keys[key] = False

        def set_resized(*args):
            nonlocal resized
            resized = True

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        if not _IS_WINDOWS:
            signal.signal(signal.SIGWINCH, set_resized)

        try:
            last_time = monotonic()
            while True:
                current_time = monotonic()
                dt = current_time - last_time
                last_time = current_time
                if resized or _IS_WINDOWS and screen.getch() == curses.KEY_RESIZE:
                    if _IS_WINDOWS:
                        height, width = screen.getmaxyx()
                    else:
                        width, height = os.get_terminal_size()
                        curses.resizeterm(height, width)
                    caster.resize(width - 1, height)
                    resized = False

                caster.cast()

                for row_num, row in enumerate(caster.buffer):
                    screen.addstr(row_num, 0, "".join(row))
                    screen.refresh()

                if pressed_keys[KEY_BINDINGS["quit"]]:
                    break
                if pressed_keys[KEY_BINDINGS["toggle_texture"]]:
                    pressed_keys[KEY_BINDINGS["toggle_texture"]] = False
                    caster.toggle_textures()

                left = (
                    pressed_keys[KEY_BINDINGS["turn_left_1"]]
                    or pressed_keys[KEY_BINDINGS["turn_left_2"]]
                )
                right = (
                    pressed_keys[KEY_BINDINGS["turn_right_1"]]
                    or pressed_keys[KEY_BINDINGS["turn_right_2"]]
                )
                forward = (
                    pressed_keys[KEY_BINDINGS["forward_1"]]
                    or pressed_keys[KEY_BINDINGS["forward_2"]]
                )
                backward = (
                    pressed_keys[KEY_BINDINGS["backward_1"]]
                    or pressed_keys[KEY_BINDINGS["backward_2"]]
                )
                strafe_left = pressed_keys[KEY_BINDINGS["strafe_left"]]
                strafe_right = pressed_keys[KEY_BINDINGS["strafe_right"]]

                if left and not right:
                    camera.rotate(-self.rotation_speed * dt)
                elif right and not left:
                    camera.rotate(self.rotation_speed * dt)

                if forward and not backward:
                    next_pos = (
                        self.translation_speed * dt * camera._plane[0] + camera.pos
                    )
                    _move_to(camera, game_map, next_pos)
                elif backward and not forward:
                    next_pos = (
                        -self.translation_speed * dt * camera._plane[0] + camera.pos
                    )
                    _move_to(camera, game_map, next_pos)

                if strafe_left and not strafe_right:
                    next_pos = (
                        self.translation_speed * dt * camera._plane[0] @ strafe_rot
                        + camera.pos
                    )
                    _move_to(camera, game_map, next_pos)
                elif strafe_right and not strafe_left:
                    next_pos = (
                        self.translation_speed * dt * camera._plane[0] @ -strafe_rot
                        + camera.pos
                    )
                    _move_to(camera, game_map, next_pos)

        finally:
            listener.stop()
            if not _IS_WINDOWS:
                signal.signal(signal.SIGWINCH, signal.SIG_DFL)

            curses.flushinp()
            curses.endwin()
