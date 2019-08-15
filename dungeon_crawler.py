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
        self.right = np.array([[np.cos(self.rotate_speed),\
                                np.sin(self.rotate_speed)],\
                               [-np.sin(self.rotate_speed),\
                                np.cos(self.rotate_speed)]])
    
        self.left = np.array([[np.cos(-self.rotate_speed),\
                               np.sin(-self.rotate_speed)],\
                              [-np.sin(-self.rotate_speed),\
                                np.cos(-self.rotate_speed)]])

    def turn(self, left):
        self.x_dir, self.y_dir = np.array([self.x_dir, self.y_dir]) @\
                                 (self.left if left else self.right)
        self.x_plane, self.y_plane = np.array([self.x_plane, self.y_plane]) @\
                                     (self.left if left else self.right)

        
        
        
GAME = types.SimpleNamespace(mouse_sensitivity=1., running=True,\
                             texture_width=29, texture_height=21)

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

def draw_terminal_out(terminal, player):
    ydim, xdim = terminal.getmaxyx() #Get current terminal size.
    terminal_out = np.full((ydim, xdim), " ", dtype=str) #our screen buffer
    terminal_out[ydim//2:, :] = ASCII_MAP[1] #Draw floor
    #Draw walls
    for column in range(xdim):
        camera = column / ydim - 1.0
        ray_x = player.x
        ray_y = player.y
        ray_x_dir = player.x_dir + player.x_plane * camera
        ray_y_dir = player.y_dir + player.y_plane * camera
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
            line_height = int(xdim / (wall_dis))
        except ZeroDivisionError:
            line_height = float("inf")
        line_start = -line_height // 2 + ydim // 2
        line_start = np.clip(line_start, 0, None)
        line_end = line_height // 2 + ydim // 2
        line_end = np.clip(line_end, None, xdim - 1)
        #Shading
        shade = int(np.clip(wall_dis, 0, 20))
        shade = (20 - shade) // 2

        #Draw a column
        terminal_out[line_start:line_end, column] = ASCII_MAP[shade + 6]\
                                             if side else ASCII_MAP[shade + 4]

        #Texturing
        texture_num = GAME.world_map[map_x][map_y] - 1
        if side:
            wall_x = player.y + wall_dis * ray_y_dir
        else:
            wall_x = player.x + wall_dis * ray_x_dir
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
                terminal_out[np.clip(char, None, ydim - 1)][column] = " "

    terminal_out[5, 2:9] = np.array(list(f'{xdim:03},{ydim:03}')) #for testing
    terminal_out[7, 2:9] = np.array(list(f'{int(player.x):03},{int(player.y):03}'))
    #print to terminal
    for row_num, row in enumerate(terminal_out):
        terminal.addstr(row_num, 0, ''.join(row[:-1]))
    terminal.refresh()

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

def main(terminal):
    init_curses(terminal)
    init_pygame()
    clock = pygame.time.Clock()
    GAME.world_map = load_map("map1")
    GAME.textures = load_textures("texture1",)
    player = Player()
    while GAME.running:
        draw_terminal_out(terminal, player)
        user_input()
        move(player)
    clock.tick(40)
    pygame.quit()

def init_pygame():
    pygame.init()
    pygame.display.set_mode((305, 2))
    pygame.display.set_caption('Focus this window to move.')

def init_curses(terminal):
    curses.noecho()
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    terminal.attron(curses.color_pair(1))
    terminal.clear()

if __name__ == "__main__":
    curses.wrapper(main)
