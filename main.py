#!/usr/bin/env pybricks-micropython
"""Origin geometry, observed flow, and concurrent speed-controlled syringe."""
from dispensing import load_path, drawing_distance
PATH_NUMBER = 12
XY_SPEED = 1800
XY_ACCELERATION = 3600
BASE_FEED_RATIO = 157 / (1080 / 5400)
FEED_RATIO = BASE_FEED_RATIO * 3.25
STROKE_START_EXTRA_DEG = 0
STROKE_START_PUSH_MS = 8000
STROKE_START_SPEED = 80
DRAW_FORWARD_MS = 4000
DRAW_HOLD_MS = 100
DRAW_FORWARD_SPEED = 100
PRIME_BURST_MS = 1500
PRIME_RELEASE_MS = 100
STROKE_PUSH_SPEED = 800
STROKE_REVERSE_DEG = 90
BETWEEN_STROKE_PAUSE_MS = 2000
FINAL_REVERSE_DEG = 60

def motion_plan(points, speed=XY_SPEED):
    x = y = 0.0
    for nx, ny, draw in points:
        dx, dy = (int((nx - x) * 27 * 360), int((ny - y) * 15 * 360))
        longest = max(abs(dx), abs(dy))
        yield (nx, ny, draw, dx, dy, speed * abs(dx / longest) if longest else speed, speed * abs(dy / longest) if longest else speed)
        x, y = (nx, ny)

def simplify_strokes(points):
    """Keep stroke endpoints so straight line tests traverse without tiny stops."""
    output = []
    i = 0
    while i < len(points):
        if not points[i][2]:
            output.append(points[i])
            i += 1
            continue
        start = i
        while i + 1 < len(points) and points[i + 1][2]:
            i += 1
        output.append(points[start])
        if i != start:
            output.append(points[i])
        i += 1
    return output

