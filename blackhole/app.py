"""Interactive window (Pygame)."""
import pygame

from . import theme as T
from .experiment import Experiment
from .ui import Panel

PANEL_W = 420


def run(args):
    pygame.init()
    pygame.display.set_caption("SKILL CIRCUIT | Interactive Black Hole")
    info = pygame.display.Info()
    full = (T.W + PANEL_W, T.H)
    scale = args.scale or min(1.0, info.current_h * 0.88 / T.H)
    size = (int(full[0] * scale), int(full[1] * scale))
    screen = pygame.display.set_mode(size)
    canvas = pygame.Surface(full, depth=32)
    reel = canvas.subsurface((0, 0, T.W, T.H))
    exp = Experiment(args.quality or 0.4, args.seed, args.particles)
    panel = Panel(exp, T.W, PANEL_W)
    if args.demo:
        exp.start_demo()
    clock = pygame.time.Clock()
    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 1 / 20)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                k = ev.key
                if k == pygame.K_ESCAPE:
                    running = False
                elif k == pygame.K_SPACE:
                    exp.paused = not exp.paused
                elif k == pygame.K_r:
                    exp.reset()
                elif k == pygame.K_s:
                    exp.spawn(150)
                elif k == pygame.K_i:
                    exp.infall()
                elif k == pygame.K_d:
                    exp.start_demo()
            elif ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION,
                             pygame.MOUSEBUTTONUP):
                pos = (ev.pos[0] / scale, ev.pos[1] / scale)
                panel.handle(ev, pos)
        exp.update(dt)
        exp.draw(reel, dt)
        panel.draw(canvas)
        pygame.display.set_caption(
            f"SKILL CIRCUIT | Black Hole | {clock.get_fps():.0f} fps")
        screen.blit(pygame.transform.smoothscale(canvas, size), (0, 0))
        pygame.display.flip()
    pygame.quit()
