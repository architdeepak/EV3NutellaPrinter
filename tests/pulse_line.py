"""Supervised relative line with bounded alternating syringe pulses."""
from pybricks.ev3devices import Motor
from pybricks.hubs import EV3Brick
from pybricks.parameters import Port, Direction, Stop, Button
from pybricks.tools import StopWatch, wait

brick = EV3Brick()
cart = Motor(Port.D)
c = Motor(Port.C)
c.reset_angle(1254)  # Last stopped encoder position, assuming no manual movement.
c.control.limits(speed=800, actuation=100)
c.control.pid(kp=600)
clock = StopWatch()
start_y = cart.angle()
phase = 'waiting'
pulses = 0
last_start = 0
stalled_since = None
index = 0
while True:
    filename = 'tests/results/pulse-line-{}.csv'.format(index)
    try:
        with open(filename):
            pass
    except OSError:
        break
    index += 1
print('LOG:', filename)
try:
    with open(filename, 'w') as log:
        log.write('ms,phase,pulses,y_angle,y_speed,c_angle,c_speed,c_stalled,battery_mv\n')
        cart.run_angle(200, -270, then=Stop.HOLD, wait=False)
        last_report = -500
        while True:
            now = clock.time()
            if Button.DOWN in brick.buttons.pressed():
                raise RuntimeError('Operator stop')
            if c.angle() > 1500 or c.angle() < 1224 or abs(cart.angle()-start_y) > 290:
                raise RuntimeError('Travel limit')
            if cart.control.stalled():
                raise RuntimeError('Cart stalled')
            if c.control.stalled():
                if stalled_since is None:
                    stalled_since = now
                elif now-stalled_since >= 1000:
                    print('C stalled; brief reverse and retry')
                    c.brake()
                    c.run_angle(800, -2, then=Stop.HOLD, wait=False)
                    phase = 'reverse'
                    stalled_since = None
            else:
                stalled_since = None
            if cart.control.done():
                print('LINE COMPLETE; syringe', c.angle(), 'cart delta', cart.angle()-start_y)
                break
            if phase == 'forward' and c.control.done():
                c.run_angle(800, -2, then=Stop.HOLD, wait=False)
                phase = 'reverse'
            elif phase == 'reverse' and c.control.done():
                phase = 'waiting'
            elif phase == 'waiting' and pulses < 25:
                c.run_angle(120, 50, then=Stop.HOLD, wait=False)
                phase = 'forward'
                pulses += 1
                last_start = now
            values = (now, phase, pulses, cart.angle(), cart.speed(), c.angle(),
                      c.speed(), int(c.control.stalled()), brick.battery.voltage())
            log.write(','.join(str(v) for v in values)+'\n')
            if now-last_report >= 500:
                log.flush()
                print('PULSE', values)
                last_report = now
            if now > 15000:
                raise RuntimeError('Test timed out')
            wait(20)
finally:
    cart.brake()
    c.brake()
    print('STOPPED: syringe', c.angle(), 'cart delta', cart.angle()-start_y)
