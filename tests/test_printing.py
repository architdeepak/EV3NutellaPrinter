"""Hardware-free checks of the continuous origin-based controller."""
import ast
import csv
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch
import main
from dispensing import load_path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('previous_fakes', ROOT / 'tests/archive/before-continuous-rebuild/test_printing.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)

class Simulation:

    def __init__(self, blocked=False, cancel=False, stop_at=None, manual_pullback=0):
        self.world = old.World()
        self.motors = {}
        self.beeps = []
        self.marked = False
        self.blocked = blocked
        self.cancel = cancel
        self.stop_at = stop_at
        self.manual_pullback = manual_pullback
        self.pulled_back = False

    def beep(self):
        self.beeps.append(self.world.ms)
        if self.marked and self.world.ms >= 2000 and not self.pulled_back and self.manual_pullback:
            c = self.motors['C']
            c.position -= self.manual_pullback
            c.goal = c.position
            self.pulled_back = True

    def buttons(self):
        if self.cancel and self.world.ms >= 5:
            return ['up']
        if self.stop_at is not None and self.world.ms >= self.stop_at:
            return ['down']
        return []

    def runtime(self):
        sim = self

        class Motor(old.Motor):

            def __init__(self, port, **kwargs):
                super().__init__(sim.world)
                self.port = port
                sim.motors[port] = self

            def dc(self, power):
                self.calls.append(('dc', power))
                self.blocked = False
                super().run(800 if power > 0 else -800)

            def run(self, speed):
                self.calls.append(('run', speed, any(not sim.motors[p].control.done() for p in ('A', 'D'))))
                if self.port == 'C' and sim.blocked:
                    self.blocked = True
                super().run(speed)

            def limits(self, speed=None, acceleration=None, actuation=None):
                self.acceleration = acceleration
                super().limits(speed=speed, actuation=actuation)

        class Sensor:

            def __init__(self, port):
                self.reads = 0

            def pressed(self):
                self.reads += 1
                return self.reads >= 2
        brick = types.SimpleNamespace(buttons=types.SimpleNamespace(pressed=self.buttons), screen=types.SimpleNamespace(clear=lambda: None, print=lambda *a: None), speaker=types.SimpleNamespace(beep=self.beep))
        return (Motor, Sensor, lambda: brick, types.SimpleNamespace(A='A', B='B', C='C', D='D', S1='S1', S4='S4'), types.SimpleNamespace(COUNTERCLOCKWISE='ccw'), types.SimpleNamespace(HOLD='hold'), types.SimpleNamespace(DOWN='down', UP='up'), lambda: self.world, self.world.wait)

    def run(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p / 'paths').mkdir()
            shutil.copyfile(ROOT / 'paths/12.txt', p / 'paths/12.txt')
            previous = Path.cwd()
            try:
                os.chdir(p)
                with contextlib.redirect_stdout(io.StringIO()):
                    main.run(12, runtime=self.runtime())
                with (p / 'tests/results/print-0.csv').open() as f:
                    self.rows = list(csv.DictReader(f))
            finally:
                os.chdir(previous)

class PrintingTests(unittest.TestCase):

    def test_origin_geometry_and_command_order_for_every_point(self):
        source = subprocess.check_output(['git', 'show', '8338420:main.py'], cwd=ROOT).decode()
        node = next((n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'go_to_relative'))
        captured = []

        class Capture:

            def __init__(self, name):
                self.name = name

            def run_angle(self, speed, degrees, **kwargs):
                captured.append((self.name, speed, degrees))
        env = dict(Consts=types.SimpleNamespace(x_end=27, y_end=15), current_x=0.0, current_y=0.0, x_mtr=Capture('x'), y_mtr=Capture('y'), Stop=types.SimpleNamespace(HOLD='hold'))
        original = old.compile_function(node, env)
        points = load_path(str(ROOT / 'paths/12.txt'))
        for x, y, draw in points:
            original(x, y, speed=main.XY_SPEED)
        planned = []
        for x, y, d, dx, dy, xs, ys in main.motion_plan(points):
            planned.extend((('x', xs, dx), ('y', ys, dy)))
        self.assertEqual(captured, planned)

    def test_manual_syringe_goes_directly_to_homing_and_printing(self):
        sim = Simulation()
        sim.run()
        phases = [r['phase'] for r in sim.rows]
        self.assertNotIn('seek-flow', phases)
        self.assertNotIn('countdown', phases)
        self.assertLess(phases.index('home-x'), phases.index('home-y'))
        self.assertLess(phases.index('home-y'), phases.index('point'))
        first_axis = next(r for r in sim.rows if r['phase'] == 'axis-command')
        self.assertEqual(float(first_axis['c_angle'] or 0), 0)
        self.assertEqual(sim.rows[-1]['phase'], 'complete')
        self.assertTrue(all((m.braked for m in sim.motors.values())))
        self.assertIn((-400, 4000, 'hold', False), sim.motors['B'].calls)
        self.assertIn((400, 4000, 'hold', False), sim.motors['B'].calls)
        self.assertTrue(any((r['phase'] == 'stroke-reverse' for r in sim.rows)))
        self.assertIn((800, -90, 'hold', False), sim.motors['C'].calls)
        self.assertIn((800, -60, 'hold', False), sim.motors['C'].calls)
        self.assertEqual(sim.motors['A'].acceleration, 3600)
        self.assertTrue(any(call[0]=='run' and call[1]>0 and call[2] for call in sim.motors['C'].calls))

    def test_stalled_syringe_never_blocks_xy_or_completion(self):
        sim = Simulation(blocked=True)
        sim.run()
        self.assertEqual(sim.rows[-1]['phase'], 'complete')
        self.assertTrue(any((r['c_stalled'] == '1' for r in sim.rows)))
        self.assertEqual(int(sim.rows[-1]['point_index']), len(load_path(str(ROOT / 'paths/12.txt'))) - 1)

    def test_down_stops_after_setup(self):
        sim = Simulation(stop_at=12000)
        with self.assertRaisesRegex(RuntimeError, 'operator'):
            sim.run()
        self.assertTrue(all((m.braked for m in sim.motors.values())))

    def test_manual_line_ratio(self):
        self.assertAlmostEqual(main.BASE_FEED_RATIO * (1080 / 5400), 157)
        self.assertAlmostEqual(main.FEED_RATIO/main.BASE_FEED_RATIO,3.25)

    def test_extra_push_at_every_travel_to_draw_transition(self):
        sim=Simulation()
        sim.run()
        points=load_path(str(ROOT/'paths/12.txt'))
        previous=False
        starts=0
        for x,y,draw in points:
            if draw and not previous: starts+=1
            previous=draw
        pushes=[r for r in sim.rows if r['phase'] in ('first-stroke-restore','stroke-restore')]
        self.assertEqual(len(pushes),starts)
        for row in pushes:
            amount=float(row['event'].split('requested=')[1].split()[0])
            if row['phase']=='first-stroke-restore':
                self.assertGreaterEqual(amount,1440)
            else:
                self.assertGreaterEqual(amount,0)
if __name__ == '__main__':
    unittest.main()
