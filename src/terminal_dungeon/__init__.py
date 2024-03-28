"""A raycasting library for your terminal."""

import curses
import platform
import sys

__version__ = "0.1.1"


# Patching windows-curses's wrapper on 3.12 due to a bug.
# More info: https://github.com/zephyrproject-rtos/windows-curses/issues/50
if (
    platform.system() == "Windows"
    and sys.version_info.major == 3
    and sys.version_info.minor >= 12
):

    def _wrapper(func):
        stdscr = None
        try:
            import _curses

            stdscr = _curses.initscr()
            for key, value in _curses.__dict__.items():
                if key.startswith("ACS_") or key in ("LINES", "COLS"):
                    setattr(curses, key, value)

            curses.noecho()
            curses.cbreak()

            try:
                curses.start_color()
            except:  # noqa
                pass

            if stdscr is not None:
                stdscr.keypad(True)
                func(stdscr)
        finally:
            if stdscr is not None:
                stdscr.keypad(False)
            curses.echo()
            curses.nocbreak()
            return curses.endwin()

    curses.wrapper = _wrapper
