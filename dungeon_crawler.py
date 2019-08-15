# -*- coding: utf-8 -*-
"""
A terminal based ray-casting engine.

Make sure the pygame window is focused for input events to be received.
"""
import types
import pygame
import curses
import numpy as np

GAME = types.SimpleNamespace(mouse_sensitivity=1., running=True,\
                             texture_width=29, texture_height=21)

PLAYER = types.SimpleNamespace(rotation=0.008, speed=0.03, x_pos=5.0,\
                               y_pos=5.0, x_dir=1.0, y_dir=0.0,\
                               x_plane=0.0, y_plane=0.3)
KEYS = [False]*324

ASCII_MAP = dict(enumerate([' ', '.', "'", ',', ':', ';', 'c', 'l', 'x', 'o',
                            'k', 'X', 'd', 'O', '0', 'K', 'N']))

RIGHT_ROTATE = (np.cos(PLAYER.rotation), np.sin(PLAYER.rotation))
LEFT_ROTATE = (np.cos(-PLAYER.rotation), np.sin(-PLAYER.rotation))

def load_map(map_name):
    with open(map_name+".txt", 'r') as a_map:
        world_map = [[int(char) for char in row]\
                      for row in a_map.read().splitlines()]

    return np.array(world_map)

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

def draw_terminal_out(terminal):
    ydim, xdim = terminal.getmaxyx() #Get current terminal size.
    terminal_out = np.full((ydim, xdim), " ", dtype=str) #our screen buffer
    terminal_out[ydim//2:, :] = ASCII_MAP[1] #Draw floor
    #Draw walls
    for column in range(xdim):
        camera = column / ydim - 1.0
        ray_x = PLAYER.x_pos
        ray_y = PLAYER.y_pos
        ray_x_dir = PLAYER.x_dir + PLAYER.x_plane * camera
        ray_y_dir = PLAYER.y_dir + PLAYER.y_plane * camera + .0000000000001
        map_x = int(ray_x)
        map_y = int(ray_y)
        delta_x = abs(1/ray_x_dir)
        delta_y = abs(1/ray_y_dir)
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

        line_height = int(xdim / (wall_dis+.0000001))
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
            wall_x = PLAYER.y_pos + wall_dis * ray_y_dir
        else:
            wall_x = PLAYER.x_pos + wall_dis * ray_x_dir
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
    terminal_out[7, 2:9] = np.array(list(f'{int(PLAYER.x_pos):03},{int(PLAYER.y_pos):03}'))
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

def move():
    if KEYS[pygame.K_LEFT] or KEYS[pygame.K_a]:
        old_x_dir = PLAYER.x_dir
        PLAYER.x_dir = PLAYER.x_dir * LEFT_ROTATE[0] -\
                       PLAYER.y_dir * LEFT_ROTATE[1]
        PLAYER.y_dir = old_x_dir * LEFT_ROTATE[1] + \
                       PLAYER.y_dir * LEFT_ROTATE[0]
        old_x_plane = PLAYER.x_plane
        PLAYER.x_plane = PLAYER.x_plane * LEFT_ROTATE[0] -\
                         PLAYER.y_plane * LEFT_ROTATE[1]
        PLAYER.y_plane = old_x_plane * LEFT_ROTATE[1] +\
                         PLAYER.y_plane * LEFT_ROTATE[0]

    if KEYS[pygame.K_RIGHT] or KEYS[pygame.K_d]:
        old_x_dir = PLAYER.x_dir
        PLAYER.x_dir = PLAYER.x_dir * RIGHT_ROTATE[0] -\
                       PLAYER.y_dir * RIGHT_ROTATE[1]
        PLAYER.y_dir = old_x_dir * RIGHT_ROTATE[1] + \
                       PLAYER.y_dir * RIGHT_ROTATE[0]
        old_x_plane = PLAYER.x_plane
        PLAYER.x_plane = PLAYER.x_plane * RIGHT_ROTATE[0] - \
                         PLAYER.y_plane * RIGHT_ROTATE[1]
        PLAYER.y_plane = old_x_plane * RIGHT_ROTATE[1] +\
                         PLAYER.y_plane * RIGHT_ROTATE[0]

    if KEYS[pygame.K_UP] or KEYS[pygame.K_w]:
        if not GAME.world_map[int(PLAYER.x_pos +\
                                  PLAYER.x_dir *\
                                  PLAYER.speed)][int(PLAYER.y_pos)]:
            PLAYER.x_pos += PLAYER.x_dir * PLAYER.speed
        if not GAME.world_map[int(PLAYER.x_pos)][int(PLAYER.y_pos +\
                                                 PLAYER.y_dir *\
                                                 PLAYER.speed)]:
            PLAYER.y_pos += PLAYER.y_dir * PLAYER.speed

    if KEYS[pygame.K_DOWN] or KEYS[pygame.K_s]:
        if not GAME.world_map[int(PLAYER.x_pos -\
                                  PLAYER.x_dir *\
                                  PLAYER.speed)][int(PLAYER.y_pos)]:
            PLAYER.x_pos -= PLAYER.x_dir * PLAYER.speed
        if not GAME.world_map[int(PLAYER.x_pos)][int(PLAYER.y_pos -\
                                                 PLAYER.y_dir *\
                                                 PLAYER.speed)]:
            PLAYER.y_pos -= PLAYER.y_dir * PLAYER.speed

    if KEYS[pygame.K_q]:
        perp_x_dir = PLAYER.y_dir
        perp_y_dir = -PLAYER.x_dir
        if not GAME.world_map[int(PLAYER.x_pos +\
                                  perp_x_dir *\
                                  PLAYER.speed)][int(PLAYER.y_pos)]:
            PLAYER.x_pos += perp_x_dir * PLAYER.speed
        if not GAME.world_map[int(PLAYER.x_pos)][int(PLAYER.y_pos +\
                                                 perp_y_dir *\
                                                 PLAYER.speed)]:
            PLAYER.y_pos += perp_y_dir * PLAYER.speed

    if KEYS[pygame.K_e]:
        perp_x_dir = PLAYER.y_dir
        perp_y_dir = -PLAYER.x_dir
        if not GAME.world_map[int(PLAYER.x_pos -\
                                  perp_x_dir *\
                                  PLAYER.speed)][int(PLAYER.y_pos)]:
            PLAYER.x_pos -= perp_x_dir * PLAYER.speed
        if not GAME.world_map[int(PLAYER.x_pos)][int(PLAYER.y_pos -\
                                                 perp_y_dir *\
                                                 PLAYER.speed)]:
            PLAYER.y_pos -= perp_y_dir * PLAYER.speed

def main(terminal):
    init_curses(terminal)
    init_pygame()
    clock = pygame.time.Clock()
    GAME.world_map = load_map("map1")
    GAME.textures = load_textures("texture1",)
    while GAME.running:
        draw_terminal_out(terminal)
        user_input()
        move()
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
