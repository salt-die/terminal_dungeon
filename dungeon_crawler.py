# -*- coding: utf-8 -*-
"""
A terminal based ray-casting engine.

Make sure the pygame window is focused for input events to be received.
"""
import types
import pygame
import curses
import numpy as np

class Player:
    def __init__(self, x_pos=5., y_pos=5., x_dir=1., y_dir=0.,\
                 x_plane=0., y_plane=.3):
        self.x = x_pos
        self.y = y_pos
        self.x_dir = x_dir
        self.y_dir = y_dir
        self.x_plane = x_plane
        self.y_plane = y_plane
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

    def turn(self, left=True):
        self.x_dir, self.y_dir = np.array([self.x_dir, self.y_dir]) @\
                                 (self.left if left else self.right)
        self.x_plane, self.y_plane = np.array([self.x_plane, self.y_plane]) @\
                                     (self.left if left else self.right)


class Renderer:
    def __init__(self, screen, player):
        self.screen = screen
        self.height, self.width = screen.getmaxyx()
        self.player = player
        self.buffer = np.full((self.height, self.width), " ", dtype=str)
        self.ascii_map = dict(enumerate(list(" .',:;clxokXdO0KN")))
        self.shades = len(self.ascii_map)
        self.max_range = 30
        self.wall_ratio = 1/2 #Height of walls, between 0 and 1
    
    def cast_ray(self, column):
        camera = column / self.height - 1.0
        ray_x = self.player.x
        ray_y = self.player.y
        ray_x_dir = self.player.x_dir + self.player.x_plane * camera
        ray_y_dir = self.player.y_dir + self.player.y_plane * camera
        map_x = int(ray_x)
        map_y = int(ray_y)
        try:
            delta_x = abs(1/ray_x_dir)
        except ZeroDivisionError:
            delta_x = float("inf")
        try:
            delta_y = abs(1/ray_y_dir)
        except ZeroDivisionError:
            delta_y = float("inf")
        if ray_x_dir < 0:
            step_x = -1
            side_x_dis = (ray_x - map_x) * delta_x
        else:
            step_x = 1
            side_x_dis = (map_x + 1.0 - ray_x) * delta_x
        if ray_y_dir < 0:
            step_y = -1
            side_y_dis = (ray_y - map_y) * delta_y
        else:
            step_y = 1
            side_y_dis = (map_y + 1.0 - ray_y) * delta_y
        #Distance to wall
        hit = False
        while not hit:
            if side_x_dis < side_y_dis:
                side_x_dis += delta_x
                map_x += step_x
                side = True
            else:
                side_y_dis += delta_y
                map_y += step_y
                side = False
            if GAME.world_map[map_x][map_y]:
                hit = True

        #Avoiding euclidean distance, to avoid fish-eye effect.
        if side:
            wall_dis = (map_x - ray_x + (1 - step_x) / 2) / ray_x_dir
        else:
            wall_dis = (map_y - ray_y + (1 - step_y) / 2) / ray_y_dir
        try:
            line_height = int(self.height / wall_dis)
        except ZeroDivisionError:
            line_height = float("inf")
        WALL_SCALE , WALL_Y = 2, 1.8
        line_start = int((-line_height * WALL_SCALE + self.height) / WALL_Y)
        line_start = np.clip(line_start, 0, None)
        line_end = int((line_height / WALL_SCALE + self.height) / WALL_Y)
        line_end = np.clip(line_end, None, self.height - 1)
        #Shading
        shade = int(np.clip(wall_dis, 0, 20))
        shade = (20 - shade) // 2 + (6 if side else 4)

        #Draw a column
        self.buffer[line_start:line_end, column] = ASCII_MAP[shade]

        #Texturing
        texture_num = GAME.world_map[map_x][map_y] - 1
        if side:
            wall_x = self.player.y + wall_dis * ray_y_dir
        else:
            wall_x = self.player.x + wall_dis * ray_x_dir
        wall_x -= np.floor(wall_x)
        tex_x = int(wall_x * GAME.texture_width)
        if (side and ray_x_dir > 0) or (not side and ray_y_dir < 0):
            tex_x = GAME.texture_width - tex_x - 1
        #Replace non-" " characters with " " according to texture
        for char in range(line_start, line_end):
            tex_y = int((char - line_start) / (line_end - line_start) *\
                        GAME.texture_height)
            if not GAME.textures[texture_num][tex_x][tex_y]:
                #can't figure out why char keeps going out of bounds
                #hence the numpy clip
                self.buffer[np.clip(char, None, self.height - 1)][column] = " "
    
    def update(self):
        #Clear buffer
        self.buffer = np.full((self.height, self.width), " ", dtype=str)
        #Draw floor
        self.buffer[self.height // 2 + 1:, :] = ASCII_MAP[1] #Draw floor
        for column in range(self.width-1):
            self.cast_ray(column)
    
    def render(self):
        #print to terminal
        for row_num, row in enumerate(self.buffer):
            self.screen.addstr(row_num, 0, ''.join(row[:-1]))
        self.screen.refresh()

GAME = types.SimpleNamespace(running=True, texture_width=29, texture_height=21)

KEYS = [False]*324

ASCII_MAP = dict(enumerate(list(" .',:;clxokXdO0KN")))

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

def close():
    pygame.display.quit()
    pygame.quit()

def user_input():
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                GAME.running = False
            KEYS[event.key] = True
        elif event.type == pygame.KEYUP:
            KEYS[event.key] = False

def move(player):
    if KEYS[pygame.K_LEFT] or KEYS[pygame.K_a]:
        player.turn()

    if KEYS[pygame.K_RIGHT] or KEYS[pygame.K_d]:
        player.turn(False)

    if KEYS[pygame.K_UP] or KEYS[pygame.K_w]:
        if not GAME.world_map[int(player.x +\
                                  player.x_dir *\
                                  player.speed)][int(player.y)]:
            player.x += player.x_dir * player.speed
        if not GAME.world_map[int(player.x)][int(player.y +\
                                                 player.y_dir *\
                                                 player.speed)]:
            player.y += player.y_dir * player.speed

    if KEYS[pygame.K_DOWN] or KEYS[pygame.K_s]:
        if not GAME.world_map[int(player.x -\
                                  player.x_dir *\
                                  player.speed)][int(player.y)]:
            player.x -= player.x_dir * player.speed
        if not GAME.world_map[int(player.x)][int(player.y -\
                                                 player.y_dir *\
                                                 player.speed)]:
            player.y -= player.y_dir * player.speed

    if KEYS[pygame.K_q]:
        perp_x_dir = player.y_dir
        perp_y_dir = -player.x_dir
        if not GAME.world_map[int(player.x +\
                                  perp_x_dir *\
                                  player.speed)][int(player.y)]:
            player.x += perp_x_dir * player.speed
        if not GAME.world_map[int(player.x)][int(player.y +\
                                                 perp_y_dir *\
                                                 player.speed)]:
            player.y += perp_y_dir * player.speed

    if KEYS[pygame.K_e]:
        perp_x_dir = player.y_dir
        perp_y_dir = -player.x_dir
        if not GAME.world_map[int(player.x -\
                                  perp_x_dir *\
                                  player.speed)][int(player.y)]:
            player.x -= perp_x_dir * player.speed
        if not GAME.world_map[int(player.x)][int(player.y -\
                                                 perp_y_dir *\
                                                 player.speed)]:
            player.y -= perp_y_dir * player.speed

def main(screen):
    init_curses(screen)
    init_pygame()
    clock = pygame.time.Clock()
    GAME.world_map = load_map("map1")
    GAME.textures = load_textures("texture1",)
    player = Player()
    renderer = Renderer(screen, player)
    while GAME.running:
        #draw_terminal_out(screen, player)
        renderer.update()
        renderer.render()
        user_input()
        move(player)
    clock.tick(40)
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
