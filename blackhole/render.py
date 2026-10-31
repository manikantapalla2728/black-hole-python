"""Scene renderer (top 65 %).

Rendering is a VISUAL approximation: the lensing and disk shading are
artist-style models, not a general-relativistic ray tracer.
"""
import math

import numpy as np
import pygame

from . import physics
from . import theme as T

OFF1 = [(0, 0, 1.0)]
OFF5 = [(0, 0, 1.0), (1, 0, .55), (-1, 0, .55), (0, 1, .55), (0, -1, .55)]
OFF9 = OFF5 + [(1, 1, .3), (-1, 1, .3), (1, -1, .3), (-1, -1, .3),
               (2, 0, .2), (-2, 0, .2), (0, 2, .2), (0, -2, .2)]
R_IN, R_OUT, R_SH = 3.0, 8.0, 2.6     # in units of r_s
GAIN = 0.80


def _lut(stops, n=256):
    xs = [s[0] for s in stops]
    out = np.zeros((n, 3), np.float32)
    t = np.linspace(0, 1, n)
    for c in range(3):
        out[:, c] = np.interp(t, xs, [s[1][c] for s in stops])
    return out


DISK_LUT = _lut([(0.0, (70, 14, 60)), (0.22, (190, 52, 28)),
                 (0.5, (255, 140, 36)), (0.8, (255, 214, 120)),
                 (1.0, (255, 246, 228))])
PART_LUT = _lut([(0.0, (90, 210, 255)), (0.35, (170, 120, 255)),
                 (0.65, (255, 150, 70)), (1.0, (255, 240, 200))])


