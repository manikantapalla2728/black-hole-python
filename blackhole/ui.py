"""Interactive control panel (mouse sliders + buttons)."""
import pygame

from . import theme as T

SLIDERS = [
    ("mass", "BLACK HOLE MASS", 0.5, 3.0, "{:.2f}x", False),
    ("max_particles", "PARTICLE COUNT", 0, 2000, "{:d}", True),
    ("velocity", "INITIAL VELOCITY", 0.3, 1.5, "{:.2f}x v_circ", False),
    ("disk_speed", "DISK ROTATION", 0.0, 4.0, "{:.2f}x", False),
    ("gravity", "GRAVITATIONAL STRENGTH", 0.3, 2.5, "{:.2f}x", False),
    ("speed", "SIMULATION SPEED", 0.1, 3.0, "{:.2f}x", False),
    ("zoom", "CAMERA ZOOM", 0.4, 2.2, "{:.2f}x", False),
    ("spawn_rate", "SPAWN RATE", 0.0, 120.0, "{:.0f} /s", False),
]


class Panel:
    def __init__(self, exp, x0, width):
        self.exp, self.x0, self.w = exp, x0, width
        self.drag = None
        pad = 30
        self.track = []
        y = 330
        for spec in SLIDERS:
            self.track.append(pygame.Rect(x0 + pad, y + 44, width - 2 * pad, 12))
            y += 112
        names = [("START", self.start), ("PAUSE", self.pause),
                 ("RESET", exp.reset), ("SPAWN", lambda: exp.spawn(150)),
                 ("INFALL", exp.infall), ("DEMO", exp.start_demo)]
        self.buttons = []
        bw = (width - 2 * pad - 24) // 3
        for i, (label, fn) in enumerate(names):
            r = pygame.Rect(x0 + pad + (i % 3) * (bw + 12),
                            110 + (i // 3) * 92, bw, 72)
            self.buttons.append((r, label, fn))

    def start(self):
        self.exp.paused = False

    def pause(self):
        self.exp.paused = True

    def _set_from_mouse(self, i, mx):
        key, _, lo, hi, _, is_int = SLIDERS[i]
        r = self.track[i]
        k = max(0.0, min(1.0, (mx - r.x) / r.w))
        v = lo + (hi - lo) * k
        self.exp.set_param(key, int(round(v)) if is_int else v,
                           traced=True)

    def handle(self, ev, pos):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for r, label, fn in self.buttons:
                if r.collidepoint(pos):
                    fn()
                    return True
            for i, r in enumerate(self.track):
                if r.inflate(0, 44).collidepoint(pos):
                    self.drag = i
                    self._set_from_mouse(i, pos[0])
                    return True
        elif ev.type == pygame.MOUSEMOTION and self.drag is not None:
            self._set_from_mouse(self.drag, pos[0])
            return True
        elif ev.type == pygame.MOUSEBUTTONUP:
            self.drag = None
        return False

    def draw(self, surf):
        surf.fill(T.PANEL, (self.x0, 0, self.w, T.H))
        surf.fill((30, 36, 62), (self.x0, 0, 2, T.H))
        T.text(surf, "CONTROLS", T.font("sans", 34, True), T.WHITE,
               (self.x0 + 30, 40), "tl", spacing=4)
        T.text(surf, "experiment panel (not recorded)", T.font("sans", 20),
               T.DIM, (self.x0 + 30, 82), "tl")
        mx, my = pygame.mouse.get_pos()
        for r, label, fn in self.buttons:
            on = (label == "PAUSE" and self.exp.paused) or \
                 (label == "START" and not self.exp.paused)
            col = T.CYAN if on else (44, 52, 88)
            pygame.draw.rect(surf, (18, 22, 42), r, border_radius=14)
            pygame.draw.rect(surf, col, r, 3, border_radius=14)
            T.text(surf, label, T.font("sans", 26, True),
                   T.WHITE if on else T.TEXT, r.center, "mc", spacing=2)
        y = 330
        for i, (key, label, lo, hi, fmt, is_int) in enumerate(SLIDERS):
            v = getattr(self.exp.params, key)
            T.text(surf, label, T.font("sans", 21, True), T.DIM,
                   (self.x0 + 30, y), "tl", spacing=1)
            T.text(surf, fmt.format(int(v) if is_int else v),
                   T.font("mono", 24), T.GOLD,
                   (self.x0 + self.w - 30, y - 2), "tr")
            r = self.track[i]
            pygame.draw.rect(surf, (34, 40, 70), r, border_radius=6)
            k = (v - lo) / (hi - lo)
            fill = pygame.Rect(r.x, r.y, int(r.w * k), r.h)
            pygame.draw.rect(surf, T.VIOLET, fill, border_radius=6)
            pygame.draw.circle(surf, T.CYAN, (r.x + int(r.w * k), r.centery), 14)
            y += 112
        hints = ["SPACE start/pause   R reset", "S spawn   I infall   D demo",
                 "ESC quit"]
        for j, s in enumerate(hints):
            T.text(surf, s, T.font("mono", 20), T.DIM,
                   (self.x0 + 30, T.H - 130 + j * 30), "tl")
