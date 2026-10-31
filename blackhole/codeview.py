"""Code editor panel: shows the REAL physics.py and follows the
lines reported by the execution tracer."""
import io
import keyword
import math
import tokenize

import pygame

from . import theme as T

LH = 38           # line height (px)
FONT_PX = 24
GUTTER = 84

# (label, needle, colour, hold seconds, priority) - rare events
KEY_EVENTS = [
    ("CAPTURE  r < r_s", "self.captured +=", T.ORANGE, 1.8, 3),
    ("SPAWN  new particles", "self.pos = np.vstack(", T.CYAN, 1.3, 2),
    ("PARAM  live control change", "setattr(self.p", T.GOLD, 0.9, 2),
]
# lines that execute continuously, shown in rotation
CYCLE = [
    ("GRAVITY  a = -GM r / |r|^3", "return -gm * pos * inv_r3", T.CYAN),
    ("INTEGRATE  velocity Verlet", "vel = vel + 0.5 * (acc + acc_new)",
     T.VIOLET),
    ("CAPTURE TEST  |r| < r_s", "return (pos * pos).sum(axis=1) < r_c",
     T.ORANGE),
    ("DISK  spin update", "self.disk_t += dt", T.GOLD),
    ("LIGHT  rays bend 2x", "acc = 2.0 * gravity_accel", T.CYAN),
    ("LENS  visual approximation", "img = 0.5 * (b + np.sqrt", T.VIOLET),
    ("ANGULAR MOMENTUM  L = x vy - y vx", "return pos[:, 0] * vel[:, 1]",
     T.GOLD),
]
DWELL = 1.0


def find_lines(lines, needle):
    return [i + 1 for i, s in enumerate(lines) if needle in s]


def tokenize_lines(lines):
    """Return per-line segments [(text, colour)] using tokenize."""
    colors = {i + 1: [] for i in range(len(lines))}
    src = "\n".join(lines) + "\n"
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    prev = ""
    for k, tok in enumerate(toks):
        ttype, s, (sr, sc), (er, ec), _ = tok
        if sr != er or ttype in (tokenize.NEWLINE, tokenize.NL,
                                 tokenize.INDENT, tokenize.DEDENT,
                                 tokenize.ENDMARKER):
            continue
        col = T.TEXT
        nxt = toks[k + 1].string if k + 1 < len(toks) else ""
        if ttype == tokenize.COMMENT:
            col = T.DIM
        elif ttype == tokenize.STRING:
            col = T.CYAN
        elif ttype == tokenize.NUMBER:
            col = T.ORANGE
        elif ttype == tokenize.OP:
            col = (150, 165, 205)
        elif ttype == tokenize.NAME:
            if s in ("True", "False", "None"):
                col = T.ORANGE
            elif keyword.iskeyword(s):
                col = T.VIOLET
            elif prev in ("def", "class"):
                col = T.GOLD
            elif s == "self":
                col = (255, 140, 190)
            elif nxt == "(":
                col = T.CYAN
        colors[sr].append((sc, ec, col))
        prev = s
    out = {}
    for ln, text in enumerate(lines, 1):
        segs, pos = [], 0
        for a, b, c in sorted(colors[ln]):
            if a > pos:
                segs.append((text[pos:a], T.TEXT))
            segs.append((text[a:b], c))
            pos = b
        if pos < len(text):
            segs.append((text[pos:], T.TEXT))
        out[ln] = segs
    return out


