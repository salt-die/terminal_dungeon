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
import curses
import numpy as np
import pygame

class Map:
    """
    Intend to change map files from txt into json to store arbitrary values
    at each location.  Also can simultaneouly load sprite positions.
    """
    __map = 0
    def __init__(self, file_name):
        self.load(file_name)
        self.sprites = None

    def load(self, map_name):
        with open(map_name + ".txt", 'r') as a_map:
            world_map = [[int(char) for char in row]\
                          for row in a_map.read().splitlines()]
        self.__map = np.array(world_map).T

    def __getitem__(self, key):
        return self.__map[key]


class Player:
    def __init__(self, game_map, pos=np.array([5., 5.]),\
                 angle=np.array([1., 0.]), plane=np.array([0., 1.])):
        self.game_map = game_map
        self.pos = pos
        self.field_of_view = .6 #Somewhere between 0 and 1 is reasonable
        self.cam = np.array([angle, self.field_of_view * plane])
        self.speed = .1
        self.rotate_speed = .05
        self.left = np.array([[np.cos(-self.rotate_speed),\
                               np.sin(-self.rotate_speed)],\
                              [-np.sin(-self.rotate_speed),\
                                np.cos(-self.rotate_speed)]])
        self.right = np.array([[np.cos(self.rotate_speed),\
                                np.sin(self.rotate_speed)],\
                               [-np.sin(self.rotate_speed),\
                                np.cos(self.rotate_speed)]])
        self.perp = np.array([[0., -1.],\
                              [1., 0.]])
        self.jump_time = 9
        self.time_in_jump = 0
        self.z = 0.
        self.is_falling = False

    def update(self):
        #We'll have more to do here eventually.
        self.fall()

    def jump(self):
        if self.is_falling:
            return
        self.is_falling = True

    def fall(self):
        if not self.is_falling:
            return
        if self.time_in_jump >= 2 * self.jump_time:
            self.is_falling, self.time_in_jump, self.z = False, 0, 0.
            return
        self.z +=\
         (self.jump_time - self.time_in_jump)**2 / (10 * self.jump_time**2)\
          * (1 if self.time_in_jump < self.jump_time else -1)
        self.time_in_jump += 1

    def turn(self, left=True):
        self.cam = self.cam @ (self.left if left else self.right)

    def move(self, forward=1, strafe=False):
        next_step = (self.pos + forward * self.cam[0] * self.speed @ self.perp)\
                    if strafe else\
                    (self.pos + forward * self.cam[0] * self.speed)
        #If we can move both coordinates at once, we should
        if not self.game_map[tuple(next_step.astype(int))]:
            self.pos = next_step
        #Allows 'sliding' on walls
        elif not self.game_map[int(next_step[0])][int(self.pos[1])]:
            self.pos[0] = next_step[0]
        elif not self.game_map[int(self.pos[0])][int(next_step[1])]:
            self.pos[1] = next_step[1]