def run(path_number=PATH_NUMBER, skip_flow=False, runtime=None):
    if runtime is None:
        from pybricks.ev3devices import Motor, TouchSensor
        from pybricks.hubs import EV3Brick
        from pybricks.parameters import Port, Direction, Stop, Button
        from pybricks.tools import StopWatch, wait
        runtime = (Motor, TouchSensor, EV3Brick, Port, Direction, Stop, Button, StopWatch, wait)
    Motor, TouchSensor, EV3Brick, Port, Direction, Stop, Button, StopWatch, wait = runtime
    try:
        import uos as os
    except ImportError:
        import os
    points = simplify_strokes(load_path('paths/{}.txt'.format(path_number)))
    brick, clock = (EV3Brick(), StopWatch())
    motors = {}
    handle = None
    index = -1
    requested = ('', '', '')
    expected = command = 0.0
    last_sample = last_report = last_flush = -1000
    duty_path = None
    flow_mark = None
    electrical = ['', '']
    last_electrical = -1000

    def read(path):
        try:
            with open(path) as f:
                return f.read().strip()
        except (OSError, TypeError):
            return ''

    def stop():
        for m in motors.values():
            m.brake()

    def guard():
        # On this EV3 Pybricks build, the physical BACK button exits the
        # program directly; it is not part of brick.buttons().
        pass

    def log(phase, event='', force=False):
        nonlocal last_sample, last_report, last_flush, last_electrical
        now = clock.time()
        if handle is None or (not force and now - last_sample < 50):
            return
        values = [now, phase, index, requested[0], requested[1], requested[2], event, expected, command]
        metadata_only = phase in ('path-source', 'point', 'axis-command')
        if metadata_only:
            values.extend([''] * 12)
        else:
            for name in ('x', 'y', 'z', 'c'):
                m = motors[name]
                values.extend((m.angle(), m.speed(), int(m.control.stalled())))
            if now-last_electrical >= 1000:
                electrical[:] = [read(duty_path), read('/sys/class/power_supply/lego-ev3-battery/voltage_now')]
                last_electrical = now
        values.extend(electrical)
        handle.write(','.join(('"' + str(v).replace('"', '""') + '"' for v in values)) + '\n')
        last_sample = now
        if phase in ('complete', 'stopped', 'flow-confirmed') or now - last_flush >= 500:
            handle.flush()
            last_flush = now
        if not metadata_only and (phase in ('complete', 'stopped', 'flow-confirmed') or now - last_report >= 1000):
            print('MOTOR', now, phase, 'point', index, 'C', motors['c'].angle(), 'expected', expected, 'speed', motors['c'].speed(), 'stalled', motors['c'].control.stalled(), event)
            last_report = now

    def pause(ms, phase):
        began = clock.time()
        while clock.time() - began < ms:
            guard()
            log(phase)
            wait(10)

    def nudge(degrees, phase):
        m = motors['c']
        origin = m.angle()
        began = clock.time()
        if degrees > 0:
            m.dc(100)
            while m.angle() - origin < degrees:
                guard()
                log(phase)
                wait(10)
            m.brake()
        else:
            m.run_angle(800, degrees, then=Stop.HOLD, wait=False)
            while not m.control.done():
                guard()
                wait(5)
            m.hold()
        log(phase, 'requested={} actual={} elapsed_ms={}'.format(degrees, m.angle() - origin, clock.time() - began), True)

    def full_power_burst(duration, phase):
        m = motors['c']
        origin = m.angle()
        began = clock.time()
        m.dc(100)
        try:
            while clock.time() - began < duration:
                guard()
                log(phase)
                wait(10)
        finally:
            m.hold()
        log(phase + '-end', 'duration_ms={} angle_delta={}'.format(clock.time()-began, m.angle()-origin), True)

    def prime_until_down():
        brick.screen.clear()
        brick.screen.print('C forward; DOWN to print')
        while brick.buttons.pressed():
            wait(10)
        c = motors['c']
        c.dc(100)
        try:
            while Button.DOWN not in brick.buttons.pressed():
                log('prime-forward')
                wait(10)
        finally:
            c.hold()
        log('prime-marked', 'angle={}'.format(c.angle()), True)
        while Button.DOWN in brick.buttons.pressed():
            wait(10)

    def plate(up):
        motors['c'].hold()
        motors['z'].run_time(-400 if up else 400, 4000, then=Stop.HOLD, wait=False)
        while not motors['z'].control.done():
            pause(10, 'plate-up' if up else 'plate-down')
        log('plate-end', 'up=' + str(up), True)

    def home(name, sensor):
        brick.speaker.beep()
        motors[name].dc(-100)
        log('home-' + name, 'dc=-100', True)
        while not sensor.pressed():
            guard()
            log('home-' + name)
            wait(5)
        motors[name].brake()
        brick.speaker.beep()
        log('home-end-' + name, force=True)

    def move_xy(dx, dy, xs, ys, drawing):
        nonlocal expected, command
        axes = []
        for name, degrees, speed, span in (('x', dx, xs, 9720), ('y', dy, ys, 5400)):
            if degrees:
                axis = motors[name]
                origin = axis.angle()
                axes.append((name, axis, degrees, speed, span, origin))
        if not axes:
            return
        initial = expected
        expected_amount = sum(FEED_RATIO * abs(degrees) / span for _, _, degrees, _, span, _ in axes) if drawing else 0
        for name, axis, degrees, speed, span, origin in axes:
            log('axis-command', '{} degrees={} speed={} drawing={}'.format(name, degrees, speed, drawing), True)
            axis.run_angle(speed, degrees, then=Stop.HOLD, wait=False)
        while any(not axis.control.done() for _, axis, _, _, _, _ in axes):
            guard()
            progress_total = 0.0
            for name, axis, degrees, speed, span, origin in axes:
                progress = max(0.0, min(1.0, (axis.angle() - origin) / degrees))
                progress_total += FEED_RATIO * abs(degrees) / span * progress if drawing else 0
            expected = initial + progress_total
            if drawing:
                command = 800
                c.run(800)
            else:
                command = 0
                c.hold()
            log('draw-xy' if drawing else 'travel-xy')
            wait(10)
        expected = initial + expected_amount
        command = 0
        c.hold()
        for name, axis, degrees, speed, span, origin in axes:
            log('axis-end-' + name, 'endpoint_error={}'.format(axis.angle()-origin-degrees), True)

    try:
        motors['c'] = Motor(Port.C)
        motors['x'] = Motor(Port.D)
        motors['y'] = Motor(Port.A, positive_direction=Direction.COUNTERCLOCKWISE)
        motors['z'] = Motor(Port.B)
        sx, sy = (TouchSensor(Port.S4), TouchSensor(Port.S1))
        for name in ('x', 'y'):
            motors[name].control.limits(speed=XY_SPEED, acceleration=XY_ACCELERATION, actuation=100)
        c = motors['c']
        c.control.limits(speed=800, actuation=100)
        c.control.pid(kp=600)
        c.reset_angle(0)
        try:
            entries = os.ilistdir('/sys/class/tacho-motor') if hasattr(os, 'ilistdir') else ((n,) for n in os.listdir('/sys/class/tacho-motor'))
            for entry in entries:
                directory = '/sys/class/tacho-motor/' + entry[0]
                if read(directory + '/address').endswith('outC'):
                    duty_path = directory + '/duty_cycle'
        except OSError:
            pass
        for directory in ('tests', 'tests/results'):
            try:
                os.mkdir(directory)
            except OSError:
                pass
        num = 0
        while True:
            filename = 'tests/results/print-{}.csv'.format(num)
            try:
                with open(filename):
                    pass
            except OSError:
                break
            num += 1
        handle = open(filename, 'w')
        handle.write('ms,phase,point_index,x_requested,y_requested,draw,event,c_expected,c_command_speed,' + ','.join((name + '_' + field for name in ('x', 'y', 'z', 'c') for field in ('angle', 'speed', 'stalled'))) + ',c_reported_duty_pct,battery_uv\n')
        print('Telemetry:', filename)
        log('run-start', 'path={} points={} normalized_length={} ratio={} xy_speed={}'.format(path_number, len(points), drawing_distance(points, 9720, 5400), FEED_RATIO, XY_SPEED), True)
        for i, p in enumerate(points):
            log('path-source', '{}:{} {} {}'.format(i, p[0], p[1], p[2]), True)
        takeup = 0
        log('manual-syringe-ready', 'Operator positioned syringe before launch', True)
        plate(False)
        home('x', sx)
        home('y', sy)
        plan = iter(motion_plan(points))
        first = next(plan)
        x, y, draw, dx, dy, xs, ys = first
        requested = (x, y, int(draw))
        log('position-at-design-start', 'x={} y={}'.format(x, y), True)
        move_xy(dx, dy, xs, ys, False)
        is_drawing = False
        for index, (x, y, draw, dx, dy, xs, ys) in enumerate(plan, start=1):
            requested = (x, y, int(draw))
            guard()
            if draw != is_drawing:
                c.hold()
                if is_drawing:
                    c.hold()
                    takeup = 0
                plate(draw)
                first_stroke = draw and flow_mark is not None
                if first_stroke:
                    # Include measured manual pullback, plus any later drift.
                    takeup = max(0, flow_mark-c.angle())
                if draw:
                    nudge(-takeup, 'stroke-restore') if takeup else None
                    takeup = 0
                if first_stroke:
                    flow_mark = None
                expected = float(c.angle())
                is_drawing = draw
            log('point', 'dx={} dy={} xs={} ys={}'.format(dx, dy, xs, ys), True)
            move_xy(dx, dy, xs, ys, draw)
        stop()
        log('complete', force=True)
        print('Complete; motors stopped')
    except BaseException as error:
        stop()
        log('stopped', type(error).__name__ + ': ' + str(error), force=True)
        raise
    finally:
        stop()
        if handle:
            handle.close()
if __name__ == '__main__':
    import sys
    try:
        import pybricks.hubs
    except ImportError:
        from desktop import run as run_desktop
        run_desktop(draw_new='--draw' in sys.argv[1:])
    else:
        args = sys.argv[1:]
        number = int(args[1]) if len(args) > 1 and args[0] in ('--auto', '--skip-flow') else PATH_NUMBER
        run(number, skip_flow=bool(args and args[0] == '--skip-flow'))
