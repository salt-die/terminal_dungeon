import numpy as np

def rotation_matrix(theta):
    """
    Returns a 2-dimensional rotation array of a given angle.
    """
    return np.array([[np.cos(theta), np.sin(theta)],
                     [-np.sin(theta), np.cos(theta)]])

class Player:
    """
    Player class with methods for moving and updating any effects on the
    player such as falling.
    """
    speed = .1

    rotate_speed = .07

    jump_time = 8
    is_jumping = False
    z = 0.0

    field_of_view = .6  # Somewhere between 0 and 1 is reasonable

    left = rotation_matrix(-rotate_speed)
    right = rotation_matrix(rotate_speed)

    perp = rotation_matrix(3 * np.pi / 2)

    def __init__(self, game_map, pos=np.array([5., 5.]), initial_angle=0):
        self.game_map = game_map
        self.pos = pos
        self.cam = np.array([[1, 0], [0, self.field_of_view]]) @ rotation_matrix(initial_angle)

        # generate z sequence for jumping
        t = np.arange(self.jump_time + 1)
        self.zs = t * (self.jump_time - t) / self.jump_time**2

    def jump(self):
        if self.is_jumping:
            return

        self.is_jumping = True
        self.iter_z = self.z_gen()

    def z_gen(self):
        """
        Set each z value in self.zs to self.z consecutively,
        then set self.is_jumping to False.
        """
        for z in self.zs:
            self.z = z
            yield

        self.is_jumping = False
        yield

    def update(self):
        # We'll have more to do here eventually, e.g., decrement timers on power-ups.
        if self.is_jumping:
            next(self.iter_z)

    def turn(self, left=True):
        self.cam = self.cam @ (self.left if left else self.right)

    def move(self, speed, strafe=False):
        next_step = self.pos + speed * \
                    (self.cam[0] @ self.perp if strafe else self.cam[0])

        # If we can move both coordinates at once, we should
        if not self.game_map[next_step]:
            self.pos = next_step

        # Allows 'sliding' on walls
        elif not self.game_map[next_step[0], self.pos[1]]:
            self.pos[0] = next_step[0]
        elif not self.game_map[self.pos[0], next_step[1]]:
            self.pos[1] = next_step[1]
