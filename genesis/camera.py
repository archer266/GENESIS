"""Rendering-only camera math. No simulation, Pygame, RNG or wall-clock imports."""
import math


class Camera:
    MAX_ZOOM = 6.0
    MAX_SCALE = 8.0

    def __init__(self, width, height):
        self.width, self.height = width, height
        self.viewport = (0, 0, width, height)
        self.zoom = 1.0
        self.x, self.y = width / 2, height / 2

    @property
    def base_scale(self):
        return min(self.viewport[2] / self.width, self.viewport[3] / self.height)

    @property
    def scale(self):
        return self.base_scale * self.zoom

    @property
    def max_zoom(self):
        return max(1, min(self.MAX_ZOOM, self.MAX_SCALE / self.base_scale))

    @property
    def left(self):
        return self.x - self.viewport[2] / (2 * self.scale)

    @property
    def top(self):
        return self.y - self.viewport[3] / (2 * self.scale)

    def resize(self, viewport):
        self.viewport = tuple(viewport)
        self.zoom = min(self.zoom, self.max_zoom)
        self.clamp()

    def clamp(self):
        half_w = self.viewport[2] / (2 * self.scale)
        half_h = self.viewport[3] / (2 * self.scale)
        self.x = self.width / 2 if half_w >= self.width / 2 else max(half_w, min(self.width - half_w, self.x))
        self.y = self.height / 2 if half_h >= self.height / 2 else max(half_h, min(self.height - half_h, self.y))

    def fit(self):
        self.zoom = 1.0
        self.x, self.y = self.width / 2, self.height / 2

    def world_to_screen(self, x, y):
        return self.viewport[0] + (x - self.left) * self.scale, self.viewport[1] + (y - self.top) * self.scale

    def screen_to_world(self, x, y):
        return self.left + (x - self.viewport[0]) / self.scale, self.top + (y - self.viewport[1]) / self.scale

    def zoom_at(self, point, wheel_steps):
        before = self.screen_to_world(*point)
        self.zoom = max(1.0, min(self.max_zoom, self.zoom * 1.2 ** max(-30, min(30, wheel_steps))))
        after = self.screen_to_world(*point)
        self.x += before[0] - after[0]
        self.y += before[1] - after[1]
        self.clamp()

    def pan(self, dx, dy):
        self.x -= dx / self.scale
        self.y -= dy / self.scale
        self.clamp()

    def follow(self, x, y, elapsed):
        weight = -math.expm1(-8 * max(0, elapsed))
        self.x += (x - self.x) * weight
        self.y += (y - self.y) * weight
        self.clamp()
