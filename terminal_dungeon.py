"""
A terminal based ray-casting engine.

'esc' to exit
't' to turn off textures
'wasdqe' or arrow-keys to move
'space' to jump

Depending on your terminal font, Renderer.ascii_map may need to be adjusted.
If you'd like to make an ascii map more suitable to your terminal's font,
check my Snippets repository for a script that grabs mean brightness of
unicode characters.

Values stored in textures should range from 0-9.  Values below 6 are
subtractive and above 6 are additive.
"""
from collections import defaultdict
import json
import numpy as np
import curses
from pynput import keyboard
from pynput.keyboard import Key, KeyCode


def rotation_matrix(theta):
    """
    Returns a 2-dimensional rotation array of a given angle.
    """
    return np.array([[np.cos(theta), np.sin(theta)],
                     [-np.sin(theta), np.cos(theta)]])

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
            self.__map = np.array(map_dict["map"]).T
            self.sprites = map_dict["sprites"]
        for sprite in self.sprites: #lists --> numpy arrays
            sprite["pos"] = np.array(sprite["pos"])

    def __getitem__(self, key):
        return self.__map[key]


class Player:
    """
    Player class with methods for moving and updating any effects on the
    player such as falling.
    """
    speed = .1

    rotate_speed = .05

    # Jump implementation could use some improvement
    jump_time = 8
    time_in_jump = 0
    z = 0.0
    is_jumping = False

    field_of_view = .6  # Somewhere between 0 and 1 is reasonable

    left = rotation_matrix(-rotate_speed)
    right = rotation_matrix(rotate_speed)

    perp = np.array([[0., -1.],
                     [1., 0.]])

    def __init__(self, game_map, pos=np.array([5., 5.]), initial_angle=0):
        self.game_map = game_map
        self.pos = pos
        self.cam = np.array([[1, 0], [0, self.field_of_view]]) @ rotation_matrix(initial_angle)

    def update(self):
        # We'll have more to do here eventually.
        self.fall()

    def fall(self):
        if not self.is_jumping:
            return
        if self.time_in_jump >= 2 * self.jump_time:
            self.is_jumping, self.time_in_jump, self.z = False, 0, 0.
            return
        self.z +=\
         (self.jump_time - self.time_in_jump)**2 / (10 * self.jump_time**2)\
          * (1 if self.time_in_jump < self.jump_time else -1)
        self.time_in_jump += 1

    def turn(self, left=True):
        self.cam = self.cam @ (self.left if left else self.right)

    def move(self, speed, strafe=False):
        next_step = self.pos + speed * \
                    (self.cam[0] @ self.perp if strafe else self.cam[0])

        # If we can move both coordinates at once, we should
        if not self.game_map[tuple(next_step.astype(int))]:
            self.pos = next_step

        # Allows 'sliding' on walls
        elif not self.game_map[int(next_step[0])][int(self.pos[1])]:
            self.pos[0] = next_step[0]
        elif not self.game_map[int(self.pos[0])][int(next_step[1])]:
            self.pos[1] = next_step[1]


