"""Tests for the core physics (run: python -m unittest -v)."""
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from blackhole import physics as ph  # noqa: E402
from blackhole.tracer import LineTracer  # noqa: E402

GM = ph.GM0


def energy(pos, vel, gm):
    r = np.hypot(pos[:, 0], pos[:, 1])
    return 0.5 * (vel * vel).sum(axis=1) - gm / r


def orbit(pos, vel, steps, dt=ph.DT, gm=GM):
    for _ in range(steps):
        pos, vel = ph.verlet_step(pos, vel, gm, dt)
    return pos, vel


class TestFormulas(unittest.TestCase):
    def test_schwarzschild_radius_scales_with_mass(self):
        r1 = ph.schwarzschild_radius(GM)
        self.assertAlmostEqual(r1, 2 * GM / ph.C2)
        self.assertAlmostEqual(ph.schwarzschild_radius(2 * GM), 2 * r1)
        self.assertAlmostEqual(r1, 50.0)

    def test_circular_speed(self):
        self.assertAlmostEqual(float(ph.circular_speed(400.0, GM)),
                               math.sqrt(GM / 400.0))

    def test_gravity_points_to_centre_and_falls_as_inverse_square(self):
        a1 = ph.gravity_accel(np.array([[300.0, 0.0]]), GM)[0]
        a2 = ph.gravity_accel(np.array([[600.0, 0.0]]), GM)[0]
        self.assertLess(a1[0], 0)
        self.assertAlmostEqual(a1[1], 0.0)
        self.assertAlmostEqual(a1[0] / a2[0], 4.0, delta=0.01)  # softening
        self.assertAlmostEqual(-a1[0], GM / 300.0 ** 2, delta=2.0)

    def test_angular_momentum(self):
        L = ph.angular_momentum(np.array([[3.0, 0.0]]),
                                np.array([[0.0, 2.0]]))
        self.assertAlmostEqual(float(L[0]), 6.0)

    def test_capture_mask(self):
        pos = np.array([[10.0, 0.0], [60.0, 0.0], [0.0, 49.0]])
        self.assertEqual(ph.capture_mask(pos, 50.0).tolist(),
                         [True, False, True])

    def test_lens_never_places_images_inside_einstein_radius(self):
        rel = np.array([[1.0, 0.0], [50.0, 50.0], [-300.0, 20.0]])
        img = ph.lens_map(rel, 100.0)
        self.assertTrue((np.hypot(img[:, 0], img[:, 1]) >= 100.0 - 1e-6).all())
        far = ph.lens_map(np.array([[5000.0, 0.0]]), 100.0)
        self.assertAlmostEqual(far[0, 0] / 5000.0, 1.0, places=3)


class TestIntegrator(unittest.TestCase):
    def test_circular_orbit_keeps_its_radius(self):
        r = 300.0
        pos = np.array([[r, 0.0]])
        vel = np.array([[0.0, float(ph.circular_speed(r, GM))]])
        period = 2 * math.pi * math.sqrt(r ** 3 / GM)
        steps = int(3 * period / ph.DT)
        for _ in range(steps):
            pos, vel = ph.verlet_step(pos, vel, GM, ph.DT)
            self.assertAlmostEqual(float(np.hypot(*pos[0])), r, delta=r * 0.01)

    def test_energy_and_angular_momentum_conserved(self):
        pos = np.array([[400.0, 0.0]])
        vel = np.array([[0.0, 0.8 * float(ph.circular_speed(400.0, GM))]])
        e0, l0 = energy(pos, vel, GM)[0], ph.angular_momentum(pos, vel)[0]
        pos, vel = orbit(pos, vel, 4000)
        self.assertAlmostEqual(energy(pos, vel, GM)[0] / e0, 1.0, delta=2e-3)
        self.assertAlmostEqual(ph.angular_momentum(pos, vel)[0] / l0, 1.0,
                               delta=1e-6)

    def test_second_order_convergence(self):
        pos = np.array([[400.0, 0.0]])
        vel = np.array([[0.0, 150.0]])
        t = 0.5

        def run(dt):
            return orbit(pos, vel, int(round(t / dt)), dt)[0][0]
        ref = run(1 / 3840)
        e1 = np.hypot(*(run(1 / 120) - ref))
        e2 = np.hypot(*(run(1 / 240) - ref))
        self.assertGreater(e1 / e2, 3.0)   # ~4 for a 2nd-order scheme


