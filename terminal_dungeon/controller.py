import signal
import curses
from pynput import keyboard
from pynput.keyboard import Key, KeyCode


# Key Bindings
JUMP = Key.space
TOGGLE_TEXTURE = KeyCode(char='t')
QUIT = Key.esc
FORWARD_1 = Key.up
FORWARD_2 = KeyCode(char='w')
BACKWARD_1 = Key.down
BACKWARD_2 = KeyCode(char='s')
LEFT_1 = Key.left
LEFT_2 = KeyCode(char='a')
RIGHT_1 = Key.right
RIGHT_2 = KeyCode(char='d')
STRAFE_LEFT = KeyCode(char='q')
STRAFE_RIGHT = KeyCode(char='e')


class KeyDict(dict):
    """Dictionary that ignores certain movement inputs when player is jumping.
    """
    _ignored_inputs = { FORWARD_1, FORWARD_2, BACKWARD_1, BACKWARD_2, STRAFE_LEFT, STRAFE_RIGHT }

    def __init__(self, player):
        self._player = player
        self._jump_keys = dict.fromkeys(self._ignored_inputs, False)
        super().__init__()

    def __getitem__(self, key):
        if self._player.is_jumping and key in self._ignored_inputs:
            return self._jump_keys[key]
        return super().__getitem__(key)

    def freeze(self):
        self._jump_keys = {key: super(KeyDict, self).__getitem__(key) for key in self._ignored_inputs}

    def __missing__(self, key):
        self[key] = False
        return False


class Controller:
    """Controller class handles user input and updates all other objects.
    """
    running = True
    resized = False

    def __init__(self, renderer):
        self.renderer = renderer
        self.player = renderer.player
        self.keys = KeyDict(self.player)

        try: # Fails on windows
            signal.signal(signal.SIGWINCH, self.resize) # Our solution to curses resize bug
        except:
            pass

        self.listener = keyboard.Listener(on_press=self.pressed,
                                          on_release=self.released)
        self.listener.start()

    def resize(self, *args):
        self.resized = True

    def user_input(self):
        if self.keys[QUIT]:
            self.running = False
            return
        if self.keys[TOGGLE_TEXTURE]:
            self.renderer.toggle_textures()
            self.keys[TOGGLE_TEXTURE] = False
        self.movement()

    def pressed(self, key):
        self.keys[key] = True

    def released(self, key):
        self.keys[key] = False
        return key != QUIT

    def movement(self):
        keys = self.keys

        left = keys[LEFT_1] or keys[LEFT_2]
        right = keys[RIGHT_1] or keys[RIGHT_2]
        up = keys[FORWARD_1] or keys[FORWARD_2]
        down = keys[BACKWARD_1] or keys[BACKWARD_2]
        strafe_l = keys[STRAFE_LEFT]
        strafe_r = keys[STRAFE_RIGHT]

        if left ^ right:
            self.player.turn(left)
        if up ^ down:
            self.player.move(up - down)
        if strafe_l ^ strafe_r:
            self.player.move(strafe_l - strafe_r, strafe=True)
        if self.keys[JUMP] and self.player.jump():
            self.keys.freeze()

    def start(self):
        while self.running:
            self.update()

    def update(self):
        self.player.update()
        if self.resized or self.renderer.screen.getch() == curses.KEY_RESIZE: # 2nd check for windows
            self.renderer.resize()
            self.resized = False
        self.renderer.update()
        self.user_input()
