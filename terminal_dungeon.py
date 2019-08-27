# -*- coding: utf-8 -*-
"""
A terminal based ray-casting engine.

'esc' to exit
't' to turn off textures

IMPORTANT:
Make sure the pygame window is focused for input events to be received.

Depending on your terminal font, Renderer.ascii_map may need to be adjusted.
If you'd like to make an ascii map more suitable to your terminal's font,
check my Snippets repository for a script that grabs mean brightness of
unicode characters.

Values stored in textures should range from 0-9.  Values below 6 are
subtractive and above 6 are additive.
"""
import json
import curses
import numpy as np
import pygame

class Map:
    """
    A helper class for easy loading of maps.

    Each sprite is a dict with keys "pos","image","relative" for position,
    sprite image number, and relative position to player (which will be set
    after first call to cast_sprites in the renderer).
    """
    __map = 0
    def __init__(self, file_name):
        self.sprites = []
        self.load(file_name)

    def load(self, file_name):
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
    def __init__(self, game_map, pos=np.array([5., 5.]),
                 initial_angle=0):
        #Settings======================================================
        self.speed = .1
        self.rotate_speed = .05
        self.jump_time = 8
        self.field_of_view = .6 #Somewhere between 0 and 1 is reasonable

        self.game_map = game_map
        self.pos = pos
        self.cam = np.array([[1, 0], [0, self.field_of_view]]) @\
                   np.array([[np.cos(initial_angle), np.sin(initial_angle)],
                             [-np.sin(initial_angle), np.cos(initial_angle)]])
        self.left = np.array([[np.cos(-self.rotate_speed),
                               np.sin(-self.rotate_speed)],
                              [-np.sin(-self.rotate_speed),
                                np.cos(-self.rotate_speed)]])
        self.right = np.array([[np.cos(self.rotate_speed),
                                np.sin(self.rotate_speed)],
                               [-np.sin(self.rotate_speed),
                                np.cos(self.rotate_speed)]])
        self.perp = np.array([[0., -1.],
                              [1., 0.]])
        self.time_in_jump = 0
        self.z = 0.
        self.is_jumping = False

    def update(self):
        #We'll have more to do here eventually.
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

        #If we can move both coordinates at once, we should
        if not self.game_map[tuple(next_step.astype(int))]:
            self.pos = next_step

        #Allows 'sliding' on walls
        elif not self.game_map[int(next_step[0])][int(self.pos[1])]:
            self.pos[0] = next_step[0]
        elif not self.game_map[int(self.pos[0])][int(next_step[1])]:
            self.pos[1] = next_step[1]


