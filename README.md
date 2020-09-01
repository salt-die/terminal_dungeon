# Terminal Dungeon

A Doom-like game engine that renders to ascii and outputs to terminal! From `/terminal_dungeon/` root directory type `python -m terminal_dungeon` to play.

![Terminal Dungeon Preview](preview.gif)

This engine was used to power a maze solving robot during Advent of Code 2019:

![Maze Solver](https://github.com/salt-die/Advent-of-Code/blob/master/maze_solver_2.gif)

(see code here: [AoC Raycaster](https://github.com/salt-die/Advent-of-Code/tree/master/raycaster))


* **'esc'** to exit

* **'t'** to turn off textures

* **'wasdqe'** or arrow-keys to move

* **'space'** to jump
***********
Depending on your terminal font, Renderer.ascii_map may need to be adjusted.
If you'd like to make an ascii map more suitable to your terminal's font,
check my Snippets repository for a script that grabs mean brightness of
unicode characters.

Values stored in textures should range from 0-9.  Values below 6 are
subtractive and above 6 are additive.
***********
This project wouldn't have been possible without the following valuable
resources:

[Lode's Computer Graphics Tutorial](https://lodev.org/cgtutor/raycasting.html)

[PyRay - Python Raycasting Engine](https://github.com/oscr/PyRay)

[pygame-raycasting-experiment](https://github.com/crobertsbmw/pygame-raycasting-experiment/blob/master/raycast.py)
