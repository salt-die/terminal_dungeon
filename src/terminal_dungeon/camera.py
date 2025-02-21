"""The raycaster's camera."""

from __future__ import annotations

__all__ = ["Camera"]

import numpy as np
from numpy.typing import NDArray


def rotation_matrix(theta: float) -> NDArray[np.float64]:
    """Return a 2-D rotation matrix from a given angle.

    Parameters
    ----------
    theta : float
        Angle in radians.

    Returns
    -------
    numpy.ndarray
        2-D rotation matrix.
    """
    x = np.cos(theta)
    y = np.sin(theta)
    return np.array([[x, y], [-y, x]], np.float64)


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
        Field of view of camera. The field of view is a float
            between 0 and 1.

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

        if fov > 1.0:
            fov = 1.0
        elif fov < 0.0:
            fov = 0.0

        self._plane: NDArray[np.float64] = np.empty((2, 2), np.float64)
        """Plane of camera."""

        self._build_plane(theta, fov)

    def _build_plane(self, theta: float, fov: float) -> None:
        """Build the plane of the camera.

        Parameters
        ----------
        theta : float
            Direction of camera in radians.
        fov : float
            Field of view of camera. The field of view is a float
            between 0 and 1.
        """
        initial_plane = np.array([[1.001, 0.001], [0.0, fov]], np.float64)
        self._plane = initial_plane @ rotation_matrix(theta)

    @property
    def theta(self) -> float:
        """Direction of camera in radians.

        Returns
        -------
        float
            Direction of camera in radians.
        """
        x2, x1 = self._plane[0]
        return np.arctan2(x1, x2)

    @theta.setter
    def theta(self, theta: float) -> None:
        self._build_plane(theta, self.fov)

    @property
    def fov(self) -> float:
        """Field of view of camera.

        Returns
        -------
        float
            Field of view of camera.
        """
        return np.linalg.norm(self._plane[1]).item()

    @fov.setter
    def fov(self, fov: float) -> None:
        self._build_plane(self.theta, fov)

    def rotate(self, theta: float) -> None:
        """Rotate camera `theta` radians.

        Parameters
        ----------
        theta : float
            Angle in radians.
        """
        self._plane = self._plane @ rotation_matrix(theta)