class Renderer:
    def __init__(self, quality=0.45, seed=3):
        rng = np.random.default_rng(seed)
        self.q = quality
        self.lw, self.lh = int(T.W * quality), int(T.TOP_H * quality)
        self.top = pygame.Surface((T.W, T.TOP_H), depth=32)
        self.big = pygame.Surface((T.W, T.TOP_H), depth=32)
        self.small = pygame.Surface((self.lw, self.lh), depth=32)
        self.b1 = pygame.Surface((T.W // 4, T.TOP_H // 4), depth=32)
        self.b2 = pygame.Surface((T.W // 12, T.TOP_H // 12), depth=32)
        self.ray_layer = pygame.Surface((T.W, T.TOP_H), depth=32)
        self._geometry()
        self.bg = self._background(rng)
        self._stars(rng)
        self.caption_cache = {}

    # ---------- one-time setup ----------
    def _geometry(self):
        q = self.q
        x = ((np.arange(self.lw) + 0.5) / q - T.CX).astype(np.float32)
        y = ((np.arange(self.lh) + 0.5) / q - T.CY).astype(np.float32)
        X, Y = x[:, None], y[None, :]
        Yd = Y / T.S_INC
        self.R0 = np.hypot(X, Yd).astype(np.float32)
        self.PHI_F = np.arctan2(Yd, X + 0 * Y).astype(np.float32)
        self.RHO = np.hypot(X, Y).astype(np.float32)
        self.PHI_B = np.arctan2(Y + 0 * X, X).astype(np.float32)
        rho = np.maximum(self.RHO, 1e-3)
        self.XN = (X / rho).astype(np.float32)
        s = (-Y / rho)
        self.WB = (0.28 + 0.72 * np.clip(s * 2.0 + 0.6, 0, 1)
                   ).astype(np.float32)
        self.WF = np.clip(Y / 6.0 + 0 * X, 0, 1).astype(np.float32)
        self.NEG = np.clip(-Y / 6.0 + 0 * X, 0, 1).astype(np.float32)

    def _background(self, rng):
        w, h = T.W, T.TOP_H
        xx = np.linspace(0, 1, w, dtype=np.float32)[:, None]
        yy = np.linspace(0, 1, h, dtype=np.float32)[None, :]
        base = np.zeros((w, h, 3), np.float32)
        base[:] = (4, 6, 14)
        glow = np.exp(-(((xx - .5) ** 2) / .16 + ((yy - .5) ** 2) / .12))
        base += glow[..., None] * np.array([12, 6, 26], np.float32)
        for tint, seed in (((70, 24, 120), 1), ((8, 60, 96), 2)):
            r = np.random.default_rng(seed + 11)
            n = r.random((7, 9)).astype(np.float32)
            n = np.kron(n, np.ones((1, 1), np.float32))
            tmp = pygame.Surface((7, 9), depth=32)
            pygame.surfarray.blit_array(
                tmp, np.repeat((n[..., None] * 255).astype(np.uint8), 3, 2))
            big = pygame.transform.smoothscale(tmp, (w, h))
            arr = pygame.surfarray.array3d(big)[..., 0].astype(np.float32)
            arr = (arr / 255.0) ** 3.0
            base += arr[..., None] * np.array(tint, np.float32) * 0.26
        surf = pygame.Surface((w, h), depth=32)
        pygame.surfarray.blit_array(surf, np.clip(base, 0, 255).astype(np.uint8))
        return surf

    def _stars(self, rng, n=2300):
        self.star_rel = np.stack([rng.uniform(-900, 900, n),
                                  rng.uniform(-900, 900, n)], 1)
        b = rng.random(n) ** 3.2
        self.star_b = (0.25 + 0.75 * b).astype(np.float32)
        tint = rng.random(n)
        col = np.where(tint[:, None] < .6, [255, 255, 255],
                       np.where(tint[:, None] < .85, [170, 205, 255],
                                [255, 220, 170])).astype(np.float32)
        self.star_col = col
        self.star_f = rng.uniform(.6, 2.5, n).astype(np.float32)
        self.star_ph = rng.uniform(0, 6.28, n).astype(np.float32)
        self.star_bright = self.star_b > .62

    # ---------- helpers ----------
    @staticmethod
    def _splat(surf, xs, ys, cols, offsets):
        pix = pygame.surfarray.pixels3d(surf)
        w, h = pix.shape[0], pix.shape[1]
        for dx, dy, k in offsets:
            x, y = xs + dx, ys + dy
            ok = (x >= 0) & (x < w) & (y >= 0) & (y < h)
            if not ok.any():
                continue
            x, y = x[ok], y[ok]
            add = (cols[ok] * k).astype(np.int16)
            pix[x, y] = np.minimum(pix[x, y].astype(np.int16) + add,
                                   255).astype(np.uint8)
        del pix

    def _disk(self, rs, z, disk_t):
        inv = 1.0 / (z * rs)
        xf = self.R0 * inv
        xb = self.RHO * inv
        beam = np.clip(1.0 - 0.32 * self.XN, 0.6, 1.5) ** 2
        # --- front half of the disk (tilted ellipse)
        lg = np.log(np.maximum(xf, 0.5))
        om = 11.3 * np.maximum(xf, 1.0) ** -1.5     # Kepler-like shear
        ph = self.PHI_F - disk_t * om
        tex = (0.60 + 0.24 * np.sin(3 * ph - 2.5 * lg)
               + 0.16 * np.sin(7 * ph - 4 * lg + 1.3)
               + 0.05 * np.sin(xf * 5.0))
        edge = (np.clip((xf - R_IN) * 14.0, 0, 1)
                * np.clip((R_OUT - xf) / 3.0, 0, 1))
        prof = np.maximum(xf / R_IN, 1.0) ** -1.5
        wf = self.WF + self.NEG * np.clip((xb - R_SH) * 8.0, 0, 1)
        inten = prof * edge * np.maximum(tex, 0.15) * beam * wf
        idx = (np.clip(R_IN / np.maximum(xf, 1e-3), 0, 1) ** 1.5 * 0.88 * 255
               ).astype(np.intp)
        out = DISK_LUT[idx] * inten[..., None]
        # --- lensed image of the far side (arc over the hole)
        xd = R_IN + (xb - R_SH) * 1.7
        lg = np.log(np.maximum(xd, 0.5))
        om = 11.3 * np.maximum(xd, 1.0) ** -1.5
        ph = self.PHI_B - disk_t * om
        tex = (0.60 + 0.24 * np.sin(3 * ph - 2.5 * lg)
               + 0.16 * np.sin(7 * ph - 4 * lg + 1.3))
        edge = (np.clip((xb - R_SH) * 14.0, 0, 1)
                * np.clip((R_OUT - xd) / 3.0, 0, 1))
        prof = np.maximum(xd / R_IN, 1.0) ** -1.5
        inten = prof * edge * np.maximum(tex, 0.15) * beam * self.WB * 0.95
        idx = (np.clip(R_IN / np.maximum(xd, 1e-3), 0, 1) ** 1.5 * 0.88 * 255
               ).astype(np.intp)
        out += DISK_LUT[idx] * inten[..., None]
        # --- photon ring + faint halo
        ring = np.exp(-((xb - R_SH) / 0.05) ** 2) * (xb > R_SH - .03)
        out += ring[..., None] * np.array([255, 232, 190], np.float32) * 1.1
        halo = np.exp(-np.maximum(xb - R_SH, 0) * 1.5) * (xb > R_SH) * 0.16
        out += halo[..., None] * np.array([120, 70, 230], np.float32)
        return np.clip(out * GAIN, 0, 255).astype(np.uint8)

    def _bloom(self, top):
        pygame.transform.smoothscale(top, self.b1.get_size(), self.b1)
        self.b1.fill((70, 70, 70), special_flags=pygame.BLEND_RGB_MULT)
        pygame.transform.smoothscale(top, self.b2.get_size(), self.b2)
        self.b2.fill((150, 150, 150), special_flags=pygame.BLEND_RGB_MULT)
        for src in (self.b1, self.b2):
            pygame.transform.smoothscale(src, self.big.get_size(), self.big)
            top.blit(self.big, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    # ---------- frame ----------
    def draw(self, reel, exp):
        w, p = exp.world, exp.params
        z = p.zoom
        gm = w.gm()
        rs = physics.schwarzschild_radius(gm)
        sh = max(2.0, R_SH * rs * z)
        top, now = self.top, exp.clock
        top.blit(self.bg, (0, 0))
        call = exp.tracer.call
        # stars, bent around the hole (point-lens approximation)
        img = call(physics.lens_map, self.star_rel, sh)
        xs = (T.CX + img[:, 0]).astype(np.intp)
        ys = (T.CY + img[:, 1]).astype(np.intp)
        tw = 0.78 + 0.22 * np.sin(now * self.star_f + self.star_ph)
        cols = self.star_col * (self.star_b * tw)[:, None] * 0.9
        br = self.star_bright
        self._splat(top, xs[~br], ys[~br], cols[~br], OFF1)
        self._splat(top, xs[br], ys[br], cols[br], OFF5)
        # particles behind the hole (lensed)
        pos = w.pos
        n = len(pos)
        if n:
            sx = pos[:, 0] * z
            sy = pos[:, 1] * z * T.S_INC
            rr = np.hypot(pos[:, 0], pos[:, 1])
            tt = np.clip(190.0 / np.maximum(rr, 1.0), 0, 1) ** 0.7
            pc = PART_LUT[(tt * 255).astype(np.intp)]
            back = pos[:, 1] < 0
            if back.any():
                rel = np.stack([sx[back], sy[back]], 1)
                li = call(physics.lens_map, rel, sh)
                self._splat(top, (T.CX + li[:, 0]).astype(np.intp),
                            (T.CY + li[:, 1]).astype(np.intp),
                            pc[back] * 1.25, OFF9)
        # light rays (sky plane)
        self._rays(top, w, z)
        # event horizon / shadow
        pygame.draw.circle(top, (0, 0, 0), (T.CX, T.CY), int(sh))
        # accretion disk + photon ring (additive)
        arr = self._disk(rs, z, w.disk_t)
        pygame.surfarray.blit_array(self.small, arr)
        pygame.transform.smoothscale(self.small, self.big.get_size(),
                                     self.big)
        top.blit(self.big, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        # particles in front of the hole
        if n:
            fr = ~back
            if fr.any():
                self._splat(top, (T.CX + sx[fr]).astype(np.intp),
                            (T.CY + sy[fr]).astype(np.intp), pc[fr] * 1.25, OFF9)
            self._probe(top, w, z, exp)
        self._flashes(top, exp, z)
        self._bloom(top)
        reel.blit(top, (0, 0))
        self._hud(reel, exp, rs)

    def _rays(self, top, w, z):
        tr = w.trail
        px = T.CX + tr[:, :, 0] * z
        py = T.CY + tr[:, :, 1] * z
        layer = self.ray_layer
        layer.fill((0, 0, 0))
        seg = 8
        for k in range(tr.shape[0]):
            xk, yk = px[k], py[k]
            if xk.max() < 0 or xk.min() > T.W or yk.max() < 0 \
                    or yk.min() > T.TOP_H:
                continue
            pts = list(zip(xk.tolist(), yk.tolist()))
            n = len(pts)
            for s in range(seg):
                a, b = s * (n - 1) // seg, (s + 1) * (n - 1) // seg + 1
                f = ((s + 1) / seg) ** 1.8
                col = (int(70 * f), int(190 * f), int(255 * f))
                pygame.draw.lines(layer, col, False, pts[a:b], 2)
            pygame.draw.circle(layer, (200, 245, 255), pts[-1], 3)
        top.blit(layer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _probe(self, top, w, z, exp):
        p0, v0 = w.pos[0], w.vel[0]
        c = (T.CX + p0[0] * z, T.CY + p0[1] * z * T.S_INC)
        pygame.draw.circle(top, T.WHITE, (int(c[0]), int(c[1])), 11, 1)
        label = exp.code.label
        if label.startswith("INTEGRATE") or label.startswith("ANG"):
            d = (v0[0] * .22 * z, v0[1] * .22 * z * T.S_INC)
            col = T.VIOLET
        elif label.startswith("GRAVITY"):
            a = physics.gravity_accel(w.pos[:1], w.gm())[0]
            d = (a[0] * .35 * z, a[1] * .35 * z * T.S_INC)
            col = T.CYAN
        else:
            return
        e = (c[0] + d[0], c[1] + d[1])
        pygame.draw.line(top, col, c, e, 3)
        pygame.draw.circle(top, col, (int(e[0]), int(e[1])), 5)

    def _flashes(self, top, exp, z):
        for fx, fy, age in exp.flashes:
            k = age / 0.9
            c = (int(T.CX + fx * z), int(T.CY + fy * z * T.S_INC))
            f = max(0.0, 1 - k)
            pygame.draw.circle(top, (int(255 * f), int(150 * f),
                                     int(60 * f)), c, int(10 + k * 110), 4)
            pygame.draw.circle(top, (int(255 * f), int(235 * f),
                                     int(200 * f)), c, int(12 * f) + 2)

    def _hud(self, reel, exp, rs):
        w, p = exp.world, exp.params
        T.text(reel, "BLACK HOLE", T.font("sans", 40, True), T.WHITE,
               (44, 40), "tl", spacing=4)
        T.text(reel, "LIVE EXPERIMENT  |  NEWTONIAN MODEL",
               T.font("sans", 21), T.CYAN, (46, 92), "tl", spacing=2)
        T.text(reel, "SKILL CIRCUIT", T.font("sans", 30, True), T.GOLD,
               (T.W - 44, 42), "tr", spacing=3)
        T.text(reel, "LEARN  .  BUILD  .  GROW", T.font("sans", 19),
               T.DIM, (T.W - 44, 84), "tr", spacing=2)
        f = T.font("mono", 22)
        probe = exp.probe
        lines = [f"M   {p.mass:4.2f}x     r_s  {rs:6.1f}",
                 f"N   {len(w.pos):<5d}     captured {w.captured}"]
        if probe:
            lines.append(f"probe r {probe[0]:5.0f}  v {probe[1]:4.0f}  "
                         f"L {probe[2]:.2e}")
        y = T.TOP_H - 28 - 30 * len(lines)
        for s in lines:
            T.text(reel, s, f, T.TEXT, (44, y), "tl")
            y += 30
        T.text(reel, "visual lensing approximation - not full GR",
               T.font("sans", 18), T.DIM, (T.W - 44, T.TOP_H - 30), "br")
        cap = exp.caption_state()
        if cap:
            title, sub, alpha = cap
            key = (title, sub)
            if key not in self.caption_cache:
                a = T.font("sans", 52, True).render(title, True, T.WHITE)
                b = T.font("sans", 26).render(sub, True, T.CYAN)
                s = pygame.Surface((max(a.get_width(), b.get_width()),
                                    a.get_height() + b.get_height() + 6),
                                   pygame.SRCALPHA)
                s.blit(a, ((s.get_width() - a.get_width()) // 2, 0))
                s.blit(b, ((s.get_width() - b.get_width()) // 2,
                           a.get_height() + 6))
                self.caption_cache = {key: s}
            s = self.caption_cache[key]
            s.set_alpha(int(255 * alpha))
            reel.blit(s, s.get_rect(midbottom=(T.W // 2, T.TOP_H - 150)))
