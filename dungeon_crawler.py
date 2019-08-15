# -*- coding: utf-8 -*-
"""
This will draw the player's current view and display it.
"""
import types
import pygame
import curses
import numpy as np

game = types.SimpleNamespace(mouse_sensitivity=1., running=True)

keys=[False]*324

ASCII_MAP = dict(enumerate([' ', '.', "'", ',', ':', ';', 'c', 'l', 'x', 'o',
                            'k', 'X', 'd', 'O', '0', 'K', 'N']))

player = types.SimpleNamespace(rotation=0.008, speed=0.03, x_pos=5.0,\
                               y_pos=5.0, x_dir=1.0, y_dir = 0.0,\
                               x_plane=0.0, y_plane=0.5)

right_rotate = (np.cos(player.rotation), np.sin(player.rotation))
left_rotate = (np.cos(-player.rotation), np.sin(-player.rotation))

def load_map(map_name):
    with open(map_name+".txt", 'r') as file:
        world_map = [[int(char) for char in row]\
                      for row in file.read().splitlines()]
    return world_map

def close():
    pygame.display.quit()
    pygame.quit()

def draw_terminal_out(terminal):
    ydim, xdim = terminal.getmaxyx() #Get current terminal size.
    terminal_out = np.full((ydim, xdim), " ", dtype=str)
    terminal_out[ydim//2:,:] = ASCII_MAP[1] #Draw floor
    #Draw walls
    for column in range(xdim):
        camera = column / ydim - 1.0
        ray_x = player.x_pos
        ray_y = player.y_pos
        ray_x_dir = player.x_dir + player.x_plane * camera
        ray_y_dir = player.y_dir + player.y_plane * camera + .0000000000001
        map_x = int(ray_x)
        map_y = int(ray_y)
        delta_x = np.sqrt(1.0 + ray_y_dir**2 / ray_x_dir**2)
        delta_y = np.sqrt(1.0 + ray_x_dir**2 / ray_y_dir**2)
        if ray_x_dir < 0:
            step_x = -1
            side_x_dis = (ray_x - map_x) * delta_x
        else:
            step_x = 1
            side_x_dis = (map_x + 1.0 - ray_x) * delta_x
        if (ray_y_dir < 0):
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
                side = 0
            else:
                side_y_dis += delta_y
                map_y += step_y
                side = 1
            if game.world_map[map_x][map_y]:
                hit = True

        #Fish-eye correction
        if not side:
            wall_dis = abs((map_x - ray_x + (1 - step_x) / 2) / ray_x_dir)
        else:
            wall_dis = abs((map_y - ray_y + (1 - step_y) / 2) / ray_y_dir)

        line_height = abs(int(xdim / (wall_dis+.0000001)))
        line_start = -line_height / 2 + ydim / 2
        line_start = int(np.clip(line_start, 0, None))
        line_end = line_height / 2 + ydim / 2
        line_end = int(np.clip(line_end, None, xdim - 1))
        #Shading
        shade = int(np.clip(wall_dis, 0, 11))
        shade = 11 - shade
        #Draw a column
        terminal_out[line_start:line_end, column] = ASCII_MAP[shade + 4]\
                                     if side == 1 else ASCII_MAP[shade + 5]
    terminal_out[5,2:9] = np.array(list(f'{xdim:03},{ydim:03}')) #for testing
    terminal_out[7,2:9] = np.array(list(f'{map_x:03},{map_y:03}'))
    #print to terminal_out
    for row_num, row in enumerate(terminal_out):
        terminal.addstr(row_num, 0, ''.join(row[:-1]))
    terminal.refresh()

def user_input():
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                game.running = False
            keys[event.key] = True
        elif event.type == pygame.KEYUP:
            keys[event.key] = False

    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        old_x_dir = player.x_dir
        player.x_dir = player.x_dir * left_rotate[0] -\
                       player.y_dir * left_rotate[1]
        player.y_dir = old_x_dir * left_rotate[1] + \
                       player.y_dir * left_rotate[0]
        old_x_plane = player.x_plane
        player.x_plane = player.x_plane * left_rotate[0] -\
                         player.y_plane * left_rotate[1]
        player.y_plane = old_x_plane * left_rotate[1] +\
                         player.y_plane * left_rotate[0]

    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        old_x_dir = player.x_dir
        player.x_dir = player.x_dir * right_rotate[0] -\
                       player.y_dir * right_rotate[1]
        player.y_dir = old_x_dir * right_rotate[1] + \
                       player.y_dir * right_rotate[0]
        old_x_plane = player.x_plane
        player.x_plane = player.x_plane * right_rotate[0] - \
                         player.y_plane * right_rotate[1]
        player.y_plane = old_x_plane * right_rotate[1] +\
                         player.y_plane * right_rotate[0]

    if keys[pygame.K_UP] or keys[pygame.K_w]:
        if not game.world_map[int(player.x_pos +\
                                  player.x_dir *\
                                  player.speed)][int(player.y_pos)]:
            player.x_pos += player.x_dir * player.speed
        if not game.world_map[int(player.x_pos)][int(player.y_pos +\
                                                 player.y_dir *\
                                                 player.speed)]:
            player.y_pos += player.y_dir * player.speed

    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        if not game.world_map[int(player.x_pos -\
                                  player.x_dir *\
                                  player.speed)][int(player.y_pos)]:
            player.x_pos -= player.x_dir * player.speed
        if not game.world_map[int(player.x_pos)][int(player.y_pos -\
                                                 player.y_dir *\
                                                 player.speed)]:
            player.y_pos -= player.y_dir * player.speed

    if keys[pygame.K_q]:
        perp_x_dir = player.y_dir
        perp_y_dir = -player.x_dir
        if not game.world_map[int(player.x_pos +\
                                  perp_x_dir *\
                                  player.speed)][int(player.y_pos)]:
            player.x_pos += perp_x_dir * player.speed
        if not game.world_map[int(player.x_pos)][int(player.y_pos +\
                                                 perp_y_dir *\
                                                 player.speed)]:
            player.y_pos += perp_y_dir * player.speed

    if keys[pygame.K_e]:
        perp_x_dir = player.y_dir
        perp_y_dir = -player.x_dir
        if not game.world_map[int(player.x_pos -\
                                  perp_x_dir *\
                                  player.speed)][int(player.y_pos)]:
            player.x_pos -= perp_x_dir * player.speed
        if not game.world_map[int(player.x_pos)][int(player.y_pos -\
                                                 perp_y_dir *\
                                                 player.speed)]:
            player.y_pos -= perp_y_dir * player.speed

def main(terminal):
    init_curses(terminal)
    clock = pygame.time.Clock()
    game.world_map = load_map("map1")
    while game.running:
        draw_terminal_out(terminal)
        user_input()
    clock.tick(40)
    pygame.quit()

def init_curses(terminal):
    curses.noecho()
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    terminal.attron(curses.color_pair(1))
    terminal.clear()

if __name__ == "__main__":
    pygame.init()
    pygame.display.set_mode((35,2))
    curses.wrapper(main)
