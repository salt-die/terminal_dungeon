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
        self.speed = .05
        self.rotate_speed = .03
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
        elif not GAME.world_map[int(next_step[0])][int(self.pos[1])]:
            self.pos[0] = next_step[0]
        elif not GAME.world_map[int(self.pos[0])][int(next_step[1])]:
            self.pos[1] = next_step[1]

class Renderer:
    def __init__(self, screen, player):
        self.screen = screen
        self.height, self.width = screen.getmaxyx()
        self.player = player
        self.buffer = np.full((self.height, self.width), " ", dtype=str)
        self.ascii_map = dict(enumerate(list(' .,:;<+*LtaC4U80dQM@')))
        self.shades = len(self.ascii_map)
        self.max_hops = 60 #Controls how far rays are cast.
        self.wall_height = 1.
        self.wall_y = 2. #Wall vertical placement

    def cast_ray(self, column):
        ray_angle = self.player.angle +\
                    self.player.plane * (column / self.height - 1)
        map_pos = self.player.pos.astype(int)
        with np.errstate(divide="ignore"):
            delta = abs(1 / ray_angle)
        step = np.sign(ray_angle)
        side_dis = step * (map_pos + (step + 1) / 2 - self.player.pos) * delta
        #Distance to wall
        for hops in range(self.max_hops):
            side = 0 if side_dis[0] < side_dis[1] else 1
            side_dis[side] += delta[side]
            map_pos[side] += step[side]
            if GAME.world_map[tuple(map_pos)]:
                break
            if hops == self.max_hops - 1: #No walls in range
                return
        #Avoiding euclidean distance, to avoid fish-eye effect.
        wall_dis = (map_pos[side] - self.player.pos[side] +\
                    (1 - step[side]) / 2) / ray_angle[side]
        return wall_dis, side, map_pos, ray_angle

    def draw_column(self, wall_dis, side, map_pos, ray_angle):
        try:
            line_height = int(self.height / wall_dis)
        except ZeroDivisionError:
            line_height = float("inf")
        if line_height == 0:
            return 0, 0, [] #Draw nothing
        line_start = int((-line_height * self.wall_height + self.height) /\
                         self.wall_y)
        line_start = 0 if line_start < 0 else line_start
        line_end = int((line_height * self.wall_height + self.height) /\
                       self.wall_y)
        line_end = self.height if line_end > self.height else line_end
        line_height = line_end - line_start
        #Shading
        shade = int(15 if wall_dis > 15 else wall_dis)
        shade = 15 - shade + (0 if side else 4) #One side is brighter
        #Write column to a temporary buffer
        shade_buffer = [shade] * line_height

        #Texturing
        if GAME.textures_on:
            tex_num = GAME.world_map[map_pos[0]][map_pos[1]] - 1
            texture_width, texture_height = GAME.textures[tex_num].shape
            wall_x = (self.player.pos[-side + 1] +\
                     wall_dis * ray_angle[-side + 1]) % 1
            tex_x = int(wall_x * texture_width)
            if (not side and ray_angle[0] > 0) or (side and ray_angle[1] < 0):
                tex_x = texture_width - tex_x - 1
            #Add or subtract texture values to shade values
            tex_to_wall_ratio = 1 / line_height * texture_height
            for i, val in enumerate(shade_buffer):
                tex_y = int(i * tex_to_wall_ratio)
                new_shade_val = GAME.textures[tex_num][tex_x][tex_y] - 6 + val
                if new_shade_val < 2:
                    shade_buffer[i] = 2
                elif 0 <= new_shade_val <= self.shades - 1:
                    shade_buffer[i] =  new_shade_val
                else:
                    shade_buffer[i] = self.shades - 1

        #Convert shade values to ascii
        column_buffer = [self.ascii_map[val] for val in shade_buffer]
        column_buffer = np.array(column_buffer, dtype=str)
        return line_start, line_end, column_buffer

    def update(self):
        #Clear buffer
        self.buffer = np.full((self.height, self.width), " ", dtype=str)
        #Draw floor
        self.buffer[self.height // 2:, :] = self.ascii_map[1]
        #Draw Columns
        for column in range(self.width-1):
            ray = self.cast_ray(column)
            if ray:
                start, end, col_buffer = self.draw_column(*ray)
                self.buffer[start:end, column] = col_buffer
        self.render()

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
