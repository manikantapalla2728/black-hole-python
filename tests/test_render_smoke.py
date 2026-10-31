"""Headless smoke test of the full experiment (needs pygame)."""
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import pygame
except ImportError:   # pragma: no cover
    pygame = None


@unittest.skipIf(pygame is None, "pygame not installed")
class TestSmoke(unittest.TestCase):
    def test_demo_frames_and_code_sync(self):
        from blackhole import theme as T
        from blackhole.experiment import Experiment
        pygame.init()
        pygame.display.set_mode((32, 32))
        exp = Experiment(quality=0.25)
        exp.start_demo()
        reel = pygame.Surface((T.W, T.H), depth=32)
        labels = set()
        for _ in range(30 * 30):          # 30 s of demo at 30 fps
            exp.update(1 / 30)
            labels.add(exp.code.label)
        exp.draw(reel, 1 / 30)
        self.assertGreater(exp.world.captured, 0)
        self.assertTrue(any(l.startswith("CAPTURE  r") for l in labels))
        self.assertTrue(any(l.startswith("SPAWN") for l in labels))
        self.assertTrue(any(l.startswith("GRAVITY") for l in labels))
        top = pygame.surfarray.array3d(reel)[:, :T.TOP_H]
        self.assertGreater(top.mean(), 3)
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
