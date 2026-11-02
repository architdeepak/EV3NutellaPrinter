#!/usr/bin/env pybricks-micropython
"""Dry C-only benchmark. Requires a manually confirmed top reference.

Uses a virtual axis for feed tests; no physical X/Y/Z motors are initialized.
One Motor instance and one zero reference cover the entire sequence.
"""

from dispensing import Syringe


def run(start_angle=0, step=None):
    from pybricks.ev3devices import Motor
    from pybricks.hubs import EV3Brick
    from pybricks.parameters import Port, Stop, Button
    from pybricks.tools import StopWatch, wait
    try:
        import uos as os
    except ImportError:
        import os

    if start_angle < 0 or (step is not None and
                           (step <= 0 or start_angle+step > 1620)):
        raise ValueError('Requested measurement step exceeds known usable stroke')
    brick = EV3Brick()
    motor = Motor(Port.C)
    motor.reset_angle(start_angle)
    motor.control.limits(speed=720, actuation=100)
    clock = StopWatch()
    last_sample, last_report = -20, -1000
    phase = 'reference-restored' if start_angle else 'top-zero'
    command = 0.0
    limit = 1620 if step is not None else 1080
    rows = None
    duty_file = None

    def read_number(filename):
        if filename is None:
            return ''
        try:
            with open(filename) as source:
                return int(source.read().strip())
        except (OSError, ValueError):
            return ''

    for entry in os.ilistdir('/sys/class/tacho-motor'):
        name = entry[0]
        directory = '/sys/class/tacho-motor/' + name
        try:
            with open(directory + '/address') as source:
                if source.read().strip().endswith('outC'):
                    duty_file = directory + '/duty_cycle'
                    break
        except OSError:
            pass

    for directory in ('tests', 'tests/results'):
        try:
            os.mkdir(directory)
        except OSError:
            os.stat(directory)
    index = 0
    while True:
        filename = 'tests/results/c-bench-{}.csv'.format(index)
        try:
            with open(filename):
                pass
        except OSError:
            break
        index += 1
    rows = open(filename, 'w')
    rows.write('ms,phase,target_deg,actual_deg,turns,speed_deg_s,stalled,'
               'reported_duty_pct,battery_uv,event\n')

    def sample(event='sample', force=False):
        nonlocal last_sample, last_report
        now = clock.time()
        if not force and now-last_sample < 20:
            return
        angle, speed = motor.angle(), motor.speed()
        duty = read_number(duty_file)
        voltage = read_number('/sys/class/power_supply/lego-ev3-battery/voltage_now')
        rows.write('{},{},{},{},{:.5f},{},{},{},{},{}\n'.format(
            now, phase, command, angle, angle/360.0, speed,
            int(motor.control.stalled()), duty, voltage, event))
        if force or now-last_report >= 1000:
            rows.flush()
            print('C-BENCH', now, phase, 'target', command, 'actual', angle,
                  'speed', speed, 'reported duty', duty)
            last_report = now
        last_sample = now

    def guard():
        if Button.DOWN in brick.buttons.pressed():
            raise RuntimeError('Operator stop')
        if motor.angle() > limit or motor.angle() < -20:
            raise RuntimeError('Benchmark encoder travel limit')
        if clock.time() > 60000:
            raise RuntimeError('Benchmark overall time limit')

    def settle(target, began):
        settled = None
        while True:
            guard()
            sample()
            if abs(motor.angle()-target) <= 2 and abs(motor.speed()) <= 10:
                if settled is None:
                    settled = clock.time()
                if clock.time()-settled >= 100:
                    sample('settled', True)
                    return
            else:
                settled = None
            if clock.time()-began > 10000:
                raise RuntimeError('Position did not settle: '+phase)
            wait(20)

    def direct(target, label):
        nonlocal command, phase
        phase, command = label, target
        began = clock.time()
        motor.run_target(720, target, then=Stop.HOLD, wait=False)
        settle(target, began)

    class VirtualAxis:
        def __init__(self):
            self.position = 0.0
            self.start = 0.0
            self.change = 0.0
            self.began = 0
            self.duration = 0
            self.control = self

        def angle(self):
            if self.duration:
                ratio = min(1.0, max(0.0, (clock.time()-self.began)/self.duration))
                return self.start + self.change*ratio
            return self.position

        def run_angle(self, speed, rotation, then=None, wait=False):
            self.start = self.angle()
            self.change = rotation
            self.began = clock.time()
            self.duration = abs(rotation)/max(abs(speed), 1)*1000

        def done(self):
            return clock.time()-self.began >= self.duration

        def brake(self):
            self.position = self.angle()
            self.duration = 0

    def feed_sample(label, angle, target, actual, stalled):
        nonlocal command
        command = target
        guard()
        sample()

    print('LOG:', filename)
    print('C reference restored:', start_angle, 'speed/output limits:', motor.control.limits())
    print('C PID:', motor.control.pid())
    print('Only C is initialized. DOWN stops. Encoder travel limit:', limit)
    brick.screen.clear()
    brick.screen.print('Dry C benchmark')
    brick.screen.print('DOWN: stop')
    try:
        command = float(start_angle)
        sample('reference-restored' if start_angle else 'zero', True)
        if step is not None:
            direct(start_angle+step, 'measured-one-turn')
            sample('complete', True)
            print('MEASUREMENT STEP COMPLETE:', motor.angle(), 'degrees from original top')
            return
        direct(180, 'direct-180')

        phase = 'ramp-90-over-3s'
        origin, began = 180.0, clock.time()
        while clock.time()-began < 3000:
            guard()
            command = origin + 90*min(1.0, (clock.time()-began)/3000)
            motor.track_target(int(round(command)))
            sample()
            wait(20)
        command = 270.0
        motor.track_target(270)
        settle(270, clock.time())

        phase = 'drawing-feed-180'
        axis = VirtualAxis()
        feeder = Syringe(motor, 180, 1.0, limit, clock.time, wait,
                          lambda: Button.DOWN in brick.buttons.pressed(),
                          Stop.HOLD, feed_sample)
        for i in range(90):
            guard()
            feeder.move_axis(axis, 'virtual-x', 400, 20, 1800, True)
            command = feeder.target
            sample('feed-end', True)
            if (i+1) % 15 == 0:
                phase = 'travel-hold'
                feeder.move_axis(axis, 'virtual-x', 400, 50, 1800, False)
                sample('travel-end', True)
                phase = 'drawing-feed-180'
        direct(int(round(feeder.target+360)), 'direct-full-turn')
        phase = 'final-hold'
        motor.hold()
        began = clock.time()
        while clock.time()-began < 1000:
            guard()
            sample()
            wait(20)
        sample('complete', True)
        print('BENCH COMPLETE: angle', motor.angle(), 'turns', motor.angle()/360.0)
    except (Exception, KeyboardInterrupt) as error:
        print('BENCH STOPPED:', error)
        sample('error', True)
        raise
    finally:
        motor.brake()
        rows.flush()
        rows.close()
        print('C stopped. Current mechanical reset remains manual.')


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 4 and sys.argv[1] == '--step':
        run(start_angle=int(sys.argv[2]), step=int(sys.argv[3]))
    else:
        run()
