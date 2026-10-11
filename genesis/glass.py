"""Bounded, local frosted surfaces. No model or random-state access."""
import pygame


class Glass:
    def __init__(self):
        self.cache = {}
        self.reduced = False
        self.refreshes = 0

    def draw(self, screen, rect, role, now):
        rect = pygame.Rect(rect)
        key = (tuple(rect), self.reduced)
        cached = self.cache.get(role)
        if cached is None or cached[0] != key or (not self.reduced and now - cached[1] >= .1):
            surface = pygame.Surface(rect.size, pygame.SRCALPHA)
            if not self.reduced:
                crop = screen.subsurface(rect.clip(screen.get_rect()))
                small = pygame.transform.smoothscale(crop, (max(1, rect.w // 18), max(1, rect.h // 18)))
                surface.blit(pygame.transform.smoothscale(small, rect.size), (0, 0))
            tint = pygame.Surface(rect.size, pygame.SRCALPHA)
            tint.fill((22, 35, 56, 249 if self.reduced else 195))
            surface.blit(tint, (0, 0))
            mask = pygame.Surface(rect.size, pygame.SRCALPHA)
            radius = min(24, rect.h//2)
            pygame.draw.rect(mask, (255, 255, 255), mask.get_rect(), border_radius=radius)
            surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            pygame.draw.rect(surface, (187, 210, 235, 60), surface.get_rect(), 1, border_radius=radius)
            # Curved upper rim, soft interior sheen; cached with the local frost.
            sheen = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(sheen, (225, 240, 255, 14), (2, 2, rect.w-4, min(46, rect.h-4)), border_radius=radius)
            surface.blit(sheen, (0, 0))
            rim = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(rim, (230, 243, 255, 95), (1, 1, rect.w-2, rect.h-2), 1, border_radius=radius)
            surface.blit(rim, (0, 0), (0, 0, rect.w, radius+2))
            shadow = pygame.Surface((rect.w+20, rect.h+20), pygame.SRCALPHA)
            for pad in range(9, 0, -2):
                pygame.draw.rect(shadow, (0, 3, 12, 6+2*(9-pad)),
                                 (10-pad, 12-pad, rect.w+2*pad, rect.h+2*pad), border_radius=radius+pad)
            if len(self.cache) >= 8 and role not in self.cache:
                self.cache.clear()
            cached = (key, now, surface, shadow)
            self.cache[role] = cached
            self.refreshes += 1
        screen.blit(cached[3], (rect.x-10, rect.y-10))
        screen.blit(cached[2], rect)


def button(app, rect, title, active=False, focused=False, disabled=False, hover=None):
    focused = focused and not disabled
    if hover is None:
        hover = rect.collidepoint(pygame.mouse.get_pos())
    color = (57, 76, 99) if active else ((47, 61, 81) if hover and not disabled else (31, 43, 62))
    pygame.draw.rect(app.screen, color, rect, border_radius=9)
    pygame.draw.rect(app.screen, (183, 217, 249) if focused else ((114, 146, 178) if active else (66, 81, 104)), rect, 2 if focused else 1, border_radius=9)
    text = app.fonts[13].render(title, True, (109, 124, 145) if disabled else (237, 244, 253))
    app.screen.blit(text, text.get_rect(center=rect.center))


def speed_segments(app):
    rect = app.buttons["1"].union(app.buttons["4"])
    pygame.draw.rect(app.screen, (22, 34, 52), rect, border_radius=12)
    pygame.draw.rect(app.screen, (80, 101, 127), rect, 1, border_radius=12)
    for key in ("1", "2", "4"):
        box = app.buttons[key]
        active = app.sim_clock.speed == int(key)
        hover = box.collidepoint(pygame.mouse.get_pos())
        if active or hover:
            pygame.draw.rect(app.screen, (69, 101, 131) if active else (38, 55, 77), box.inflate(-4, -4), border_radius=9)
        if app.chrome_focus == key:
            pygame.draw.rect(app.screen, (224, 240, 255), box.inflate(-4, -4), 2, border_radius=9)
        label = app.fonts[15].render(key+"\u00d7", True, (251, 254, 255) if active else (178, 196, 220))
        app.screen.blit(label, label.get_rect(center=box.center))
