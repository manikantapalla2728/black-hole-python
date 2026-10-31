"""Offscreen recording: renders the scripted demo to a 1080x1920 MP4."""
import os
import shutil
import subprocess
import sys
import time

import pygame

from . import theme as T
from .demo import Demo
from .experiment import Experiment


def find_ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def _bytes(surface):
    fn = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
    return fn(surface, "RGB")


def render_demo(path, fps=30, duration=None, quality=0.6, seed=7,
                particles=400, frames_dir=None):
    pygame.init()
    pygame.display.set_mode((64, 64))
    exp = Experiment(quality, seed, particles)
    exp.start_demo()
    duration = duration or Demo.DURATION
    total = int(duration * fps)
    reel = pygame.Surface((T.W, T.H), depth=32)
    ffmpeg = None if frames_dir else find_ffmpeg()
    proc = None
    if frames_dir:
        os.makedirs(frames_dir, exist_ok=True)
    elif ffmpeg:
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo",
               "-pix_fmt", "rgb24", "-s", f"{T.W}x{T.H}", "-r", str(fps),
               "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
               "-crf", "16", "-pix_fmt", "yuv420p", "-movflags",
               "+faststart", path]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    else:
        frames_dir = os.path.splitext(path)[0] + "_frames"
        os.makedirs(frames_dir, exist_ok=True)
        print("ffmpeg not found - writing PNG frames to", frames_dir)
    t0 = time.time()
    for i in range(total):
        exp.update(1.0 / fps)
        exp.draw(reel, 1.0 / fps)
        if proc:
            try:
                proc.stdin.write(_bytes(reel))
            except BrokenPipeError:
                print("ffmpeg closed the pipe early")
                break
        else:
            pygame.image.save(reel, os.path.join(frames_dir,
                                                 f"frame_{i:05d}.png"))
        if i % 30 == 0:
            el = time.time() - t0
            eta = el / (i + 1) * (total - i - 1)
            print(f"\rframe {i + 1}/{total}  eta {eta:4.0f}s", end="")
            sys.stdout.flush()
    print()
    if proc:
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg failed")
        print("saved", path)
    elif frames_dir:
        print("encode with: ffmpeg -framerate", fps, "-i",
              os.path.join(frames_dir, "frame_%05d.png"),
              "-c:v libx264 -pix_fmt yuv420p", path)
    pygame.quit()


def snapshot(path, at=10.0, quality=0.6, seed=7, particles=400, fps=30):
    pygame.init()
    pygame.display.set_mode((64, 64))
    exp = Experiment(quality, seed, particles)
    exp.start_demo()
    reel = pygame.Surface((T.W, T.H), depth=32)
    frames = int(at * fps)
    for i in range(frames):
        exp.update(1.0 / fps)
        if i >= frames - 24:      # let the code view scroll settle
            exp.draw(reel, 1.0 / fps)
    pygame.image.save(reel, path)
    print("saved", path)
    pygame.quit()
