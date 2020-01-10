from collections import defaultdict
import signal
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

class Controller():
    """
    Controller class handles user input and updates all other objects.
    """
    running = True
    keys = jumping_keys = defaultdict(bool)
    player_has_jumped = False
    resized = False

    def __init__(self, renderer):
        self.player = renderer.player
        self.renderer = renderer
        signal.signal(signal.SIGWINCH, self.resize) # Our solution to curses resize bug
        self.listener = keyboard.Listener(on_press=self.pressed,
                                          on_release=self.released)
        self.listener.start()

    def resize(self, *args):
        self.resized = True

    def user_input(self):
        if self.keys[Key.esc]:
            self.running = False
            return
        if self.keys[KeyCode(char='t')]:
            self.renderer.textures_on = not self.renderer.textures_on
            self.keys[KeyCode(char='t')] = False
        self.movement()

    def pressed(self, key):
        self.keys[key] = True

    def released(self, key):
        if key == Key.esc:
            return False
        self.keys[key] = False

    def movement(self):
        # We stop accepting move inputs (but turning is ok) in the middle of a
        # jump -- the effect is momentum-like movement while in the air.
        keys = self.jumping_keys if self.player.is_jumping else self.keys
        if self.player_has_jumped:
            self.jumping_keys = self.keys.copy()
            self.player_has_jumped = False

        left = self.keys[Key.left] or self.keys[KeyCode(char='a')]
        right = self.keys[Key.right] or self.keys[KeyCode(char='d')]
        up = keys[Key.up] or keys[KeyCode(char='w')]
        down = keys[Key.down] or keys[KeyCode(char='s')]
        strafe_l = keys[KeyCode(char='q')]
        strafe_r = keys[KeyCode(char='e')]

        if left ^ right:
            self.player.turn(left)
        if up ^ down:
            self.player.move((up - down) * self.player.speed)
        if strafe_l ^ strafe_r:
            self.player.move((strafe_l - strafe_r) * self.player.speed, True)
        if self.keys[Key.space]:
            self.player_has_jumped = True
            self.player.is_jumping = True
            self.keys[Key.space] = False

    def start(self):
        while self.running:
            self.update()

    def update(self):
        self.player.update()
        if self.resized:
            self.renderer.resize()
            self.resized = False
        self.renderer.update()
        self.user_input()