class Renderer:
    """
    The Renderer class is responsible for everything drawn on the screen --
    including the environment, sprites, menus, items. All textures stored here.
    """
    max_hops = 60  # How far rays are cast.
    const = np.array([1, -1])

    # Shading constants -- Modifying ascii_map should be safe.
    ascii_map = np.array(list(' .,:;<+*LtCa4U80dQM@'))
    shades = len(ascii_map) - 1
    side_shade = (shades + 1) // 5
    shade_dif = shades - side_shade

    textures_on = True

    def __init__(self, screen, player, game_map, *textures):
        self.screen = screen
        self.height, self.width = self.screen.getmaxyx()
        self.hght_inv = np.array([0, 1 / self.height])
        self.floor_y = self.height // 2
        self.distances = [0] * self.width

        self.player = player
        self.game_map = game_map
        self._load_textures(*textures)

    def _load_textures(self, *texture_names):
        self.textures = []
        for name in texture_names:
            with open(name + ".json", 'r') as texture:
                pre_load = json.load(texture)
                self.textures.append(np.array(pre_load).T)

    def cast_ray(self, column):
        """
        Cast rays and draw columns whose heights correspond to the distance a ray traveled
        until it hit a wall.

        TODO: Pass a full numpy array of columns all at once.
        """
        ray_angle = self.player.cam.T @ (column * self.hght_inv + self.const)
        map_pos = self.player.pos.astype(int)
        with np.errstate(divide="ignore"):
            delta = abs(1 / ray_angle)
        step = 2 * np.heaviside(ray_angle, 1) - 1
        side_dis = step * (map_pos + (step + 1) / 2 - self.player.pos) * delta

        # Cast a ray until we hit a wall or hit max_range
        for hops in range(self.max_hops):
            side = 0 if side_dis[0] < side_dis[1] else 1
            side_dis[side] += delta[side]
            map_pos[side] += step[side]
            if self.game_map[tuple(map_pos)]:
                break
        else:
            # No walls in range
            self.distances[column] = float("inf")
            return float("inf"), side, map_pos, ray_angle

        # Avoiding euclidean distance, to avoid fish-eye effect.
        wall_dis = (map_pos[side] - self.player.pos[side] + (1 - step[side]) / 2) / ray_angle[side]
        # Save distance for sprite calculations.
        self.distances[column] = wall_dis

        line_height = int(self.height / wall_dis) if wall_dis else self.height
        if line_height == 0:
            return 0, 0, []  # Draw nothing

        line_start = max(0, int((-line_height + self.height) / 2 + self.player.z * line_height))
        line_end = min(self.height, int((line_height + self.height) / 2 + self.player.z * line_height))
        line_height = line_end - line_start  # Correct off-by-one errors

        # Shading
        shade = min(line_height, self.shade_dif)
        shade += 0 if side else self.side_shade  # One side is brighter

        # A buffer to store shade values
        shade_buffer = np.full(line_height, shade)

        # Texturing
        if self.textures_on:
            tex_num = self.game_map[tuple(map_pos)] - 1
            texture_width, texture_height = self.textures[tex_num].shape

            wall_x =\
             (self.player.pos[1 - side] + wall_dis * ray_angle[1 - side]) % 1
            tex_x = int(wall_x * texture_width)
            if -1**side * ray_angle[side] < 0:
                tex_x = texture_width - tex_x - 1

            # Add or subtract texture values to shade values
            tex_ys = (np.arange(line_height) * texture_height / line_height).astype(int)
            shade_buffer += 2 * self.textures[tex_num][tex_x, tex_ys] - 12
            np.clip(shade_buffer, 1, self.shades, out=shade_buffer)

        return line_start, line_end, self.ascii_map[shade_buffer]

    def cast_sprites(self):
        # For each sprite, calculate distance (squared) to player
        sprite_distances = {}
        for i, sprite in enumerate(self.game_map.sprites):
            # Relative position of sprite to player
            sprite["relative"] = self.player.pos - sprite["pos"]
            sprite_distances[i] = sprite["relative"] @ sprite["relative"]

        # Sprites sorted by distance from player.
        sorted_sprites = sorted(sprite_distances, key=sprite_distances.get, reverse=True)
        sorted_sprites = [self.game_map.sprites[i] for i in sorted_sprites]

        # Camera Inverse used to calculate transformed position of sprites.
        cam_inv = np.linalg.inv(-self.player.cam[::-1])

        # Draw each sprite from furthest to closest.
        for sprite in sorted_sprites:
            # Transformed position of sprites due to camera's plane and angle
            trans_pos = sprite["relative"] @ cam_inv

            if trans_pos[1] <= 0:  # Sprite is behind player, don't draw it.
                continue

            # Sprite x-position on screen
            sprite_x = int(self.height * (1 + trans_pos[0] / trans_pos[1]) - 1)
            # Sprite width and height
            sprite_height = int(self.height / trans_pos[1])
            sprite_width = int(self.width / trans_pos[1] / 2)
            if not all([sprite_height, sprite_width]): #Sprite too small.
                continue

            # Start and end points of vertical lines of the sprite
            start_y, end_y = [int((i * sprite_height + self.height) / 2
                              + self.player.z * sprite_height)
                              for i in [-1, 1]]
            if start_y < 0: start_y = 0
            if end_y >= self.height: end_y = self.height

            # Start and end points of horizontal lines
            start_x, end_x = [(i * sprite_width // 2 + sprite_x)
                              for i in [-1, 1]]
            if start_x < 0: start_x = 0
            if end_x > self.width: end_x = self.width

            tex_width, tex_height = self.textures[sprite["image"]].shape

            # Calculate some constants outside the next loops:
            clip_x = sprite_x - sprite_width / 2
            clip_y = (sprite_height - self.height) / 2\
                      - self.player.z * sprite_height
            width_ratio = tex_width / sprite_width
            height_ratio = tex_height / sprite_height

            # Draw sprite -- outer-loop, left-to-right; inner, top-to-bottom
            for column in range(start_x, end_x):
                # From which column in the texture characters are taken
                tex_x = int((column - clip_x) * width_ratio)

                # Check that column isn't off-screen and that sprite isn't blocked by a wall.
                if 0 <= column <= self.width and\
                   trans_pos[1] <= self.distances[column]:

                    vertical_buffer = [0] * (end_y - start_y)

                    for i in range(start_y, end_y):
                        # From which row characters are taken
                        tex_y = int((i + clip_y) * height_ratio)
                        char = self.textures[sprite["image"]][tex_x, tex_y]
                        vertical_buffer[i - start_y] = char\
                            if char != "0" else self.buffer[i, column]

                    # Convert to array to broadcast into buffer
                    vertical_buffer = np.array(vertical_buffer, dtype=str)
                    self.buffer[start_y:end_y, column] = vertical_buffer

    def update(self):
        # Clear buffer
        self.buffer = np.full((self.height, self.width), " ", dtype=str)

        # Draw floor
        self.buffer[self.floor_y:, :] = self.ascii_map[1]

        # Draw walls
        for column in range(self.width - 1):
            start, end, col_buffer = self.cast_ray(column)
            self.buffer[start:end, column] = col_buffer

        # Draw sprites
        self.cast_sprites()

        # Push buffer to screen
        self.render()

    def render(self):
        for row_num, row in enumerate(self.buffer):
            self.screen.addstr(row_num, 0, ''.join(row[:-1]))
        self.screen.refresh()


class Controller():
    """
    Controller class handles user input and updates all other objects.
    """
    running = True
    keys = jumping_keys = defaultdict(bool)
    player_has_jumped = False

    def __init__(self, player, renderer):
        self.player = player
        self.renderer = renderer
        self.listener = keyboard.Listener(on_press=self.pressed,
                                          on_release=self.released)
        self.listener.start()

    def user_input(self):
        if self.keys[Key.esc]:
            self.running = False
            self.listener.stop()
        if self.keys[KeyCode(char='t')]:
            self.renderer.textures_on = not self.renderer.textures_on
            self.keys[KeyCode(char='t')] = False
        self.movement()

    def pressed(self, key):
        self.keys[key] = True

    def released(self, key):
        self.keys[key] = False

    def movement(self):
        # We stop accepting move inputs (but turning is ok) in the middle of a
        # jump -- the effect is momentum-like movement while in the air.
        keys = self.jumping_keys if self.player.is_jumping else self.keys
        if self.player_has_jumped:
            self.jumping_keys = self.keys.copy()
            self.player_has_jumped = False

        # Constants that make the following conditionals much more readable
        left = self.keys[Key.left] or self.keys[KeyCode(char='a')]
        right = self.keys[Key.right] or self.keys[KeyCode(char='d')]
        up = keys[Key.up] or keys[KeyCode(char='w')]
        down = keys[Key.down] or keys[KeyCode(char='s')]
        strafe_l = keys[KeyCode(char='q')]
        strafe_r = keys[KeyCode(char='e')]

        if left ^ right:
            self.player.turn(left)
        if up ^ down:
            self.player.move((up - down) * self.player.speed)
        if strafe_l ^ strafe_r:
            self.player.move((strafe_l - strafe_r) * self.player.speed, True)
        if self.keys[Key.space]:
            self.player_has_jumped = True
            self.player.is_jumping = True
            self.keys[Key.space] = False

    def update(self):
        self.renderer.update()
        self.user_input()
        self.player.update()

def main(screen):
    init_curses(screen)
    game_map = Map("map1")
    player = Player(game_map)
    # We may mass load textures in the future and pass the list to renderer.
    renderer = Renderer(screen, player, game_map,
                        "texture1", "texture2", "texture3")
    controller = Controller(player, renderer)
    while controller.running:
        controller.update()
    curses.flushinp()
    curses.endwin()

def init_curses(screen):
    curses.noecho()
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    screen.attron(curses.color_pair(1))
    screen.clear()

if __name__ == "__main__":
    curses.wrapper(main)