class CodeView:
    def __init__(self, path):
        with open(path, "r", encoding="utf-8") as fh:
            self.lines = fh.read().split("\n")
        if self.lines and self.lines[-1] == "":
            self.lines.pop()
        self.name = path.replace("\\", "/").split("/")[-1]
        self.font = T.font("mono", FONT_PX)
        self.surfs = self._prerender()
        self.keys = {}
        for label, needle, color, hold, prio in KEY_EVENTS:
            for ln in find_lines(self.lines, needle):
                self.keys[ln] = (label, color, hold, prio)
        self.cycle = []
        for label, needle, color in CYCLE:
            hits = find_lines(self.lines, needle)
            if hits:
                self.cycle.append((hits[0], label, color))
        self.cycle.sort()
        self.heat = {}
        self.focus = self.cycle[0][0] if self.cycle else 1
        self.label = "READY"
        self.color = T.CYAN
        self.hold_until = 0.0
        self.prio = 0
        self.next_cycle = 0.0
        self.ptr = 0
        self.scroll = 0.0
        self.last_events = 0
        self.bands = {}

    def _prerender(self):
        segs = tokenize_lines(self.lines)
        surfs = []
        for ln in range(1, len(self.lines) + 1):
            width = max(1, sum(self.font.size(t)[0] for t, _ in segs[ln]))
            img = pygame.Surface((width, LH), pygame.SRCALPHA)
            x = 0
            for text, col in segs[ln]:
                if text.strip():
                    img.blit(self.font.render(text, True, col),
                             (x, (LH - self.font.get_height()) // 2))
                x += self.font.size(text)[0]
            surfs.append(img)
        return surfs

    def feed(self, events, now):
        """events: line numbers the tracer saw since the last frame."""
        seen = set(events)
        self.last_events = len(events)
        for ln in seen:
            if self.heat.get(ln, 0.0) < 0.6:
                self.heat[ln] = 0.6
        best = None
        for ln in seen:
            k = self.keys.get(ln)
            if k and (best is None or k[3] > best[1][3]):
                best = (ln, k)
        if best and (now >= self.hold_until or best[1][3] >= self.prio):
            ln, (label, color, hold, prio) = best
            self.focus, self.label, self.color = ln, label, color
            self.hold_until, self.prio = now + hold, prio
            self.next_cycle = now + hold
            return
        if now >= self.hold_until and now >= self.next_cycle and seen:
            for step in range(1, len(self.cycle) + 1):
                i = (self.ptr + step) % len(self.cycle)
                ln, label, color = self.cycle[i]
                if ln in seen:
                    self.ptr = i
                    self.focus, self.label, self.color = ln, label, color
                    self.prio = 0
                    self.next_cycle = now + DWELL
                    break

    def _band(self, size, color, alpha):
        key = (size, color, alpha)
        if key not in self.bands:
            s = pygame.Surface(size, pygame.SRCALPHA)
            s.fill((*color, alpha))
            self.bands[key] = s
        return self.bands[key]

    def draw(self, surf, now, dt):
        area = pygame.Rect(0, T.CODE_Y + 64, T.W, T.CODE_H - 64)
        surf.fill(T.PANEL, (0, T.CODE_Y, T.W, T.CODE_H))
        # smooth auto-scroll so the focused line sits ~40 % down
        target = (self.focus - 1) * LH - area.h * 0.40 + LH / 2
        target = max(0.0, min(target, len(self.lines) * LH - area.h))
        self.scroll += (target - self.scroll) * (1 - math.exp(-dt * 9.0))
        clip = surf.get_clip()
        surf.set_clip(area)
        first = max(0, int(self.scroll // LH))
        last = min(len(self.lines), first + area.h // LH + 2)
        for i in range(first, last):
            ln = i + 1
            y = area.y + i * LH - self.scroll
            h = self.heat.get(ln, 0.0)
            if h > 0.03:
                a = int(min(1.0, h) * 46)
                surf.blit(self._band((T.W, LH), (90, 200, 255), a),
                          (0, y))
            if ln == self.focus:
                pulse = 0.5 + 0.5 * math.sin(now * 7.0)
                a = int(58 + 26 * pulse)
                surf.blit(self._band((T.W, LH), self.color, a), (0, y))
                surf.fill(self.color, (0, y, 7, LH))
                surf.fill(self.color, (0, y, T.W, 1))
                surf.fill(self.color, (0, y + LH - 1, T.W, 1))
            numc = self.color if ln == self.focus else (82, 94, 124)
            n = self.font.render(str(ln), True, numc)
            surf.blit(n, (GUTTER - 18 - n.get_width(),
                          y + (LH - n.get_height()) // 2))
            surf.blit(self.surfs[i], (GUTTER, y),
                      pygame.Rect(0, 0, T.W - GUTTER - 8, LH))
        surf.set_clip(clip)
        for ln in list(self.heat):
            self.heat[ln] -= dt * 1.6
            if self.heat[ln] <= 0:
                del self.heat[ln]
        # header
        hdr = pygame.Rect(0, T.CODE_Y, T.W, 64)
        surf.fill(T.HEADER, hdr)
        for k, c in enumerate(((255, 96, 96), (255, 190, 70),
                               (70, 220, 120))):
            pygame.draw.circle(surf, c, (34 + k * 30, hdr.centery), 8)
        T.text(surf, self.name, T.font("mono", 24), T.TEXT,
               (150, hdr.centery), "ml")
        pulse = 0.55 + 0.45 * math.sin(now * 6.0)
        dot = tuple(int(c * pulse) for c in self.color)
        pygame.draw.circle(surf, dot, (T.W - 24, hdr.centery), 8)
        T.text(surf, f"{self.label}  :{self.focus}", T.font("sans", 24, True),
               self.color, (T.W - 44, hdr.centery), "mr")
        # divider with glow
        for k in range(10):
            a = 70 - k * 7
            s = pygame.Surface((T.W, 1), pygame.SRCALPHA)
            s.fill((*self.color, max(a, 0)))
            surf.blit(s, (0, T.CODE_Y - 1 - k))
        surf.fill(self.color, (0, T.CODE_Y, T.W, 2))
