"""Read-only presentation state, interpolation, bounded effects and sprite caches.

Never imports random or writes to an organism. Effect geometry is a function of
event IDs, so neither rendering nor toggling effects can touch simulation RNG.
"""

from collections import deque
from dataclasses import dataclass
from functools import lru_cache
import math

import pygame

from .simulation import Traits, World
from .sprite_cache import surface_cache


PALETTE = ((54, 230, 255), (179, 255, 75), (255, 165, 58), (255, 78, 169), (163, 104, 255))
GOLD = (255, 205, 94)
PREDATOR_PALETTE = ((255, 119, 106), (255, 95, 127), (255, 78, 169), (220, 89, 239), (180, 105, 255))
HABITAT_COLORS = ((106, 181, 217), (63, 220, 175), (171, 131, 239))


def color_index(traits: Traits) -> int:
    # Stable full-domain mapping. 33 quantized colors bound sprite keys.
    low, high = Traits.BOUNDS["size"]
    return max(0, min(32, round((traits.size-low)/(high-low)*32)))


def palette_color(index, palette=PALETTE):
    position=max(0,min(32,index))/8
    left=min(3,int(position)); fraction=position-left
    return tuple(round(a+(b-a)*fraction) for a,b in zip(palette[left],palette[left+1]))


def trait_color(traits: Traits) -> tuple[int, int, int]:
    return palette_color(color_index(traits))


def organism_color(organism):
    return palette_color(color_index(organism.traits), PREDATOR_PALETTE if organism.species == "predator" else PALETTE)


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    heading: float


@dataclass(frozen=True)
class Effect:
    kind: str
    x: float
    y: float
    color: tuple[int, int, int]
    started: float
    lifetime: float
    vx: float = 0
    vy: float = 0


class VisualState:
    MAX_EFFECTS = 256
    TRAIL_POINTS = 10
    TRAIL_LIFETIME = 0.24

    def __init__(self, world: World, enabled: bool = True):
        self.enabled = enabled
        self.time = 0.0
        self.current = self.snapshot(world)
        self.previous = self.current.copy()
        self.trails: dict[int, deque] = {}
        self.effects: deque[Effect] = deque(maxlen=self.MAX_EFFECTS)

    @staticmethod
    def snapshot(world):
        return {o.id: Pose(o.x, o.y, o.heading) for o in world.organisms.values()}

    def toggle(self):
        self.enabled = not self.enabled
        self.effects.clear()
        self.trails.clear()

    def advance(self, seconds: float):
        """Real presentation seconds; called only while not manually paused."""
        self.time += seconds
        self.effects = deque((e for e in self.effects if self.time - e.started < e.lifetime), maxlen=self.MAX_EFFECTS)
        for points in self.trails.values():
            while points and self.time - points[0][2] > self.TRAIL_LIFETIME:
                points.popleft()

    def on_step(self, world: World):
        self.previous, self.current = self.current, self.snapshot(world)
        # Retain neither dead poses nor old lineage trails. Newborns have no
        # previous pose, so interpolation starts at their actual spawn point.
        self.previous = {oid: pose for oid, pose in self.previous.items() if oid in self.current}
        self.trails = {oid: trail for oid, trail in self.trails.items() if oid in self.current}
        if not self.enabled:
            return
        for oid, pose in self.current.items():
            previous = self.previous.get(oid, pose)
            trail = self.trails.setdefault(oid, deque(maxlen=self.TRAIL_POINTS))
            trail.append((previous.x, previous.y, self.time))
        for event in world.events:
            color = trait_color(event.traits)
            if event.kind == "eat":
                self.effects.append(Effect("eat", event.x, event.y, GOLD, self.time, 0.38))
            elif event.kind == "catch":
                self.effects.append(Effect("catch", event.x, event.y, palette_color(color_index(event.traits), PREDATOR_PALETTE), self.time, .4))
            elif event.kind == "birth":
                self.effects.append(Effect("birth", event.x, event.y, color, self.time, 0.6))
            elif event.kind == "death":
                for i in range(5):
                    angle = event.organism_id * 2.39996 + i * math.tau / 5
                    speed = 8 + i * 1.6
                    self.effects.append(Effect("death", event.x, event.y, color, self.time, 0.85,
                                               math.cos(angle) * speed, math.sin(angle) * speed))

    def pose(self, organism, alpha: float) -> Pose:
        current = self.current.get(organism.id, Pose(organism.x, organism.y, organism.heading))
        previous = self.previous.get(organism.id, current)
        alpha = max(0.0, min(1.0, alpha))
        turn = (current.heading - previous.heading + math.pi) % math.tau - math.pi
        return Pose(previous.x + (current.x - previous.x) * alpha,
                    previous.y + (current.y - previous.y) * alpha,
                    previous.heading + turn * alpha)


