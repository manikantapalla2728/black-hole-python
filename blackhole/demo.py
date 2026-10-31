"""Scripted 38 s demonstration for the Reel."""


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class Demo:
    DURATION = 38.0

    def __init__(self, exp):
        self.exp = exp
        self.t = 0.0
        self.finished = False
        self.ramps = []
        e = exp
        e.params.zoom = 0.5
        self.script = [
            (0.0, lambda: (e.caption("A BLACK HOLE",
                                     "event horizon | disk | lensing", 3.4),
                           self.ramp("zoom", 0.5, 0.85, 5.0, False))),
            (3.6, lambda: (e.caption("SPAWN 140 PARTICLES",
                                     "spawn_ring()  v = sqrt(GM / r)", 2.6),
                           e.spawn(140))),
            (6.4, lambda: (e.caption("DIFFERENT ORBITS",
                                     "initial velocity x0.80 / x1.15", 3.0),
                           e.set_param("velocity", 0.80), e.spawn(70),
                           e.set_param("velocity", 1.15), e.spawn(70),
                           e.set_param("velocity", 1.0))),
            (12.5, lambda: (e.caption("MASS  1.0x  ->  2.0x",
                                      "same particles, stronger gravity", 4.2),
                            self.ramp("mass", 1.0, 2.0, 4.0, True))),
            (17.8, lambda: e.caption("TRAJECTORIES CHANGE",
                                     "orbits deform, some are captured", 3.6)),
            (23.0, lambda: (e.caption("INFALL",
                                      "low angular momentum -> r < r_s", 3.2),
                            e.infall())),
            (25.8, lambda: e.infall()),
            (28.0, lambda: (e.caption("CLOSE-UP", "", 2.4),
                            self.ramp("zoom", 0.85, 1.65, 7.0, False),
                            self.ramp("disk_speed", 1.0, 2.4, 7.0, False))),
            (35.0, lambda: e.caption("SKILL CIRCUIT",
                                     "LEARN  .  BUILD  .  GROW", 3.0)),
        ]
        self.idx = 0

    def ramp(self, key, v0, v1, dur, traced):
        self.ramps.append([key, self.t, dur, v0, v1, traced])

    def update(self, dt):
        self.t += dt
        while self.idx < len(self.script) and self.t >= self.script[self.idx][0]:
            self.script[self.idx][1]()
            self.idx += 1
        for key, t0, dur, v0, v1, traced in self.ramps:
            k = ease((self.t - t0) / dur)
            if 0.0 <= (self.t - t0) <= dur + dt:
                self.exp.set_param(key, v0 + (v1 - v0) * k, traced)
        self.ramps = [r for r in self.ramps if self.t - r[1] <= r[2] + dt]
        if self.t >= self.DURATION:
            self.finished = True
