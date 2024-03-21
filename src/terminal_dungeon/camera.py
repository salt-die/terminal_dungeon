"""The raycaster's camera."""

import numpy as np
from numpy.typing import NDArray


class Camera:
    """A raycaster camera.

    Parameters
    ----------
    pos : tuple[float, float], default: (0.0, 0.0)
        Position of camera on the map.
    theta : float, default: 0.0
        Direction of camera in radians.
    fov : float, default: 0.66
        Field of view of camera.

    Attributes
    ----------
    pos : tuple[float, float]
        Position of camera on the map.
    theta : float
        Direction of camera in radians.
    fov : float
        Field of view of camera.

    Methods
    -------
    rotation_matrix(theta)
        Return a 2-D rotation matrix from a given angle.
    rotate(theta)
        Rotate camera `theta` radians in-place.
    """

    def __init__(
        self,
        pos: tuple[float, float] = (0.0, 0.0),
        theta: float = 0.0,
        fov: float = 0.66,
    ) -> None:
        self.pos = pos
        self._build_plane(theta, fov)
        self._plane: NDArray[np.float32]
        """Plane of camera."""

    @staticmethod
    def rotation_matrix(theta: float) -> NDArray[np.float32]:
        """Return a 2-D rotation matrix from a given angle."""
        x = np.cos(theta)
        y = np.sin(theta)
        return np.array([[x, y], [-y, x]], float)

    def _build_plane(self, theta: float, fov: float) -> None:
        initial_plane = np.array([[1.001, 0.001], [0.0, fov]], float)
        self._plane = initial_plane @ self.rotation_matrix(theta)

    @property
    def theta(self) -> float:
        """Direction of camera in radians."""
        x2, x1 = self._plane[0]
        return np.arctan2(x1, x2)

    @theta.setter
    def theta(self, theta: float) -> None:
        self._build_plane(theta, self.fov)

    @property
    def fov(self) -> float:
        """Field of view of camera."""
        return (self._plane[1] ** 2).sum() ** 0.5

    @fov.setter
    def fov(self, fov: float) -> None:
        self._build_plane(self.theta, fov)

    def rotate(self, theta: float) -> None:
        """Rotate camera `theta` radians."""
        self._plane = self._plane @ self.rotation_matrix(theta)
