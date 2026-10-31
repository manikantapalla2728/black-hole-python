"""SKILL CIRCUIT | Black Hole - educational Newtonian model."""
# NOT general relativity: no Einstein field equations here.
import math
import numpy as np

GM0 = 1.6e7        # GM at mass=1, gravity=1 (sim units)
C2 = 6.4e5         # c^2, used only for the capture radius
C = math.sqrt(C2)  # light speed in sim units (u/s)
SOFT = 4.0         # softening length: no singularity
DT = 1.0 / 120.0   # fixed physics step (seconds)
ESCAPE2 = 3000.0 ** 2
N_RAYS = 14        # light rays
TRAIL = 80         # points kept per ray trail


def schwarzschild_radius(gm):
    # capture-radius approximation: r_s = 2 GM / c^2
    return 2.0 * gm / C2


def circular_speed(r, gm):
    # Newtonian circular orbit: v = sqrt(GM / r)
    return np.sqrt(gm / r)


def angular_momentum(pos, vel):
    # per unit mass: L = x * vy - y * vx
    return pos[:, 0] * vel[:, 1] - pos[:, 1] * vel[:, 0]


def gravity_accel(pos, gm):
    # Newton: a = -GM * r_vec / |r|^3  (softened)
    r2 = (pos * pos).sum(axis=1) + SOFT ** 2
    inv_r3 = r2 ** -1.5
    return -gm * pos * inv_r3[:, None]


def verlet_step(pos, vel, gm, dt):
    # velocity Verlet: 2nd order, time-reversible
    acc = gravity_accel(pos, gm)
    pos = pos + vel * dt + 0.5 * acc * dt * dt
    acc_new = gravity_accel(pos, gm)
    vel = vel + 0.5 * (acc + acc_new) * dt
    return pos, vel


def capture_mask(pos, r_capture):
    # captured when the particle is inside r_capture
    return (pos * pos).sum(axis=1) < r_capture ** 2


def lens_map(rel, theta_e):
    # VISUAL approximation (weak-field point lens), not GR:
    # image radius b' = (b + sqrt(b^2 + 4 th^2)) / 2
    b = np.hypot(rel[:, 0], rel[:, 1]) + 1e-6
    img = 0.5 * (b + np.sqrt(b * b + 4.0 * theta_e ** 2))
    return rel * (img / b)[:, None]


class Params:
    # live-editable experiment controls
    def __init__(self):
        self.mass = 1.0          # black-hole mass
        self.gravity = 1.0       # G multiplier
        self.max_particles = 400
        self.velocity = 1.0      # x circular speed at spawn
        self.disk_speed = 1.0    # accretion-disk spin
        self.speed = 1.0         # simulation speed
        self.zoom = 0.85         # camera zoom
        self.spawn_rate = 0.0    # particles per second


class World:
    def __init__(self, params, seed=7):
        self.p = params
        self.rng = np.random.default_rng(seed)
        self.reset()

    def reset(self):
        self.pos = np.zeros((0, 2))
        self.vel = np.zeros((0, 2))
        self.time = 0.0
        self.disk_t = 0.0
        self.captured = 0
        self.spawn_acc = 0.0
        self.flashes = []
        self.init_photons()

    def gm(self):
        return GM0 * self.p.mass * self.p.gravity

    def set_param(self, name, value):
        setattr(self.p, name, value)

    def spawn_ring(self, n, r_min=200.0, r_max=520.0):
        # random radius + angle, tangential orbital velocity
        n = max(0, min(int(n), 3000))
        r = self.rng.uniform(r_min, r_max, n)
        a = self.rng.uniform(0.0, 2 * math.pi, n)
        pos = np.stack([r * np.cos(a), r * np.sin(a)], axis=1)
        tan = np.stack([-np.sin(a), np.cos(a)], axis=1)
        v = circular_speed(r, self.gm()) * self.p.velocity
        v = v * self.rng.normal(1.0, 0.03, n)
        self.pos = np.vstack([self.pos, pos])
        self.vel = np.vstack([self.vel, tan * v[:, None]])
        return n

    def spawn_infaller(self):
        # almost no angular momentum -> plunges inward
        a = self.rng.uniform(0.0, 2 * math.pi)
        r = 480.0
        pos = np.array([[r * math.cos(a), r * math.sin(a)]])
        tan = np.array([[-math.sin(a), math.cos(a)]])
        v = circular_speed(r, self.gm()) * 0.12
        self.pos = np.vstack([self.pos, pos])
        self.vel = np.vstack([self.vel, tan * v])

    def emit(self, dt):
        self.spawn_acc += self.p.spawn_rate * dt
        n = int(self.spawn_acc)
        if n > 0:
            self.spawn_acc -= n
            self.spawn_ring(n)

    def trim(self):
        # enforce particle-count control, drop escapers
        over = len(self.pos) - self.p.max_particles
        if over > 0:
            self.pos = self.pos[over:]
            self.vel = self.vel[over:]
        far = (self.pos * self.pos).sum(axis=1) > ESCAPE2
        if far.any():
            self.pos = self.pos[~far]
            self.vel = self.vel[~far]

    def advance_disk(self, dt):
        # disk phase advances; renderer shears it with r^-1.5
        self.disk_t += dt * self.p.disk_speed

    def init_photons(self):
        self.ray_y = np.linspace(-430.0, 430.0, N_RAYS)
        x0 = -800.0 - self.rng.uniform(0.0, 900.0, N_RAYS)
        self.ppos = np.stack([x0, self.ray_y], axis=1)
        self.pvel = np.tile([C, 0.0], (N_RAYS, 1))
        self.trail = np.repeat(self.ppos[:, None, :], TRAIL, axis=1)

    def advance_photons(self, dt, gm):
        # light bends twice as much as Newton predicts
        acc = 2.0 * gravity_accel(self.ppos, gm)
        v = self.pvel + acc * dt
        v *= C / np.hypot(v[:, 0], v[:, 1])[:, None]
        self.ppos = self.ppos + v * dt
        self.pvel = v
        self.trail = np.roll(self.trail, -1, axis=1)
        self.trail[:, -1] = self.ppos
        rs = schwarzschild_radius(gm)
        out = capture_mask(self.ppos, 1.5 * rs)
        out |= self.ppos[:, 0] > 800.0
        if out.any():
            self.respawn_rays(out)

    def respawn_rays(self, out):
        n = int(out.sum())
        x0 = -800.0 - self.rng.uniform(0.0, 700.0, n)
        self.ppos[out] = np.stack([x0, self.ray_y[out]], axis=1)
        self.pvel[out] = [C, 0.0]
        self.trail[out] = self.ppos[out][:, None, :]

    def step(self, dt=DT):
        gm = self.gm()
        r_cap = schwarzschild_radius(gm)
        self.emit(dt)
        self.pos, self.vel = verlet_step(self.pos, self.vel, gm, dt)
        hit = capture_mask(self.pos, r_cap)
        if hit.any():
            self.captured += int(hit.sum())
            self.flashes += [tuple(q) for q in self.pos[hit]]
            self.pos = self.pos[~hit]
            self.vel = self.vel[~hit]
        self.trim()
        self.advance_disk(dt)
        self.advance_photons(dt, gm)
        self.time += dt

    def probe(self):
        # first particle: radius, speed, angular momentum
        if len(self.pos) == 0:
            return None
        r = float(np.hypot(*self.pos[0]))
        v = float(np.hypot(*self.vel[0]))
        L = float(angular_momentum(self.pos[:1], self.vel[:1])[0])
        return r, v, L