@surface_cache()
def cell_sprite(index: int, radius: int, pulse: int, glow: bool) -> pygame.Surface:
    """Quantized radius/pulse and 33 colors keep the LRU strictly bounded."""
    color = palette_color(index)
    body = radius + pulse * 0.16
    extent = math.ceil(radius * 2.8 + 3)
    surface = pygame.Surface((extent * 2 + 1, extent * 2 + 1), pygame.SRCALPHA)
    center = (extent, extent)
    if glow:
        for r in range(extent, max(1, round(body)), -1):
            opacity = round(21 * (1 - (r - body) / (extent - body)) ** 2)
            pygame.draw.circle(surface, (*color, opacity), center, r)
    pygame.draw.circle(surface, (*color, 52), center, max(3, round(body)))
    pygame.draw.circle(surface, (*color, 150), center, max(3, round(body)), 1)
    pygame.draw.circle(surface, (*color, 250), center, max(2, round(radius * 0.49)))
    pygame.draw.circle(surface, (239, 252, 255, 210), (extent - max(1, radius // 3), extent - max(1, radius // 3)), 1)
    return surface


@lru_cache(maxsize=16)
def food_sprite(size: int, glow: bool) -> pygame.Surface:
    extent = size + 3
    surface = pygame.Surface((extent * 2 + 1, extent * 2 + 1), pygame.SRCALPHA)
    if glow:
        pygame.draw.circle(surface, (*GOLD, 12), (extent, extent), extent)
        pygame.draw.circle(surface, (*GOLD, 24), (extent, extent), size + 1)
    # Four-point gold sparkle, unmistakably different from round cells.
    points = [(extent, extent - size), (extent + 1, extent - 1), (extent + size, extent),
              (extent + 1, extent + 1), (extent, extent + size), (extent - 1, extent + 1),
              (extent - size, extent), (extent - 1, extent - 1)]
    pygame.draw.polygon(surface, (*GOLD, 195), points)
    surface.set_at((extent, extent), (255, 244, 196, 240))
    return surface


@surface_cache()
def predator_sprite(index: int, radius: int, pulse: int, glow: bool) -> pygame.Surface:
    """Angular luminous hunters; inherited body size selects the warm palette."""
    color = palette_color(index, PREDATOR_PALETTE)
    extent = math.ceil(radius * 2.8 + 3)
    surface = pygame.Surface((extent * 2 + 1, extent * 2 + 1), pygame.SRCALPHA)
    body = radius + pulse * .16
    if glow:
        for r in range(extent, max(1, round(body)), -1):
            pygame.draw.circle(surface, (*color, round(18 * (1 - (r - body) / (extent - body)) ** 2)), (extent, extent), r)
    def triangle(r):
        return [(extent, extent - r), (extent + r, extent + r * .75), (extent - r, extent + r * .75)]
    pygame.draw.polygon(surface, (*color, 64), triangle(body))
    pygame.draw.polygon(surface, (*color, 220), triangle(body), 1)
    pygame.draw.polygon(surface, (*color, 255), triangle(body * .48))
    return surface


class EcosystemRenderer:
    def __init__(self):
        self.background = None
        self.overlay = None
        self.size = None
        self.habitat_map = None
        self.show_habitats = None
        self._view_key = None
        self._view_background = None

    def prepare(self, size, habitats=None, show_habitats=True):
        if self.size == size and self.habitat_map is habitats and self.show_habitats == show_habitats:
            return
        self.size = size
        self.habitat_map, self.show_habitats = habitats, show_habitats
        self.background = pygame.Surface(size)
        width, height = size
        for y in range(height):
            t = y / max(1, height - 1)
            pygame.draw.line(self.background, (6 + round(3 * t), 14 + round(5 * t), 35 + round(10 * t)), (0, y), (width, y))
        if habitats and habitats.columns > 1 and show_habitats:
            # A small coordinate-aligned light field, smoothly enlarged once.
            # Decorative cloud modulation has no randomness or model effects.
            light = pygame.Surface((habitats.columns, habitats.rows))
            colors = ((8, 19, 43), (8, 43, 47), (30, 20, 59))
            for row in range(habitats.rows):
                for col in range(habitats.columns):
                    color = [0.0, 0.0, 0.0]
                    for dy, wy in ((-1, 1), (0, 2), (1, 1)):
                        for dx, wx in ((-1, 1), (0, 2), (1, 1)):
                            rr = max(0, min(habitats.rows - 1, row + dy))
                            cc = max(0, min(habitats.columns - 1, col + dx))
                            base = colors[habitats.cells[rr * habitats.columns + cc]]
                            for channel in range(3):
                                color[channel] += base[channel] * wx * wy / 16
                    cloud = .88 + .12 * math.sin(col * .42 + row * .21) * math.cos(row * .37)
                    light.set_at((col, row), tuple(round(v * cloud) for v in color))
            self.background.blit(pygame.transform.smoothscale(light, size), (0, 0))
        # Sparse microscope reticle points, quieter than a full grid.
        for x in range(24, width, 48):
            for y in range(24, height, 48):
                self.background.set_at((x, y), (24, 41, 67))
        self.overlay = pygame.Surface(size, pygame.SRCALPHA)

    def draw(self, screen, viewport, scale, world, state, alpha, selected_id, show_habitats=True, camera=None):
        self.prepare((round(world.config.width), round(world.config.height)) if camera else viewport.size,
                     world.habitats, show_habitats)
        screen.set_clip(viewport)
        # One transform per frame, shared by thousands of trail vertices.
        left, top = (camera.left, camera.top) if camera else (0, 0)
        if camera:
            key = (self.background, tuple(viewport), left, top, scale)
            if key != self._view_key:
                # Crop BEFORE scaling: allocation stays viewport-sized at every zoom.
                source = pygame.Rect(math.floor(left), math.floor(top),
                                     math.ceil(viewport.width / scale) + 2, math.ceil(viewport.height / scale) + 2)
                source = source.clip(self.background.get_rect())
                self._view_background = pygame.Surface(viewport.size)
                self._view_background.fill((5, 10, 27))
                if source.width and source.height:
                    enlarged = pygame.transform.smoothscale(self.background.subsurface(source),
                                                           (max(1, round(source.width * scale)), max(1, round(source.height * scale))))
                    self._view_background.blit(enlarged, (round((source.x - left) * scale), round((source.y - top) * scale)))
                self._view_key = key
            background = self._view_background
        else:
            background = self.background
        if state.enabled and show_habitats and world.environment.enabled:
            # Tint only the background, before food/cells/trails. No RNG or animation clock.
            growth = world.environment.seasonal_multiplier-.5
            tint = (5, 2, 0) if world.environment.drought_end is not None else (0, round(growth*4), round(growth*6))
            key = (background, tint)
            if getattr(self, "_environment_key", None) != key:
                self._environment_background = background.copy()
                self._environment_background.fill(tint, special_flags=pygame.BLEND_RGB_ADD)
                self._environment_key = key
            background = self._environment_background
        screen.blit(background, viewport)
        if self.overlay.get_size() != viewport.size:
            self.overlay = pygame.Surface(viewport.size, pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 0))

        def local(x, y):
            return round((x - left) * scale), round((y - top) * scale)

        def visible(x, y, margin):
            return -margin <= x <= viewport.width + margin and -margin <= y <= viewport.height + margin

        selected = world.organisms.get(selected_id)
        if selected:
            pose = state.pose(selected, alpha)
            center = local(pose.x, pose.y)
            radius = round(selected.traits.sense * scale)
            pygame.draw.circle(self.overlay, (164, 216, 255, 10), center, radius)
            pygame.draw.circle(self.overlay, (199, 236, 255, 55), center, radius, 1)
        if state.enabled:
            for oid, points in state.trails.items():
                if oid not in world.organisms:
                    continue
                organism = world.organisms[oid]
                color = organism_color(organism)
                points = list(points)
                # End the trail at the interpolated pose, never at the future state.
                pose = state.pose(world.organisms[oid], alpha)
                points.append((pose.x, pose.y, state.time))
                pixels = [local(x, y) for x, y, _ in points]
                thickness = max(1, round(2 * scale))
                for i in range(1, len(points)):
                    fade = max(0, 1 - (state.time - points[i - 1][2]) / state.TRAIL_LIFETIME)
                    opacity = round(60 * fade * i / len(points))
                    pygame.draw.line(self.overlay, (*color, opacity), pixels[i - 1], pixels[i], thickness)
            for effect in state.effects:
                age = max(0, state.time - effect.started)
                t = min(1, age / effect.lifetime)
                center = local(effect.x + effect.vx * age, effect.y + effect.vy * age)
                opacity = round((1 - t) ** 1.5 * 145)
                if effect.kind == "death":
                    pygame.draw.circle(self.overlay, (*effect.color, opacity), center, max(1, round(2 * scale * (1 - t))))
                else:
                    radius = max(1, round((4 + t * (15 if effect.kind == "eat" else 24)) * scale))
                    if effect.kind == "catch":
                        points = [(center[0], center[1] - radius), (center[0] + radius, center[1]),
                                  (center[0], center[1] + radius), (center[0] - radius, center[1])]
                        pygame.draw.polygon(self.overlay, (*effect.color, opacity), points, 1)
                    else:
                        pygame.draw.circle(self.overlay, (*effect.color, opacity), center, radius, 1)
                    if effect.kind == "birth":
                        pygame.draw.circle(self.overlay, (244, 247, 255, round(80 * (1 - t))), center, max(1, round((1 - t) * 8 * scale)))
        screen.blit(self.overlay, viewport)
        sparkle = food_sprite(max(2, min(24, round(3 * scale))), state.enabled)
        for food in world.food.values():
            if world.config.rules_version == 2:
                sparkle = food_sprite(max(2, min(24, round((2.3 + .7*((food.id-1)%3)) * scale))), state.enabled)
            lx, ly = local(food.x, food.y)
            if not visible(lx, ly, sparkle.get_width()):
                continue
            center = (viewport.x + lx, viewport.y + ly)
            screen.blit(sparkle, sparkle.get_rect(center=center))
        for organism in world.organisms.values():
            pose = state.pose(organism, alpha)
            lx, ly = local(pose.x, pose.y)
            radius = max(4, min(96, round(organism.traits.size * scale * 1.28)))
            if radius > 20:
                radius = round(radius / 2) * 2
            if not visible(lx, ly, radius * 3 + 8):
                continue
            center = (viewport.x + lx, viewport.y + ly)
            pulse = round(2 * math.sin(state.time * 2.4 + organism.id * 2.39996)) if state.enabled else 0
            sprite_fn = predator_sprite if organism.species == "predator" else cell_sprite
            sprite = sprite_fn(color_index(organism.traits), radius, pulse, state.enabled)
            screen.blit(sprite, sprite.get_rect(center=center))
            # A small internal organelle conveys heading without arrow-like cells.
            tip = (round(center[0] + math.cos(pose.heading) * radius * 0.55),
                   round(center[1] + math.sin(pose.heading) * radius * 0.55))
            pygame.draw.circle(screen, (232, 248, 255), tip, 1)
            if organism.id == selected_id:
                pygame.draw.circle(screen, (248, 252, 255), center, radius + 5, 2)
        screen.set_clip(None)
