# -*- coding: utf-8 -*-
"""
A terminal based ray-casting engine.

'esc' to exit
't' to turn off textures

IMPORTANT:
Make sure the pygame window is focused for input events to be received.

Depending on your terminal font, Renderer.ascii_map may need to be adjusted.

Values stored in textures should range from 0-9.  Values below 5 are
substractive and above 5 are additive.
"""
import types
import curses
import numpy as np
import pygame

GAME = types.SimpleNamespace(running=True, keys=[False]*324, textures_on=True)

class Player:
    def __init__(self, pos=np.array([5., 5.]), angle=np.array([1., 0.]),\
                 plane=np.array([0., 1.])):
        self.pos = pos
        self.angle = angle
        self.field_of_view = .3 #Somewhere between 0 and 1 is reasonable
        self.plane = self.field_of_view * plane
        self.speed = .03
        self.rotate_speed = .008
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

    def turn(self, left=True):
        self.angle = self.angle @ (self.left if left else self.right)
        self.plane = self.plane @ (self.left if left else self.right)

    def move(self, forward=1, strafe=False):
        next_step = (self.pos + forward * self.angle * self.speed @ self.perp)\
                    if strafe else\
                    (self.pos + forward * self.angle * self.speed)
        if not GAME.world_map[tuple(next_step.astype(int))]:
            self.pos = next_step
###Unvectorized version below, but allows sliding on walls.
#        def next_pos(coord, direction):
#            return coord + forward * direction * self.speed
#        next_x_step = next_pos(self.pos[0], self.angle[1]) if strafe else\
#                      next_pos(self.pos[0], self.angle[0])
#        next_y_step = next_pos(self.pos[1], -self.angle[0]) if strafe else\
#                      next_pos(self.pos[1], self.angle[1])
#        if not GAME.world_map[int(next_x_step)][int(self.pos[1])]:
#            self.pos[0] = next_x_step
#        if not GAME.world_map[int(self.pos[0])][int(next_y_step)]:
#            self.pos[1] = next_y_step

