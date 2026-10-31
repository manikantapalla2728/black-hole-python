"""Headless experiment: physics + tracer + code view + renderer."""
from . import physics
from . import theme as T
from .codeview import CodeView
from .demo import Demo
from .render import Renderer
from .tracer import LineTracer

MAX_STEPS = 14


class Experiment:
    def __init__(self, quality=0.45, seed=7, particles=400):
        self.default_particles = particles
        self.seed = seed
        self.params = physics.Params()
        self.params.max_particles = particles
        self.world = physics.World(self.params, seed)
        self.tracer = LineTracer(physics)
        self.code = CodeView(physics.__file__)
        self.renderer = Renderer(quality, seed)
        self.paused = False
        self.clock = 0.0
        self.acc = 0.0
        self.flashes = []
        self.demo = None
        self.probe = None
        self._caption = None

    # ----- controls (all physics calls run under the tracer) -----
    def set_param(self, name, value, traced=True):
        if traced:
            self.tracer.call(self.world.set_param, name, value)
        else:
            setattr(self.params, name, value)

    def spawn(self, n=150):
        return self.tracer.call(self.world.spawn_ring, n)

    def infall(self):
        self.tracer.call(self.world.spawn_infaller)

    def reset(self):
        self.params.__init__()
        self.params.max_particles = self.default_particles
        self.world.reset()
        self.flashes.clear()
        self.acc = 0.0

    def start_demo(self):
        self.reset()
        self.paused = False
        self.demo = Demo(self)

    def caption(self, title, sub="", seconds=3.0):
        self._caption = (title, sub, self.clock, seconds)

    def caption_state(self):
        if not self._caption:
            return None
        title, sub, t0, dur = self._caption
        age = self.clock - t0
        if age > dur:
            return None
        alpha = min(1.0, age / 0.4, (dur - age) / 0.5)
        return title, sub, max(0.0, alpha)

    # ----- frame update -----
    def update(self, dt):
        if self.demo:
            self.demo.update(dt)
            if self.demo.finished:
                self.demo = None
        if not self.paused:
            self.acc += dt * self.params.speed
            n = 0
            while self.acc >= physics.DT and n < MAX_STEPS:
                self.tracer.call(self.world.step, physics.DT)
                self.acc -= physics.DT
                n += 1
            if n == MAX_STEPS:
                self.acc = 0.0
            for fx, fy in self.world.flashes:
                self.flashes.append([fx, fy, 0.0])
            self.world.flashes.clear()
        for f in self.flashes:
            f[2] += dt
        self.flashes = [f for f in self.flashes if f[2] < 0.9]
        self.probe = self.tracer.call(self.world.probe)
        self.code.feed(self.tracer.drain(), self.clock)
        self.clock += dt

    def draw(self, reel, dt=1 / 60):
        self.renderer.draw(reel, self)
        self.code.draw(reel, self.clock, dt)