class TestWorld(unittest.TestCase):
    def make(self):
        return ph.World(ph.Params(), seed=1)

    def test_spawn_ring_gives_tangential_circular_velocity(self):
        w = self.make()
        w.spawn_ring(50)
        self.assertEqual(len(w.pos), 50)
        r = np.hypot(w.pos[:, 0], w.pos[:, 1])
        v = np.hypot(w.vel[:, 0], w.vel[:, 1])
        ratio = v / ph.circular_speed(r, w.gm())
        self.assertTrue((abs(ratio - 1) < 0.15).all())
        radial = (w.pos * w.vel).sum(axis=1) / (r * v)
        self.assertTrue((abs(radial) < 1e-6).all())

    def test_infaller_is_captured(self):
        w = self.make()
        w.spawn_infaller()
        for _ in range(int(6 / ph.DT)):
            w.step()
            if w.captured:
                break
        self.assertEqual(w.captured, 1)
        self.assertEqual(len(w.pos), 0)
        self.assertEqual(len(w.flashes), 1)

    def test_more_mass_captures_more(self):
        counts = []
        for mass in (1.0, 2.0):
            w = self.make()
            w.p.mass = 1.0
            w.spawn_ring(200)
            w.p.mass = mass
            for _ in range(int(8 / ph.DT)):
                w.step()
            counts.append(w.captured)
        self.assertGreater(counts[1], counts[0])

    def test_particle_count_control_trims(self):
        w = self.make()
        w.spawn_ring(300)
        w.p.max_particles = 100
        w.step()
        self.assertEqual(len(w.pos), 100)

    def test_spawn_rate_emits_particles(self):
        w = self.make()
        w.p.spawn_rate = 60.0
        for _ in range(120):
            w.step()
        self.assertGreater(len(w.pos) + w.captured, 40)

    def test_light_is_deflected_toward_mass(self):
        w = self.make()
        for _ in range(int(3 / ph.DT)):
            w.step()
        self.assertTrue(np.isfinite(w.ppos).all())
        speed = np.hypot(w.pvel[:, 0], w.pvel[:, 1])
        self.assertTrue(np.allclose(speed, ph.C))


class TestTracer(unittest.TestCase):
    """The highlighted lines must be lines that really executed."""

    def setUp(self):
        self.tracer = LineTracer(ph)
        with open(ph.__file__, encoding="utf-8") as fh:
            self.src = fh.read().split("\n")

    def text(self, ln):
        return self.src[ln - 1].strip()

    def test_trace_contains_gravity_and_integrator_lines(self):
        w = ph.World(ph.Params(), 1)
        w.spawn_ring(10)
        self.tracer.call(w.step)
        texts = [self.text(n) for n in self.tracer.drain()]
        self.assertIn("return -gm * pos * inv_r3[:, None]", texts)
        self.assertIn("vel = vel + 0.5 * (acc + acc_new) * dt", texts)
        self.assertIn("self.disk_t += dt * self.p.disk_speed", texts)

    def test_capture_branch_only_traced_on_capture(self):
        w = ph.World(ph.Params(), 1)
        w.spawn_ring(10)
        self.tracer.call(w.step)
        texts = [self.text(n) for n in self.tracer.drain()]
        self.assertNotIn("self.captured += int(hit.sum())", texts)
        w.pos[0] = [5.0, 0.0]               # inside r_s
        self.tracer.call(w.step)
        texts = [self.text(n) for n in self.tracer.drain()]
        self.assertIn("self.captured += int(hit.sum())", texts)

    def test_traced_lines_belong_to_the_file(self):
        w = ph.World(ph.Params(), 1)
        self.tracer.call(w.spawn_ring, 5)
        self.tracer.call(w.set_param, "mass", 2.0)
        lines = self.tracer.drain()
        self.assertTrue(lines)
        self.assertTrue(all(1 <= n <= len(self.src) for n in lines))
        self.assertTrue(all(self.text(n) for n in lines))
        self.assertEqual(w.p.mass, 2.0)

    def test_untraced_code_is_ignored_and_tracing_restores(self):
        def foreign():
            return sum(range(10))
        self.assertEqual(self.tracer.call(foreign), 45)
        self.assertEqual(self.tracer.drain(), [])
        self.assertIsNone(sys.gettrace())


if __name__ == "__main__":
    unittest.main()
