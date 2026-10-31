# SKILL CIRCUIT - Interactive Digital Black Hole
**LEARN . BUILD . GROW**

A 1080x1920 (9:16) Reel layout: **TOP 65 % = the live experiment, BOTTOM 35 % = the
actual Python source (`blackhole/physics.py`) that runs it**, with the executing line
highlighted in real time.

## Install & run (Windows, Python 3.10+)
```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py --demo        :: interactive window + scripted sequence
python main.py               :: interactive, you drive it
python main.py --record out.mp4        :: offscreen 1080x1920 MP4 (30 fps)
python -m unittest discover -s tests -v
```
`run.bat` / `record.bat` do the venv + install for you. The MP4 is encoded with the
ffmpeg binary shipped by `imageio-ffmpeg`; nothing else to install.

Useful flags: `--fps 60`, `--quality 0.75` (disk shading resolution, default 0.4
interactive / 0.6 recording), `--particles 800`, `--duration 20`, `--seed N`,
`--snapshot frame.png --at 12.5` (one still), `--frames-dir dir` (PNG sequence).

## Controls
Right-hand panel (interactive only, not recorded): mass, particle count, initial
velocity, disk rotation, gravitational strength, simulation speed, camera zoom, spawn
rate sliders; Start / Pause / Reset / Spawn / Infall / Demo buttons.
Keys: `SPACE` start-pause, `R` reset, `S` spawn ring, `I` infalling particle,
`D` restart demo, `ESC` quit. Every change takes effect on the next physics step, and
slider moves run through `World.set_param`, so you see that line light up.

## How the code panel is truly synchronised
* The panel displays `physics.py` exactly as read from disk (never a copy).
* `blackhole/tracer.py` runs each physics call (`World.step`, `spawn_ring`,
  `set_param`, `probe`, `lens_map`, ...) under `sys.settrace`, restricted to code
  objects defined in `physics.py`. It records the real `frame.f_lineno` of every
  executed line - no hand-written line numbers.
* Lines executed in the last frame glow faintly. The strong highlight ("focus") is
  chosen from lines that really ran:
  * **rare events** - the capture branch (`self.captured += ...` only executes when
    `hit.any()` is true), spawns, and slider/parameter changes - interrupt and hold;
  * otherwise it rotates through the continuously executing lines: gravity, velocity
    Verlet update, capture test, disk update, light-ray bending, lens map, angular
    momentum.
  Focus lines are found by searching the source text, so edits to `physics.py` stay
  in sync (a missing anchor is simply skipped).
* `tests/test_physics.py::TestTracer` proves, e.g., that the capture line is traced
  only on a step where a capture happens.

## The model - and what it is NOT
Educational, **Newtonian**. It does **not** solve Einstein's field equations.
* Gravity: `a = -GM r / |r|^3` (softened), integrated with **velocity Verlet**
  (2nd order, symplectic; tests check energy/angular-momentum conservation and
  convergence order). Orbits use `v = sqrt(GM/r)`; `L = x vy - y vx` is shown for a probe.
* Capture: a particle is removed when `r < r_s = 2GM/c^2` (clear, simplified
  capture-radius rule; sim units, `c^2 = 6.4e5`). No ISCO/frame-dragging physics.
* Light rays: Newtonian acceleration x2 at constant speed - a toy that reproduces the
  weak-field deflection `4GM/(b c^2)`; strong-field behaviour is not accurate.
* **Lensing is a visual approximation.** Background stars and particles behind the
  hole are remapped with the point-lens image formula `b' = (b + sqrt(b^2+4th^2))/2`;
  the disk's far-side arc, photon ring, Doppler brightening and spiral texture are
  artist-style shading, not ray-traced geodesics. The disk shear `~ r^-1.5` is Keplerian
  but mass-independent. The on-screen footer states this too.
* The disk-plane view is foreshortened (`S_INC = 0.4`) to mimic a tilted camera.

## Layout
```
main.py                  CLI entry (interactive / --record / --snapshot)
blackhole/physics.py     THE displayed source: physics + parameters + world
blackhole/tracer.py      sys.settrace line tracer
blackhole/codeview.py    editor panel, tokenize-based Python highlighting, auto-scroll
blackhole/render.py      scene: stars, lensing, disk, particles, rays, bloom, HUD
blackhole/experiment.py  physics loop + tracer + view glue (shared by app/recorder)
blackhole/demo.py        scripted 38 s sequence
blackhole/ui.py, app.py  interactive control panel and window
blackhole/recorder.py    offscreen deterministic recording (ffmpeg pipe)
tests/                   physics, tracer and headless render tests
```
The demo: dramatic intro -> spawn 140 particles -> two groups on different orbits ->
mass 1x -> 2x (many orbits collapse, captures fire) -> two infallers captured ->
zoom close-up -> brand end card.

## Performance & errors
Physics is vectorised NumPy at a fixed 120 Hz step (max 14 steps/frame). The disk is
shaded at reduced resolution then upscaled, with a bloom pass; ~25-45 ms/frame in a
typical CPU at the default quality (use `--quality 0.3` on slow machines). Missing
dependencies print an install hint; recording falls back to PNG frames if no ffmpeg is
found; pygame import errors never leave a half-written video.
Note: a debugger/coverage tool that also uses `sys.settrace` may conflict - the tracer
restores the previous trace function after every call.
