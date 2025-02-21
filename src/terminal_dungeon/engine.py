"""A raycaster game engine."""

import curses
import os
import sys
import signal
from collections import defaultdict
from dataclasses import dataclass
from time import monotonic

import numpy as np
from numpy.typing import NDArray
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from . import _IS_WINDOWS
from .camera import Camera, rotation_matrix
from .raycaster import Raycaster
from .sprite import Sprite

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

STRAFE_ROT = rotation_matrix(3 * np.pi / 2)


def _move_to(
    camera: Camera, game_map: NDArray[np.uint32], pos: tuple[float, float]
) -> None:
    """Move the camera as close to new position as possible considering walls.

    Parameters
    ----------
    camera : terminal_dungeon.camera.Camera
        The camera to move.
    game_map : NDArray[np.uint32]
        A 2D integer numpy array with nonzero entries representing walls.
    pos : tuple[float, float]
        The new position for the camera.
    """
    old_x, old_y = camera.pos
    x, y = pos

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
    camera : terminal_dungeon.camera.Camera
        The camera for the caster.
    game_map : NDArray[np.uint32]
        A 2D integer numpy array with nonzero entries representing walls.
    sprites : list[terminal_dungeon.raycaster.Sprite]
        A list of sprites.
    wall_textures : list[NDArray[np.uint8]]
        A list of wall textures.
    sprite_textures : list[NDArray[np.str_]]
        A list of sprite textures.
    rotation_speed : float, default: 3.0
        Speed with which the camera rotates.
    translation_speed : float, default: 5.0
        Speed with which the camera translates.

    Attributes
    ----------
    camera : terminal_dungeon.camera.Camera
        The camera for the caster.
    game_map : NDArray[np.uint32]
        A 2D integer numpy array with nonzero entries representing walls.
    sprites : list[terminal_dungeon.raycaster.Sprite]
        A list of sprites.
    wall_textures : list[NDArray[np.uint8]]
        A list of wall textures.

    Methods
    -------
    run()
        Run the game engine.
    """

    camera: Camera
    """The camera for the caster."""
    game_map: NDArray[np.uint32]
    """A 2D integer numpy array with nonzero entries representing walls."""
    sprites: list[Sprite]
    """A list of sprites."""
    wall_textures: list[NDArray[np.uint8]]
    """A list of wall textures."""
    sprite_textures: list[NDArray[np.str_]]
    """A list of sprite textures."""
    rotation_speed: float = 3.0
    """Speed with which the camera rotates."""
    translation_speed: float = 5.0
    """Speed with which the camera translates."""

    def __post_init__(self) -> None:
        self.caster = Raycaster(self)
        """The raycaster for the engine."""

    def run(self) -> None:
        """Run the game engine."""
        curses.wrapper(self._run)

    def _run(self, screen: curses.window) -> None:
        """Run the game engine.

        Parameters
        ----------
        screen : curses.window
            The curses window to draw the game on.
        """
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        screen.attron(curses.color_pair(1))
        screen.nodelay(True)

        caster = self.caster
        resized: bool = True

        pressed_keys = defaultdict(bool)

        def on_press(key: Key | KeyCode | None):
            pressed_keys[key] = True
            print(key, file=sys.stderr)

        def on_release(key: Key | KeyCode | None):
            pressed_keys[key] = False

        def set_resized(*_):
            nonlocal resized
            resized = True

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()

        if not _IS_WINDOWS:
            signal.signal(signal.SIGWINCH, set_resized)

        try:
            last_time = monotonic()

            while not pressed_keys[KEY_BINDINGS["quit"]]:
                current_time = monotonic()
                dt = current_time - last_time
                last_time = current_time

                if resized or _IS_WINDOWS and screen.getch() == curses.KEY_RESIZE:
                    self._handle_resize(screen)
                    resized = False

                caster.cast()

                for row_num, row in enumerate(caster.buffer):
                    screen.addstr(row_num, 0, "".join(row))
                    screen.refresh()

                self._handle_keys(pressed_keys, dt)

        finally:
            listener.stop()

            if not _IS_WINDOWS:
                signal.signal(signal.SIGWINCH, signal.SIG_DFL)

            curses.flushinp()
            curses.endwin()

    def _handle_resize(self, screen: curses.window) -> None:
        """Handle a terminal resize.

        Parameters
        ----------
        resized : bool
            Whether the terminal has been resized.
        screen : curses.window
            The curses window to draw the game on.
        """
        if _IS_WINDOWS:
            height, width = screen.getmaxyx()
        else:
            width, height = os.get_terminal_size()
            curses.resizeterm(height, width)
        self.caster.resize(width - 1, height)

    def _handle_keys(self, pressed_keys: defaultdict, dt: float) -> None:
        """Handle key presses.

        Parameters
        ----------
        pressed_keys : defaultdict
            A dictionary of pressed keys.
        dt : float
            Time since last frame in.
        """
        camera = self.camera
        caster = self.caster
        game_map = self.game_map

        if pressed_keys[KEY_BINDINGS["toggle_texture"]]:
            pressed_keys[KEY_BINDINGS["toggle_texture"]] = False
            caster.toggle_textures()

        def _is_pressed(*args):
            """Check if any of the keys are pressed.

            Parameters
            ----------
            *args : str
                The keys to check.
            """
            return any(pressed_keys[KEY_BINDINGS[arg]] for arg in args)

        left = _is_pressed("turn_left_1", "turn_left_2")
        right = _is_pressed("turn_right_1", "turn_right_2")
        forward = _is_pressed("forward_1", "forward_2")
        backward = _is_pressed("backward_1", "backward_2")
        strafe_left = _is_pressed("strafe_left")
        strafe_right = _is_pressed("strafe_right")

        if left and not right:
            camera.rotate(-self.rotation_speed * dt)
        elif right and not left:
            camera.rotate(self.rotation_speed * dt)

        if forward and not backward:
            next_pos = self.translation_speed * dt * camera._plane[0] + camera.pos
            _move_to(camera, game_map, next_pos)
        elif backward and not forward:
            next_pos = -self.translation_speed * dt * camera._plane[0] + camera.pos
            _move_to(camera, game_map, next_pos)

        if strafe_left and not strafe_right:
            next_pos = (
                self.translation_speed * dt * camera._plane[0] @ STRAFE_ROT + camera.pos
            )
            _move_to(camera, game_map, next_pos)
        elif strafe_right and not strafe_left:
            next_pos = (
                self.translation_speed * dt * camera._plane[0] @ -STRAFE_ROT
                + camera.pos
            )
            _move_to(camera, game_map, next_pos)
