# -*- coding: utf-8 -*-
"""
This will draw the player's current view and display it.
"""
import types
import numpy as np
import pygame
import curses

player = types.SimpleNamespace(pos=np.array([0,0], dtype=float),\
                               vel=np.array([0,0], dtype=float), max_vel = 5,\
                               direction=np.array([0,0], dtype=float),\
                               rotate_vel = 1,\
                               plane=np.array([0,0]), dtype=float)

ASCII_MAP = dict(enumerate([' ', '.', "'", ',', ':', ';', 'c', 'l', 'x', 'o',
                            'k', 'X', 'd', 'O', '0', 'K', 'N']))

keys = [False] * 324

worldMap = np.full((100, 100), " ", dtype=str)

rotate_left = np.array([[np.cos(-player.rotate_vel),\
                         np.sin(-player.rotate_vel)],\
                        [-np.sin(-player.rotate_vel),\
                         np.cos(-player.rotate_vel)]])

rotate_right = np.array([[np.cos(player.rotate_vel),\
                          np.sin(player.rotate_vel)],\
                         [-np.sin(player.rotate_vel),\
                          np.cos(player.rotate_vel)]])

def draw_screen():
    pass

def user_input():
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            keys[event.key] = True
        elif event.type == pygame.KEYUP:
            keys[event.key] = False

    if keys[pygame.K_ESCAPE]:
        return False

    if keys[pygame.K_LEFT]:
        player.direction = player.direction @ rotate_left
        player.plane = player.plane @ rotate_left

    if keys[pygame.K_RIGHT]:
        player.direction = player.direction @ rotate_right
        player.plane = player.direction @ rotate_right

    if keys[pygame.K_UP]:
        player.vel += 1
        magnitude = np.linalg.norm(player.vel)
        if magnitude > player.max_vel:
            player.vel *= player.max_vel / magnitude
        if not worldMap[(player.pos + player.vel).astype(int)]:
            player.position += player.vel

    if keys[pygame.K_DOWN]:
        player.vel -= 1
        magnitude = np.linalg.norm(player.vel)
        if magnitude > player.max_vel:
            player.vel *= player.max_vel / magnitude
        if not worldMap[(player.pos - player.vel).astype(int)]:
            player.position -= player.vel

def main(stdscreen):
    pygame.init()
    init_curses(stdscreen)
    clock = pygame.time.Clock() #For limiting fps
    running = True
    while running:
        screen = np.full(stdscreen.getmaxyx(), " ", dtype=str) #set screen dim
        draw_screen()
        clock.tick(40)
        running = user_input()
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