class Renderer:
    def __init__(self, screen, player):
        self.screen = screen
        self.height, self.width = screen.getmaxyx()
        self.player = player
        self.buffer = np.full((self.height, self.width), " ", dtype=str)
        self.ascii_map = dict(enumerate(list(" .',:;cxlokXdO0KN")))
        self.shades = len(self.ascii_map)
        self.max_range = 60 #Controls how far rays are cast.
        self.wall_height = 1.5
        self.wall_y = 1.8 #Wall vertical placement

    def cast_ray(self, column):
        ray_angle = self.player.angle +\
                    self.player.plane * (column / self.height - 1)
        map_pos = self.player.pos.astype(int)

        with np.errstate(divide="ignore"):
            delta = abs(1 / ray_angle)

        def step_side(ray_dir, ray, map_, delta):
            if ray_dir < 0:
                return -1, (ray - map_) * delta
            return 1, (map_ + 1 - ray) * delta

        step_x, side_x_dis = step_side(ray_angle[0], self.player.pos[0],\
                                       map_pos[0], delta[0])
        step_y, side_y_dis = step_side(ray_angle[1], self.player.pos[1],\
                                       map_pos[1], delta[1])

        #Distance to wall
        for i in range(self.max_range):
            if side_x_dis < side_y_dis:
                side_x_dis += delta[0]
                map_pos[0] += step_x
                side = True
            else:
                side_y_dis += delta[1]
                map_pos[1] += step_y
                side = False
            if GAME.world_map[map_pos[0]][map_pos[1]]:
                break
            if i == self.max_range - 1:
                return
        #Avoiding euclidean distance, to avoid fish-eye effect.
        if side:
            wall_dis = (map_pos[0] - self.player.pos[0] + (1 - step_x) / 2)\
                       / ray_angle[0]
        else:
            wall_dis = (map_pos[1] - self.player.pos[1] + (1 - step_y) / 2)\
                       / ray_angle[1]

        try:
            line_height = int(self.height / wall_dis)
        except ZeroDivisionError:
            line_height = float("inf")

        #Casting is done, drawing starts
        line_start = int((-line_height * self.wall_height + self.height) /\
                         self.wall_y)
        line_start = np.clip(line_start, 0, None)
        line_end = int((line_height * self.wall_height + self.height) /\
                       self.wall_y)
        line_end = np.clip(line_end, None, self.height)
        line_height = line_end - line_start
        #Shading
        shade = int(np.clip(wall_dis, 0, 20))
        shade = (20 - shade) // 2 + (6 if side else 4) #One side is brighter
        #Write column to a temporary buffer
        shade_buffer = [shade] * line_height

        #Texturing
        if GAME.textures_on:
            texture_num = GAME.world_map[map_pos[0]][map_pos[1]] - 1
            texture_width, texture_height = GAME.textures[texture_num].shape
            if side:
                wall_x = self.player.pos[1] + wall_dis * ray_angle[1]
            else:
                wall_x = self.player.pos[0] + wall_dis * ray_angle[0]
            wall_x -= np.floor(wall_x)
            tex_x = int(wall_x * texture_width)
            if (side and ray_angle[0] > 0) or (not side and ray_angle[1] < 0):
                tex_x = texture_width - tex_x - 1
            #Add or subtract texture values to shade values
            for i, val in enumerate(shade_buffer):
                tex_y = int(i / line_height * texture_height)
                shade_buffer[i] =\
                    np.clip(GAME.textures[texture_num][tex_x][tex_y] +val - 5,\
                            0, self.shades - 1)

        #Convert shade values to ascii and write to screen buffer
        column_buffer = [self.ascii_map[val] for val in shade_buffer]
        column_buffer = np.array(column_buffer, dtype=str)

        self.buffer[line_start:line_end, column] = column_buffer

    def update(self):
        #Clear buffer
        self.buffer = np.full((self.height, self.width), " ", dtype=str)
        #Draw floor
        self.buffer[self.height // 2 + 1:, :] = self.ascii_map[1]
        #Draw Columns
        for column in range(self.width-1):
            self.cast_ray(column)

    def render(self):
        for row_num, row in enumerate(self.buffer):
            self.screen.addstr(row_num, 0, ''.join(row[:-1]))
        self.screen.refresh()

def load_map(map_name):
    with open(map_name+".txt", 'r') as a_map:
        world_map = [[int(char) for char in row]\
                      for row in a_map.read().splitlines()]

    return np.array(world_map).T

def load_textures(*texture_names):
    textures = []
    for name in texture_names:
        with open(name+".txt", 'r') as texture:
            pre_load = [[int(char) for char in row]\
                        for row in texture.read().splitlines()]
            textures.append(np.array(pre_load).T)
    return textures

def user_input():
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                GAME.running = False
            elif event.key == pygame.K_t:
                GAME.textures_on = not GAME.textures_on
            GAME.keys[event.key] = True
        elif event.type == pygame.KEYUP:
            GAME.keys[event.key] = False

def move(player):
    if GAME.keys[pygame.K_LEFT] or GAME.keys[pygame.K_a]:
        player.turn()
    if GAME.keys[pygame.K_RIGHT] or GAME.keys[pygame.K_d]:
        player.turn(False)
    if GAME.keys[pygame.K_UP] or GAME.keys[pygame.K_w]:
        player.move()
    if GAME.keys[pygame.K_DOWN] or GAME.keys[pygame.K_s]:
        player.move(-1)
    if GAME.keys[pygame.K_q]:
        player.move(strafe=True)
    if GAME.keys[pygame.K_e]:
        player.move(-1, True)

def main(screen):
    init_curses(screen)
    init_pygame()
    clock = pygame.time.Clock()
    GAME.world_map = load_map("map1")
    GAME.textures = load_textures("texture1","texture2")
    player = Player()
    renderer = Renderer(screen, player)
    while GAME.running:
        renderer.update()
        renderer.render()
        user_input()
        move(player)
    clock.tick(40)
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