class Renderer:
    def __init__(self, screen, player, *textures):
        self.screen = screen
        self.height, self.width = screen.getmaxyx()
        self.player = player
        self.buffer = np.full((self.height, self.width), " ", dtype=str)
        self.textures = []
        self.load_textures(*textures)
        self.textures_on = True

        #So we have fewer arrays to initialize inside loops============
        self.hght_inv = np.array([0, 1 / self.height])
        self.const = np.array([1, -1])
        #==============================================================

        #It's safe to modify ascii_map, but if the length changes, one will
        #have to fiddle with shading and texturing constants.
        #==============================================================
        self.ascii_map = dict(enumerate(list(' .,:;<+*LtCa4U80dQM@')))
        #==============================================================
        self.shades = len(self.ascii_map)

        #Settings======================================================
        self.max_hops = 60 #Controls how far rays are cast.
        self.wall_height = 1.1
        self.wall_y = 0. #Wall vertical placement
        #==============================================================
        self.floor_y = int(self.height / 2  + self.wall_y)


    def load_textures(self, *texture_names):
        textures = []
        for name in texture_names:
            with open(name+".txt", 'r') as texture:
                pre_load = [[int(char) for char in row]\
                            for row in texture.read().splitlines()]
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
            if self.player.game_map[tuple(map_pos)]:
                break
            if hops == self.max_hops - 1: #No walls in range
                return float("inf"), side, map_pos, ray_angle
        #Avoiding euclidean distance, to avoid fish-eye effect.
        wall_dis =\
         (map_pos[side] - self.player.pos[side] + (1 - step[side]) / 2)\
         / ray_angle[side]
        return wall_dis, side, map_pos, ray_angle

    def draw_column(self, wall_dis, side, map_pos, ray_angle):
        if wall_dis == 0:
            line_height = self.height
        else:
            line_height = int(self.height / wall_dis)
        if line_height == 0:
            return 0, 0, [] #Draw nothing
        line_start, line_end =\
         [int((i * line_height * self.wall_height + self.height) / 2 +\
              self.wall_y + self.player.z * line_height) for i in [-1, 1]]
        line_start = 0 if line_start < 0 else line_start
        line_end = self.height if line_end > self.height else line_end
        line_height = line_end - line_start #Correct off-by-one errors
        #Shading
        shade = int(15 if wall_dis > 15 else wall_dis)
        shade = 15 - shade + (0 if side else 4) #One side is brighter
        #Write column to a temporary buffer
        shade_buffer = [shade] * line_height

        #Texturing
        if self.textures_on:
            tex_num = self.player.game_map[map_pos[0]][map_pos[1]] - 1
            texture_width, texture_height = self.textures[tex_num].shape
            wall_x =\
             (self.player.pos[-side + 1] + wall_dis * ray_angle[-side + 1]) % 1
            tex_x = int(wall_x * texture_width)
            if (side * 2 - 1) * ray_angle[side] < 0:
                tex_x = texture_width - tex_x - 1
            #Add or subtract texture values to shade values
            tex_to_wall_ratio = 1 / line_height * texture_height
            for i, val in enumerate(shade_buffer):
                tex_y = int(i * tex_to_wall_ratio)
                new_shade_val =\
                 2 * self.textures[tex_num][tex_x][tex_y] - 12 + val
                if new_shade_val < 1:
                    shade_buffer[i] = 1
                elif 0 <= new_shade_val <= self.shades - 1:
                    shade_buffer[i] = new_shade_val
                else:
                    shade_buffer[i] = self.shades - 1

        #Convert shade values to ascii
        column_buffer = [self.ascii_map[val] for val in shade_buffer]
        column_buffer = np.array(column_buffer, dtype=str)
        return line_start, line_end, column_buffer

    def cast_sprite(self):
        pass

    def update(self):
        #Clear buffer
        self.buffer = np.full((self.height, self.width), " ", dtype=str)
        #Draw floor
        self.buffer[self.floor_y:, :] = self.ascii_map[1]
        #Draw Columns
        for column in range(self.width-1):
            start, end, col_buffer = self.draw_column(*self.cast_ray(column))
            self.buffer[start:end, column] = col_buffer
        self.render()

    def render(self):
        for row_num, row in enumerate(self.buffer):
            self.screen.addstr(row_num, 0, ''.join(row[:-1]))
        self.screen.refresh()


class Controller():
    def __init__(self, player, renderer):
        self.running = True
        self.player = player
        self.renderer = renderer
        self.clock = pygame.time.Clock()
        self.keys = [False] * 324

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
        if self.keys[pygame.K_LEFT] or self.keys[pygame.K_a]:
            self.player.turn()
        if self.keys[pygame.K_RIGHT] or self.keys[pygame.K_d]:
            self.player.turn(False)
        if self.keys[pygame.K_UP] or self.keys[pygame.K_w]:
            self.player.move()
        if self.keys[pygame.K_DOWN] or self.keys[pygame.K_s]:
            self.player.move(-1)
        if self.keys[pygame.K_q]:
            self.player.move(strafe=True)
        if self.keys[pygame.K_e]:
            self.player.move(-1, True)
        if self.keys[pygame.K_SPACE]:
            self.player.jump()
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
    renderer = Renderer(screen, player, "texture1", "texture2")
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
