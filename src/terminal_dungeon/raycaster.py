"""A raycaster."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from .engine import Engine


def _clamp(min_: float, val: float, max_: float) -> float:
    if val < min_:
        return min_
    if val > max_:
        return max_
    return val


@dataclass
class Raycaster:
    """A raycaster."""

    engine: "Engine"
    """The game engine."""
    max_hops: int = 20
    """Determines how far rays are cast."""
    ascii_map: NDArray[np.str_] = field(
        default_factory=lambda: np.array(list(" .,:;<+*LtCa4U80dQM@"))
    )
    minimap_width: float = 0.2
    """Width of minimap as a proportion of the screen's width."""
    minimap_height: float = 0.3
    """Height of minimap as a proportion of the screen's height."""
    minimap_pos: tuple[int, int] = (5, 5)
    """Offset of minimap's lower right corner from screen's lower right corner."""

    def __post_init__(self) -> None:
        self._shades = len(self.ascii_map) - 1
        self._shade_values = np.linspace(-12, 12, self._shades, dtype=int)
        self._side_shade = 2
        self._shade_dif = self._shades - self._side_shade
        self._textures_on = True
        self._mini_map = np.where(self.engine.game_map.T, "#", " ")
        # Buffers
        self._pos_int = np.zeros((2,), dtype=int)
        self._pos_frac = np.zeros((2,), dtype=float)

    @property
    def textures_on(self) -> bool:
        """Whether wall textures are rendered."""
        return self.engine.wall_textures and self._textures_on

    def toggle_textures(self) -> None:
        """Toggle whether wall textures are rendered."""
        self._textures_on = not self._textures_on

    def resize(self, width: int, height: int) -> None:
        """Resize caster's buffer."""
        self.height = height
        """Height of caster's buffer."""
        self.width = width
        """Width of caster's buffer."""
        self.buffer = np.full((height, width), " ")
        """The array in which the caster renders."""

        # Precalculate angle of rays cast.
        self._ray_angles = angles = np.ones((width, 2), dtype=float)
        angles[:, 1] = np.linspace(-1, 1, width)

        # Buffers
        self._rotated_angles = np.zeros_like(angles)
        self._deltas = np.zeros_like(angles)
        self._sides = np.zeros_like(angles)
        self._steps = np.zeros_like(angles, dtype=int)
        self._weights = weights = np.zeros((height, 2), dtype=float)
        self._tex_frac = np.zeros_like(weights)
        self._tex_frac_2 = np.zeros_like(weights)
        self._tex_int = np.zeros_like(weights, dtype=int)
        self._column_distances = np.zeros((width,), dtype=float)

    def cast(self) -> None:
        """Cast rays and sprites and render minimap into buffer."""
        self.buffer[:] = " "
        self.buffer[self.height // 2 :, ::2] = self.ascii_map[1]

        # Early calculations on rays can be vectorized:
        np.dot(self._ray_angles, self.engine.camera._plane, out=self._rotated_angles)
        with np.errstate(divide="ignore"):
            np.true_divide(1.0, self._rotated_angles, out=self._deltas)
        np.absolute(self._deltas, out=self._deltas)
        np.sign(self._rotated_angles, out=self._steps, casting="unsafe")
        np.heaviside(self._steps, 1.0, out=self._sides)
        np.mod(self.engine.camera.pos, 1.0, out=self._pos_frac)
        np.subtract(self._sides, self._pos_frac, out=self._sides)
        np.multiply(self._sides, self._steps, out=self._sides)
        np.multiply(self._sides, self._deltas, out=self._sides)

        for column in range(self.width):
            self._cast_ray(column)
        self._cast_sprites()
        self._render_minimap()

    def _cast_ray(self, column: int) -> None:
        camera = self.engine.camera
        camera_pos = camera.pos
        game_map = self.engine.game_map

        ray_pos = self._pos_int
        ray_pos[:] = camera_pos
        ray_angle = self._rotated_angles[column]
        delta = self._deltas[column]
        step = self._steps[column]
        sides = self._sides[column]

        # Cast a ray until we hit a wall or hit max_hops
        for _ in range(self.max_hops):
            side = 0 if sides[0] < sides[1] else 1
            sides[side] += delta[side]
            ray_pos[side] += step[side]

            if texture_index := game_map[tuple(ray_pos)]:
                distance = (
                    ray_pos[side] - camera_pos[side] + (0 if step[side] == 1 else 1)
                ) / ray_angle[side]
                break
        else:  # No walls in range
            distance = 10000
            return

        self._column_distances[column] = distance

        h = self.height
        column_height = int(h / distance) if distance else 10000
        if column_height == 0:
            return  # Draw nothing

        half_height = h // 2
        half_column = column_height // 2
        if half_column > half_height:
            half_column = half_height

        start = half_height - half_column
        end = half_height + half_column
        drawn_height = end - start

        shade = min(drawn_height, self._shade_dif)
        if side:
            shade += self._side_shade

        shade_buffer = np.full(drawn_height, shade)

        if self.textures_on:
            tex = self.engine.wall_textures[texture_index - 1]
            tex_w, tex_h = tex.shape

            wall_x = (camera_pos[1 - side] + distance * ray_angle[1 - side]) % 1
            tex_x = int(wall_x * tex_w)
            if (-1 if side == 1 else 1) * ray_angle[side] < 0:
                tex_x = tex_w - tex_x - 1

            offset = (column_height - drawn_height) / 2
            ratio = tex_h / column_height
            tex_start = offset * ratio
            tex_end = (offset + drawn_height) * ratio
            tex_ys = np.linspace(
                tex_start, tex_end, num=drawn_height, endpoint=False, dtype=int
            )
            shade_buffer += self._shade_values[tex[tex_x, tex_ys]]
            np.clip(shade_buffer, 1, self._shades, out=shade_buffer)

        self.buffer[start:end, column] = self.ascii_map[shade_buffer]

    def _cast_sprites(self) -> None:
        h = self.height
        w = self.width
        camera = self.engine.camera
        sprites = self.engine.sprites
        sprite_textures = self.engine.sprite_textures
        column_distances = self._column_distances

        for sprite in sprites:
            sprite.relative = (sprite.pos[0] - camera.pos[0], sprite.pos[1] - camera.pos[1])
        sprites.sort(key=lambda s: s.relative[0] ** 2 + s.relative[1] ** 2, reverse=True)

        # Camera Inverse used to calculate transformed position of sprites.
        cam_inv = np.linalg.inv(-camera._plane[::-1])

        # Draw each sprite from furthest to closest.
        for sprite in sprites:
            # Transformed position of sprites due to camera position.
            x, y = sprite.relative @ cam_inv

            # If sprite is behind camera, don't draw it.
            if y <= 0:
                continue

            # Sprite x-position on screen.
            sprite_x = int(w / 2 * (1 + x / y))
            sprite_height = int(h / y)
            sprite_width = int(w / y / 2)
            # Is sprite too small?
            if sprite_height == 0 or sprite_width == 0:
                continue
            tex = sprite_textures[sprite.texture_index]
            tex_width, tex_height = tex.shape

            start_x = _clamp(0, -sprite_width // 2 + sprite_x, w)
            end_x = _clamp(0, sprite_width // 2 + sprite_x, w)
            columns = np.arange(start_x, end_x)
            columns = columns[y <= column_distances[columns]]
            clip_x = sprite_x - sprite_width / 2
            tex_xs = columns - clip_x
            tex_xs *= tex_width / sprite_width

            start_y = _clamp(0, int((h - sprite_height) / 2), h)
            end_y = _clamp(0, int((h + sprite_height) / 2), h)
            rows = np.arange(start_y, end_y, dtype=float)
            clip_y = (sprite_height - h) / 2
            rows += clip_y
            rows *= tex_height / sprite_height
            np.clip(rows, 0, None, out=rows)

            tex_rect = tex[tex_xs.astype(int)][:, rows.astype(int)].T
            self.buffer[start_y:end_y, columns] = np.where(
                tex_rect != "0", tex_rect, self.buffer[start_y:end_y, columns]
            )

    def _render_minimap(self) -> None:
        dst_width = round(self.minimap_width * self.width)
        if dst_width % 2 == 0:
            dst_width += 1

        dst_height = round(self.minimap_height * self.height)
        if dst_height % 2 == 0:
            dst_height += 1

        display = np.full((dst_height, dst_width), " ")
        x, y = self.engine.camera.pos
        dst_x = int(x) - dst_width // 2
        dst_y = int(y) - dst_height // 2
        if dst_x < 0:
            src_l = 0
            dst_l = -dst_x
        else:
            src_l = dst_x
            dst_l = 0

        if dst_y < 0:
            src_t = 0
            dst_t = -dst_y
        else:
            src_t = dst_y
            dst_t = 0

        src_height, src_width = self._mini_map.shape
        if dst_x + dst_width >= src_width:
            src_r = src_width
            dst_r = src_width - dst_x
        else:
            src_r = dst_x + dst_width
            dst_r = dst_width

        if dst_y + dst_height >= src_height:
            src_b = src_height
            dst_b = src_height - dst_y
        else:
            src_b = dst_y + dst_height
            dst_b = dst_height

        display[dst_t:dst_b, dst_l:dst_r] = self._mini_map[src_t:src_b, src_l:src_r]
        display[dst_height // 2, dst_width // 2] = "@"
        u, v = self.minimap_pos
        self.buffer[-dst_height - v : -v, -dst_width - u : -u] = display
