# -*- coding: utf-8 -*-
"""
This will draw the player's current view and display it.
"""
import types
import numpy as np
import pygame
import curses

game = types.SimpleNamespace()

player = types.SimpleNamespace(pos=np.array([3,7], dtype=float),\
                               vel=.0001,\
                               direction=np.array([1,0], dtype=float),\
                               rotate_vel = .1,\
                               plane=np.array([0,.1]), dtype=float)

movement = types.SimpleNamespace(left=False, right=False, up=False, down=False)

ASCII_MAP = dict(enumerate([' ', '.', "'", ',', ':', ';', 'c', 'l', 'x', 'o',
                            'k', 'X', 'd', 'O', '0', 'K', 'N']))

rotate_left = np.array([[np.cos(-player.rotate_vel),\
                         np.sin(-player.rotate_vel)],\
                        [-np.sin(-player.rotate_vel),\
                         np.cos(-player.rotate_vel)]])

rotate_right = np.array([[np.cos(player.rotate_vel),\
                          np.sin(player.rotate_vel)],\
                         [-np.sin(player.rotate_vel),\
                          np.cos(player.rotate_vel)]])

def load_map(map_name):
    with open(map_name+".txt", 'r') as file:
        world_map = np.array([list(row) for row in file.read().splitlines()],\
                              dtype=str)
    return world_map

def draw_screen(stdscreen):
    xdim, ydim = stdscreen.getmaxyx()
    screen = np.full((xdim, ydim), " ", dtype=str) #set screen dim
    #draw floor
    screen[xdim//2:,:] = ASCII_MAP[1]
    #draw walls
    for column in range(ydim):
        field_of_view = .2 * column / xdim - 1
        ray_pos = player.pos
        map_pos = ray_pos.astype(int)
        ray_dir = player.direction + player.plane * field_of_view
        ray_delta = np.linalg.norm(ray_dir) / ray_dir
        step = 2 * np.heaviside(ray_dir, 1) - 1 #np.sign of 0 is 0 -- need -1 or 1
        side_distance = step * (map_pos + (step + 1)/ 2 - ray_pos) *\
                        ray_delta
        hit = 0
        while not hit:
            if side_distance[0] < side_distance[1]:
                side_distance[0] += ray_delta[0]
                map_pos[0] += step[0]
                side = 0
            else:
                side_distance[1] += ray_delta[1]
                map_pos[1] += step[1]
                side = 1
            
            if game.world_map[int(map_pos[0]), int(map_pos[1])]=='1':
                hit = 1
        if side:
            perp_wall_distance = np.abs((map_pos[1] - ray_pos[1] +\
                                         (1 - step[1]) / 2) / ray_dir[1])                
        else:
            perp_wall_distance = np.abs((map_pos[0] - ray_pos[0] +\
                                         (1 - step[0]) / 2) / ray_dir[0])
            
        line_height = np.abs(int(xdim / (perp_wall_distance + .0000001)))
        draw_start = np.clip(-line_height // 2 + xdim // 2, 0, xdim)
        draw_end = np.clip(line_height // 2 + xdim // 2, 0, xdim)
        
        screen[draw_start:draw_end, column] = ASCII_MAP[11]
        screen[5][5] = int(player.pos[0])
        screen[5][6] = ','
        screen[5][7] = int(player.pos[1])
    #print to screen
    for row_num, row in enumerate(screen):
        stdscreen.addstr(row_num, 0, ''.join(row[:-1]))
    stdscreen.refresh()

def user_input(stdscreen):
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_LEFT, pygame.K_a]:
                movement.left = True
            if event.key in [pygame.K_RIGHT, pygame.K_d]:
                movement.right = True
            if event.key in [pygame.K_UP, pygame.K_w]:
                movement.up = True
            if event.key in [pygame.K_DOWN, pygame.K_s]:
                movement.down = True
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key in [pygame.K_LEFT, pygame.K_a]:
                movement.left = False
            if event.key in [pygame.K_RIGHT, pygame.K_d]:
                movement.right = False
            if event.key in [pygame.K_UP, pygame.K_w]:
                movement.up = False
            if event.key in [pygame.K_DOWN, pygame.K_s]:
                movement.down = False

    if movement.left:
        player.direction = player.direction @ rotate_left
        player.plane = player.plane @ rotate_left
    if movement.right:
        player.direction = player.direction @ rotate_right
        player.plane = player.direction @ rotate_right

    if movement.up:
        loc = (player.pos + player.vel * player.direction).astype(int)
        if game.world_map[loc[0]][int(player.pos[1])]=='0':
            player.pos[0] = loc[0]
        if game.world_map[int(player.pos[0])][loc[1]]=='0':
            player.pos[1] = loc[1]

    if movement.down:
        loc = (player.pos - player.vel * player.direction).astype(int)
        if game.world_map[loc[0]][int(player.pos[1])]=='0':
            player.pos[0] = loc[0]
        if game.world_map[int(player.pos[0])][loc[1]]=='0':
            player.pos[1] = loc[1]

    return True

def main(stdscreen):
    pygame.init()
    init_curses(stdscreen)
    pygame.display.set_mode((1,1))
    clock = pygame.time.Clock() #For limiting fps
    game.world_map = load_map("map1")
    while user_input(stdscreen):
        draw_screen(stdscreen)
        clock.tick(40)
    pygame.quit()

def init_curses(stdscreen):
    # Do not echo characters to terminal
    curses.noecho()
    # No input buffer, make stdscreen.getch() nonblocking
    curses.cbreak()
    stdscreen.nodelay(1)
    # Hide cursor
    curses.curs_set(0)
    # Matrix colors :)
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    stdscreen.attron(curses.color_pair(1))
    stdscreen.clear()

if __name__ == "__main__":
    curses.wrapper(main)
