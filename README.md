# Terminal Dungeon

A Doom-like game engine that renders to ascii and outputs to terminal! From `/terminal_dungeon/` root directory type `python -m terminal_dungeon` to play.

![Terminal Dungeon Preview](preview.gif)

This engine was used to power a maze solving robot during Advent of Code 2019:

![Maze Solver](https://github.com/salt-die/Advent-of-Code/blob/main/visuals_media/maze_solver_2.gif)

(see code here: [AoC Raycaster](https://github.com/salt-die/Advent-of-Code/tree/main/2019/raycaster))


* **'esc'** to exit

* **'t'** to turn off textures

* **'wasdqe'** or arrow-keys to move

* **'space'** to jump
***********
Depending on your terminal font, Renderer.ascii_map may need to be adjusted.

Values stored in wall textures should range from 0-9. 6 is the default wall shade; values below 6 will darken the wall and above 6 will lighten it.
***********
This project wouldn't have been possible without the following valuable resources:

[Lode's Computer Graphics Tutorial](https://lodev.org/cgtutor/raycasting.html)

[PyRay - Python Raycasting Engine](https://github.com/oscr/PyRay)

[pygame-raycasting-experiment](https://github.com/crobertsbmw/pygame-raycasting-experiment/blob/master/raycast.py)
