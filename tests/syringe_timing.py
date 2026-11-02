#!/usr/bin/env pybricks-micropython
"""Supervised C-only timing measurement; run only after manual plunger reset."""

SPEED_DEG_S = 720
TIME_LIMIT_MS = 30000


def run():
    from pybricks.ev3devices import Motor
    from pybricks.hubs import EV3Brick
    from pybricks.parameters import Button, Port, Stop
    from pybricks.tools import StopWatch, wait

    # The results directory is created before launching this tool.
    index = 0
    while True:
        filename = 'tests/results/syringe-timing-{}.csv'.format(index)
        try:
            with open(filename):
                pass
        except OSError:
            break
        index += 1

    brick = EV3Brick()
    motor = Motor(Port.C)
    origin = motor.angle()
    watch = StopWatch()
    reason = 'time_limit'
    last_sample = -100
    last_report = -250
    logfile = open(filename, 'w')
    logfile.write('ms,degrees,rotations,speed_deg_s,stalled,event\n')

    def record(event='sample'):
        elapsed = watch.time()
        degrees = motor.angle() - origin
        speed = motor.speed()
        stalled = motor.control.stalled()
        logfile.write('{},{},{:.5f},{},{},{}\n'.format(
            elapsed, degrees, degrees / 360.0, speed, int(stalled), event))
        logfile.flush()
        return elapsed, degrees, speed, stalled

    print('LOG:', filename)
    print('C only: {} deg/s, up to {} ms; DOWN stops'.format(
        SPEED_DEG_S, TIME_LIMIT_MS))
    print('Factory limits:', motor.control.limits())
    try:
        watch.reset()
        motor.run_time(SPEED_DEG_S, TIME_LIMIT_MS, then=Stop.HOLD, wait=False)
        while watch.time() < TIME_LIMIT_MS + 250:
            if Button.DOWN in brick.buttons.pressed():
                reason = 'down_button'
                break
            if watch.time() - last_sample >= 100:
                elapsed, degrees, speed, stalled = record()
                last_sample = elapsed
                if elapsed - last_report >= 250:
                    print('ms', elapsed, 'deg', degrees, 'turns', degrees / 360.0,
                          'speed', speed, 'stalled', stalled)
                    last_report = elapsed
            if motor.control.done():
                break
            wait(20)
    except KeyboardInterrupt:
        reason = 'operator_interrupt'
    finally:
        motor.brake()
        elapsed, degrees, speed, stalled = record(reason)
        logfile.close()
        print('STOPPED:', reason, 'ms', elapsed, 'degrees', degrees,
              'rotations', degrees / 360.0)


if __name__ == '__main__':
    run()
