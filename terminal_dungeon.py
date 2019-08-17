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
        self.speed = .03
        self.rotate_speed = .01
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
        self.ascii_map = dict(enumerate(list(" .,:;<+*LtCa4Ud8Q0M@")))
        self.shades = len(self.ascii_map)
        self.max_range = 60 #Controls how far rays are cast.
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

        ###TODO: Vectorize code below======
        #Distance to wall
        for i in range(self.max_range):
            if side_dis[0] < side_dis[1]:
                side_dis[0] += delta[0]
                map_pos[0] += step[0]
                side = True
            else:
                side_dis[1] += delta[1]
                map_pos[1] += step[1]
                side = False
            if GAME.world_map[tuple(map_pos)]:
                break
            if i == self.max_range - 1:
                return
        #Avoiding euclidean distance, to avoid fish-eye effect.
        if side:
            wall_dis = (map_pos[0] - self.player.pos[0] + (1 - step[0]) / 2)\
                       / ray_angle[0]
        else:
            wall_dis = (map_pos[1] - self.player.pos[1] + (1 - step[1]) / 2)\
                       / ray_angle[1]
        ###TODO: Vectorize code above======
        return wall_dis, side, map_pos, ray_angle

    def draw_column(self, wall_dis, side, map_pos, ray_angle):
        try:
            line_height = int(self.height / wall_dis)
        except ZeroDivisionError:
            line_height = float("inf")
        line_start = int((-line_height * self.wall_height + self.height) /\
                         self.wall_y)
        line_start = np.clip(line_start, 0, None)
        line_end = int((line_height * self.wall_height + self.height) /\
                       self.wall_y)
        line_end = np.clip(line_end, None, self.height)
        line_height = line_end - line_start
        #Shading
        shade = int(np.clip(wall_dis, 0, 13))
        shade = 13 - shade + (6 if side else 2) #One side is brighter
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
                    np.clip(2 * GAME.textures[texture_num][tex_x][tex_y] - 12\
                            + val, 2, self.shades - 1)

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
