"""SKILL CIRCUIT | Interactive Digital Black Hole - entry point."""
import argparse
import os
import sys


def parse():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="store_true",
                    help="start the scripted demonstration")
    ap.add_argument("--record", metavar="OUT.mp4",
                    help="render the demo offscreen to a 1080x1920 video")
    ap.add_argument("--snapshot", metavar="OUT.png",
                    help="save one frame of the demo (see --at)")
    ap.add_argument("--at", type=float, default=10.0,
                    help="demo time in seconds for --snapshot")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--frames-dir", default=None,
                    help="write PNG frames instead of piping to ffmpeg")
    ap.add_argument("--quality", type=float, default=None,
                    help="disk shading resolution 0.25-0.9")
    ap.add_argument("--particles", type=int, default=400)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--scale", type=float, default=None,
                    help="window scale (default: fit screen)")
    return ap.parse_args()


def main():
    args = parse()
    offscreen = bool(args.record or args.snapshot)
    if offscreen:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        import pygame  # noqa: F401
        import numpy  # noqa: F401
    except ImportError as exc:
        print("Missing dependency:", exc)
        print("Run:  pip install -r requirements.txt")
        return 1
    from blackhole import recorder
    if args.record:
        recorder.render_demo(args.record, args.fps, args.duration,
                             args.quality or 0.6, args.seed,
                             args.particles, args.frames_dir)
    elif args.snapshot:
        recorder.snapshot(args.snapshot, args.at, args.quality or 0.6,
                          args.seed, args.particles, args.fps)
    else:
        from blackhole import app
        app.run(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
