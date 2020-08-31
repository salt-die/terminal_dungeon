import os
import json
import curses
import numpy as np
from pathlib import Path

class Renderer:
    """
    The Renderer class is responsible for everything drawn on the screen --
    including the environment, sprites, menus, items. All textures stored here.
    """
    max_hops = 20  # How far rays are cast.

    # Shading constants -- Modifying ascii_map should be safe.
    ascii_map = np.array(list(' .,:;<+*LtCa4U80dQM@'))
    shades = len(ascii_map) - 1
    side_shade = (shades + 1) // 5
    shade_dif = shades - side_shade

    textures_on = True

    minimap_width = 3
    pad = 50

    def __init__(self, screen, player, wall_textures, sprite_textures):
        self.screen = screen
        self.resize()

        self.player = player
        self.game_map = player.game_map
        self.mini_map = np.pad(np.where(self.game_map._map.T, '#', ' '), self.pad, constant_values=' ')
        self._load_textures(wall_textures, sprite_textures)

    def resize(self):
        try: # linux
            self.width, self.height = os.get_terminal_size()
            curses.resizeterm(self.height, self.width)
        except: # windows
            self.height, self.width = self.screen.getmaxyx()
            os.system(f"mode con cols={self.width} lines={self.height}")
        self.angle_increment = 1 / self.width
        self.floor_y = self.height // 2
        self.distances = [0] * self.width

    def _load_textures(self, wall_textures, sprite_textures):
        self.textures = tex = []  # We may store the different texture types in different lists in the future.
        for name in wall_textures:
            filename = str(Path("wall_textures", name + ".txt"))
            with open(filename, "r") as file:
                tmp = file.read()
            tex.append(np.array([list(map(int, line)) for line in tmp.splitlines()]).T)

        for name in sprite_textures:
            filename = str(Path("sprite_textures", name + ".txt"))
            with open(filename, "r") as file:
                tmp = file.read()
            tex.append(np.array([list(line) for line in tmp.splitlines()]).T)

    def cast_ray(self, column):
        """
        Cast rays and draw columns whose heights correspond to the distance a ray traveled
        until it hit a wall.

        TODO: Pass a full numpy array of columns all at once.
        """
        ray_angle = self.player.cam.T @ np.array((1, 2 * column * self.angle_increment - 1))
        map_pos = self.player.pos.astype(int)
        with np.errstate(divide="ignore"):
            delta = abs(1 / ray_angle)
        step = 2 * np.heaviside(ray_angle, 1) - 1  # Same as np.sign except 0 is mapped to 1
        side_dis = step * (map_pos + (step + 1) / 2 - self.player.pos) * delta

        # Cast a ray until we hit a wall or hit max_range
        for hops in range(self.max_hops):
            side = 0 if side_dis[0] < side_dis[1] else 1
            side_dis[side] += delta[side]
            map_pos[side] += step[side]
            if self.game_map[tuple(map_pos)]:
                break
        else:  # No walls in range
            self.distances[column] = float("inf")
            return 0, 0, []

        # Avoiding euclidean distance, to avoid fish-eye effect.
        wall_dis = (map_pos[side] - self.player.pos[side] + (1 - step[side]) / 2) / ray_angle[side]
        # Save distance for sprite calculations.
        self.distances[column] = wall_dis

        line_height = int(self.height / wall_dis) if wall_dis else self.height
        if line_height == 0:
            return 0, 0, []  # Draw nothing

        jump_height = self.player.z * line_height
        line_start = max(0, int((-line_height + self.height) / 2 + jump_height))
        line_end = min(self.height, int((line_height + self.height) / 2 + jump_height))
        line_height = line_end - line_start  # Correct off-by-one errors

        shade = min(line_height, self.shade_dif)
        shade += 0 if side else self.side_shade  # One side is brighter

        shade_buffer = np.full(line_height, shade)

        if self.textures_on:
            tex_num = self.game_map[tuple(map_pos)] - 1
            texture_width, texture_height = self.textures[tex_num].shape

            wall_x = (self.player.pos[1 - side] + wall_dis * ray_angle[1 - side]) % 1
            tex_x = int(wall_x * texture_width)
            if (-1)**side * ray_angle[side] < 0:
                tex_x = texture_width - tex_x - 1

            tex_ys = (np.arange(line_height) * (texture_height / line_height)).astype(int)
            # Add or subtract texture values to shade values
            # Note 2 * n - 12 is 0 for n = 6, i.e., values above 6 are additive and
            # below 6 are subtractive. For larger ascii maps, one may want to use linear
            # equation with a larger slope.
            shade_buffer += 2 * self.textures[tex_num][tex_x, tex_ys] - 12
            np.clip(shade_buffer, 1, self.shades, out=shade_buffer)

        self.buffer[line_start:line_end, column] = self.ascii_map[shade_buffer]

    def cast_sprites(self):
        for sprite in self.game_map.sprites:
            # Relative position of sprite to player
            sprite["relative"] = self.player.pos - sprite["pos"]

        # Sprites sorted by distance (squared) from player.
        sorted_sprites = sorted(self.game_map.sprites,
                                key=lambda s:s["relative"] @ s["relative"], reverse=True)

        # Camera Inverse used to calculate transformed position of sprites.
        cam_inv = np.linalg.inv(-self.player.cam[::-1])

        for sprite in sorted_sprites: # Draw each sprite from furthest to closest.
            # Transformed position of sprites due to camera's plane and angle
            trans_pos = sprite["relative"] @ cam_inv

            if trans_pos[1] <= 0:  # Sprite is behind player, don't draw it.
                continue

            # Sprite x-position on screen
            sprite_x = int(self.width / 2 * (1 + trans_pos[0] / trans_pos[1]))

            sprite_height = int(self.height / trans_pos[1])
            sprite_width = int(self.width / trans_pos[1] / 2)
            if not (sprite_height and sprite_width):  # Sprite too small.
                continue

            jump_height = self.player.z * sprite_height
            start_y = max(0, int((-sprite_height + self.height) / 2 + jump_height))
            end_y = min(self.height, int((sprite_height + self.height) / 2 + jump_height))

            start_x = max(0, -sprite_width // 2 + sprite_x)
            end_x = min(self.width, sprite_width // 2 + sprite_x)

            tex_width, tex_height = self.textures[sprite["image"]].shape

            # Calculate some constants outside the next loops:
            clip_x = sprite_x - sprite_width / 2
            clip_y = (sprite_height - self.height) / 2 - self.player.z * sprite_height
            width_ratio = tex_width / sprite_width
            height_ratio = tex_height / sprite_height

            # Draw sprite -- outer-loop, left-to-right; inner, top-to-bottom
            for column in range(start_x, end_x):
                # From which column in the texture characters are taken
                tex_x = int((column - clip_x) * width_ratio)

                # Check that column isn't off-screen and that sprite isn't blocked by a wall.
                if not (0 <= column <= self.width and trans_pos[1] <= self.distances[column]):
                    continue

                tex_ys = np.clip((np.arange(start_y, end_y) + clip_y) * height_ratio, 0, None).astype(int)
                self.buffer[start_y:end_y, column] = np.where(self.textures[sprite["image"]][tex_x, tex_ys] != "0",
                                                              self.textures[sprite["image"]][tex_x, tex_ys],
                                                              self.buffer[start_y:end_y, column])

    def draw_minimap(self):
        pad = self.pad
        width = self.minimap_width

        start_col = 2 * (self.width // width) - 2
        start_row = 2 * (self.height // width) - 1
        x, y = self.player.pos.astype(int) + pad
        half_w = self.width // width // 2
        half_h = self.height // width // 2

        self.buffer[start_row: start_row + 2 * half_h,
                    start_col: start_col + 2 * half_w] = self.mini_map[y - half_h: y + half_h,
                                                                       x - half_w: x + half_w]
        self.buffer[start_row + half_h, start_col + half_w] = '@'

    def update(self):
        self.buffer = np.full((self.height, self.width), " ") # Clear buffer

        self.buffer[self.floor_y:, :] = self.ascii_map[1] # Draw floor

        for column in range(self.width - 1): # Draw walls
            self.cast_ray(column)

        self.cast_sprites()

        self.draw_minimap()

        self.render()

    def render(self):
        for row_num, row in enumerate(self.buffer):
            self.screen.addstr(row_num, 0, ''.join(row[:-1]))
        self.screen.refresh()
