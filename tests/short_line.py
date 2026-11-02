"""Single relative downward line. Requires raised plate and known C start."""
from pybricks.ev3devices import Motor
from pybricks.hubs import EV3Brick
from pybricks.parameters import Port, Direction, Stop, Button
from pybricks.tools import StopWatch, wait


def run(start_angle=510, feed_degrees=360):
    brick = EV3Brick()
    cart = Motor(Port.A, positive_direction=Direction.COUNTERCLOCKWISE)
    syringe = Motor(Port.C)
    syringe.reset_angle(start_angle)
    syringe.control.limits(speed=800, actuation=100)
    syringe.control.pid(kp=600)
    clock = StopWatch()
    stalled_since = None
    filename = 'tests/results/short-line-{}.csv'.format(brick.battery.voltage())
    # Unique suffix without relying on an EV3 wall clock.
    index = 0
    while True:
        filename = 'tests/results/short-line-{}.csv'.format(index)
        try:
            with open(filename):
                pass
        except OSError:
            break
        index += 1
    print('LOG:', filename)
    try:
        with open(filename, 'w') as log:
            log.write('ms,y_angle,y_speed,c_angle,c_speed,y_stalled,c_stalled,battery_mv\n')
            start = cart.angle()
            print('LINE: Y -1080 degrees at 100 deg/s; C +', feed_degrees,
                  'degrees at', feed_degrees/10.8, 'deg/s; start', start_angle)
            syringe.run_angle(feed_degrees/10.8, feed_degrees, then=Stop.HOLD, wait=False)
            cart.run_angle(100, -1080, then=Stop.HOLD, wait=False)
            last_report = -250
            while True:
                now = clock.time()
                ys, cs = cart.control.stalled(), syringe.control.stalled()
                values = (now, cart.angle(), cart.speed(), syringe.angle(),
                          syringe.speed(), int(ys), int(cs), brick.battery.voltage())
                log.write(','.join(str(v) for v in values)+'\n')
                if now-last_report >= 250:
                    log.flush()
                    print('LINE', values)
                    last_report = now
                if Button.DOWN in brick.buttons.pressed():
                    raise RuntimeError('Operator stop')
                if syringe.angle() > min(1800, start_angle+feed_degrees+16) or abs(cart.angle()-start) > 1100:
                    raise RuntimeError('Test travel bound exceeded')
                if ys or cs:
                    if stalled_since is None:
                        stalled_since = now
                    elif now-stalled_since >= 1000:
                        raise RuntimeError('Motor stalled; line stopped')
                else:
                    stalled_since = None
                if cart.control.done() and syringe.control.done():
                    print('LINE COMPLETE:', 'C', syringe.angle(), 'Y delta', cart.angle()-start)
                    break
                if now > 15000:
                    raise RuntimeError('Line test timed out')
                wait(20)
    finally:
        cart.brake()
        syringe.brake()
        print('LINE STOPPED: C', syringe.angle())


run()
