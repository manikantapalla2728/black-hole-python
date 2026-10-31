"""Shared layout constants, palette and fonts."""
import pygame

W, H = 1080, 1920
TOP_H = 1248            # 65 %
CODE_Y = TOP_H
CODE_H = H - TOP_H      # 35 %
CX, CY = W // 2, 626    # black hole centre on screen
S_INC = 0.40            # disk-plane foreshortening (camera tilt)

BG = (6, 8, 16)
PANEL = (10, 12, 24)
HEADER = (15, 18, 34)
TEXT = (208, 216, 238)
DIM = (112, 124, 154)
CYAN = (86, 218, 255)
VIOLET = (172, 128, 255)
ORANGE = (255, 148, 66)
GOLD = (255, 205, 110)
WHITE = (245, 247, 255)

MONO = "consolas,cascadiamono,couriernew,dejavusansmono,menlo,monospace"
SANS = "segoeui,helveticaneue,arial,dejavusans,sans"

_cache = {}


def font(kind, size, bold=False):
    key = (kind, size, bold)
    if key not in _cache:
        names = MONO if kind == "mono" else SANS
        _cache[key] = pygame.font.SysFont(names, size, bold=bold)
    return _cache[key]


def text(surf, s, f, color, pos, anchor="tl", spacing=0):
    """Draw text; optional letter-spacing; returns the rect."""
    if spacing:
        parts = [f.render(c, True, color) for c in s]
        w = sum(p.get_width() for p in parts) + spacing * (len(s) - 1)
        h = parts[0].get_height() if parts else f.get_height()
        img = pygame.Surface((max(w, 1), h), pygame.SRCALPHA)
        x = 0
        for p in parts:
            img.blit(p, (x, 0))
            x += p.get_width() + spacing
    else:
        img = f.render(s, True, color)
    rect = img.get_rect()
    setattr(rect, {"tl": "topleft", "tr": "topright", "tc": "midtop",
                   "ml": "midleft", "mc": "center", "mr": "midright",
                   "bl": "bottomleft", "br": "bottomright",
                   "bc": "midbottom"}[anchor], pos)
    surf.blit(img, rect)
    return rect