class Renderer:
    """
    The Renderer class is responsible for everything drawn on the screen --
    including the environment, sprites, menus, items. All textures stored here.
    """
    def __init__(self, screen, player, game_map, *textures):
        #Settings======================================================
        self.max_hops = 60 #How far rays are cast.

        self.screen = screen
        self.height, self.width = screen.getmaxyx()
        self.floor_y = self.height // 2
        self.distances = [0] * self.width
        self.player = player
        self.game_map = game_map
        self.buffer = np.full((self.height, self.width), " ", dtype=str)
        self.textures = []
        self.load_textures(*textures)
        self.textures_on = True

        #So we have fewer arrays to initialize inside loops============
        self.hght_inv = np.array([0, 1 / self.height])
        self.const = np.array([1, -1])

        #Shading Constants--It's safe to modify ascii_map==============
        self.ascii_map = dict(enumerate(list(' .,:;<+*LtCa4U80dQM@')))
        self.shades = len(self.ascii_map) - 1
        self.side_shade = (self.shades + 1) // 5
        self.shade_dif = self.shades - self.side_shade

    def load_textures(self, *texture_names):
        textures = []
        for name in texture_names:
            with open(name + ".json", 'r') as texture:
                pre_load = json.load(texture)
                textures.append(np.array(pre_load).T)
        self.textures = textures

    def cast_ray(self, column):
        ray_angle = self.player.cam.T @ (column * self.hght_inv + self.const)
        map_pos = self.player.pos.astype(int)
        with np.errstate(divide="ignore"):
            delta = abs(1 / ray_angle)
        step = 2 * np.heaviside(ray_angle, 1) - 1
        side_dis = step * (map_pos + (step + 1) / 2 - self.player.pos) * delta

        #Distance to wall
        for hops in range(self.max_hops):
            side = 0 if side_dis[0] < side_dis[1] else 1
            side_dis[side] += delta[side]
            map_pos[side] += step[side]
            if self.game_map[tuple(map_pos)]:
                break
            if hops == self.max_hops - 1: #No walls in range
                self.distances[column] = float("inf")
                return float("inf"), side, map_pos, ray_angle

        #Avoiding euclidean distance, to avoid fish-eye effect.
        wall_dis =\
         (map_pos[side] - self.player.pos[side] + (1 - step[side]) / 2)\
         / ray_angle[side]
        #Save distance for sprite calculations.
        self.distances[column] = wall_dis
        return wall_dis, side, map_pos, ray_angle

    def draw_column(self, wall_dis, side, map_pos, ray_angle):
        line_height = int(self.height / wall_dis) if wall_dis else self.height
        if line_height == 0:
            return 0, 0, [] #Draw nothing

        line_start, line_end =\
         [int((i * line_height + self.height) / 2 +
              self.player.z * line_height) for i in [-1, 1]]
        line_start = 0 if line_start < 0 else line_start
        line_end = self.height if line_end > self.height else line_end
        line_height = line_end - line_start #Correct off-by-one errors

        #Shading
        shade = line_height if line_height < self.shade_dif else self.shade_dif
        shade += 0 if side else self.side_shade #One side is brighter

        #A buffer to store shade values
        shade_buffer = [shade] * line_height

        #Texturing
        if self.textures_on:
            tex_num = self.game_map[tuple(map_pos)] - 1
            texture_width, texture_height = self.textures[tex_num].shape

            wall_x =\
             (self.player.pos[1 - side] + wall_dis * ray_angle[1 - side]) % 1
            tex_x = int(wall_x * texture_width)
            if -1**side * ray_angle[side] < 0:
                tex_x = texture_width - tex_x - 1

            #Add or subtract texture values to shade values
            tex_to_wall_ratio = texture_height / line_height
            for i, val in enumerate(shade_buffer):
                tex_y = int(i * tex_to_wall_ratio)
                val += 2 * self.textures[tex_num][tex_x, tex_y] - 12

                #Write to shade_buffer, this clipping logic will be changed
                #in the future.
                if val <= 1:
                    shade_buffer[i] = 1
                elif 1 < val <= self.shades:
                    shade_buffer[i] = val
                else:
                    shade_buffer[i] = self.shades

        #Convert shade values to ascii; convert to array to broadcast to buffer
        column_buffer = [self.ascii_map[val] for val in shade_buffer]
        column_buffer = np.array(column_buffer, dtype=str)
        return line_start, line_end, column_buffer

    def cast_sprites(self):
        #For each sprite, calculate distance (squared) to player
        sprite_distances = {}
        for i, sprite in enumerate(self.game_map.sprites):
            #Relative position of sprite to player
            sprite["relative"] = self.player.pos - sprite["pos"]
            sprite_distances[i] = sprite["relative"] @ sprite["relative"]

        #Sprites sorted by distance from player.
        sorted_sprites = sorted(sprite_distances, key=sprite_distances.get,
                                reverse=True)
        sorted_sprites = [self.game_map.sprites[i] for i in sorted_sprites]

        #Camera Inverse used to calculate transformed position of sprites.
        cam_inv = np.linalg.inv(-self.player.cam[::-1])

        #Draw each sprite from furthest to closest.
        for sprite in sorted_sprites:
            #Transformed position of sprites due to camera's plane and angle
            trans_pos = sprite["relative"] @ cam_inv

            if trans_pos[1] <= 0: #Sprite is behind player, don't draw it.
                continue

            #Sprite x-position on screen
            sprite_x = int(self.height * (1 + trans_pos[0] / trans_pos[1]) - 1)
            #Sprite width and height
            sprite_height = int(self.height / trans_pos[1])
            sprite_width = int(self.width / trans_pos[1] / 2)
            if not all([sprite_height, sprite_width]): #Sprite too small.
                continue

            #Start and end points of vertical lines of the sprite
            start_y, end_y = [int((i * sprite_height + self.height) / 2
                              + self.player.z * sprite_height)
                              for i in [-1, 1]]
            if start_y < 0: start_y = 0
            if end_y >= self.height: end_y = self.height

            #Start and end points of horizontal lines
            start_x, end_x = [(i * sprite_width // 2 + sprite_x)
                              for i in [-1, 1]]
            if start_x < 0: start_x = 0
            if end_x > self.width: end_x = self.width

            tex_width, tex_height = self.textures[sprite["image"]].shape

            #Calculate some constants outside the next loops:
            clip_x = sprite_x - sprite_width / 2
            clip_y = (sprite_height - self.height) / 2\
                      - self.player.z * sprite_height
            width_ratio = tex_width / sprite_width
            height_ratio = tex_height / sprite_height

            #Draw sprite -- outer-loop, left-to-right; inner, top-to-bottom
            for column in range(start_x, end_x):
                #From which column in the texture characters are taken
                tex_x = int((column - clip_x) * width_ratio)

                #Check that column isn't off-screen and that sprite isn't
                #blocked by a wall
                if 0 <= column <= self.width and\
                   trans_pos[1] <= self.distances[column]:

                    vertical_buffer = [0] * (end_y - start_y)

                    for i in range(start_y, end_y):
                        #From which row characters are taken
                        tex_y = int((i + clip_y) * height_ratio)
                        char = self.textures[sprite["image"]][tex_x, tex_y]
                        vertical_buffer[i - start_y] = char\
                            if char != "0" else self.buffer[i, column]

                    #Convert to array to broadcast into buffer
                    vertical_buffer = np.array(vertical_buffer, dtype=str)
                    self.buffer[start_y:end_y, column] = vertical_buffer

    def update(self):
        #Clear buffer
        self.buffer = np.full((self.height, self.width), " ", dtype=str)

        #Draw floor
        self.buffer[self.floor_y:, :] = self.ascii_map[1]

        #Draw walls
        for column in range(self.width-1):
            start, end, col_buffer = self.draw_column(*self.cast_ray(column))
            self.buffer[start:end, column] = col_buffer
        self.cast_sprites()
        self.render()

    def render(self):
        for row_num, row in enumerate(self.buffer):
            self.screen.addstr(row_num, 0, ''.join(row[:-1]))
        self.screen.refresh()


class Controller():
    """
    Controller class handles user input and updates all other objects.
    """
    def __init__(self, player, renderer):
        self.running = True
        self.player = player
        self.renderer = renderer
        self.clock = pygame.time.Clock()
        self.keys = [False] * 324
        self.jumping_keys = [False] * 324
        self.player_has_jumped = False

    def user_input(self):
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_t:
                    self.renderer.textures_on = not self.renderer.textures_on
                self.keys[event.key] = True
            elif event.type == pygame.KEYUP:
                self.keys[event.key] = False

    def move_player(self):
        #We stop accepting move inputs (but turning is ok) in the middle of a
        #jump -- the effect is momentum-like movement while in the air.
        keys = self.jumping_keys if self.player.is_jumping else self.keys
        if self.player_has_jumped:
            self.jumping_keys = self.keys.copy()
            self.player_has_jumped = False

        #Constants that make the following conditionals much more readable
        left = self.keys[pygame.K_LEFT] or self.keys[pygame.K_a]
        right = self.keys[pygame.K_RIGHT] or self.keys[pygame.K_d]
        up = keys[pygame.K_UP] or keys[pygame.K_w]
        down = keys[pygame.K_DOWN] or keys[pygame.K_s]
        strafe_l = keys[pygame.K_q]
        strafe_r = keys[pygame.K_e]

        if left ^ right:
            self.player.turn(left)
        if up ^ down:
            self.player.move((up - down) * self.player.speed)
        if strafe_l ^ strafe_r:
            self.player.move((strafe_l - strafe_r) * self.player.speed, True)
        if self.keys[pygame.K_SPACE]:
            self.player_has_jumped = True
            self.player.is_jumping = True
            self.keys[pygame.K_SPACE] = False

    def update(self):
        self.renderer.update()
        self.user_input()
        self.move_player()
        self.player.update()
        self.clock.tick(40)


def main(screen):
    init_curses(screen)
    init_pygame()
    game_map = Map("map1")
    player = Player(game_map)

    #We may mass load textures in the future and pass the list to renderer.
    renderer = Renderer(screen, player, game_map,
                        "texture1", "texture2", "texture3")
    controller = Controller(player, renderer)
    while controller.running:
        controller.update()
    pygame.display.quit()
    pygame.quit()

def init_pygame():
    pygame.init()
    pygame.display.set_mode((305, 2))
    pygame.display.set_caption('Focus this window to move.')

def init_curses(screen):
    curses.noecho()
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    screen.attron(curses.color_pair(1))
    screen.clear()

if __name__ == "__main__":
    curses.wrapper(main)
