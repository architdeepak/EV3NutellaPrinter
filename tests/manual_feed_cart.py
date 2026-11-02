"""Move only A while recording hand-driven C, without resetting either encoder."""
import glob
import time
from pathlib import Path

motors = [Path(p) for p in glob.glob('/sys/class/tacho-motor/motor*')]
def device(port):
    return next(p for p in motors if (p/'address').read_text().strip().endswith(port))
cart, syringe = device('outA'), device('outC')
def number(p, name):
    return int((p/name).read_text())
if any(number(p, 'speed') != 0 or 'running' in (p/'state').read_text() for p in motors):
    raise RuntimeError('A motor is already moving; demonstration not started')
print('Cart starts in five seconds. C remains unpowered.', flush=True)
time.sleep(5)
y0, c0 = number(cart, 'position'), number(syringe, 'position')
yscale = 360/number(cart, 'count_per_rot')
cscale = 360/number(syringe, 'count_per_rot')
began = time.monotonic()
print('CART START; raw C reference', c0, flush=True)
print('seconds,cart_degrees,c_degrees,forward_degrees,backward_degrees', flush=True)
previous = c0
forward = backward = 0
try:
    # Clockwise A is negative Y in the original CCW-positive cart convention.
    (cart/'polarity').write_text('normal')
    (cart/'stop_action').write_text('brake')
    (cart/'speed_sp').write_text(str(round(200/yscale)))
    (cart/'position_sp').write_text(str(round(1080/yscale)))
    (cart/'command').write_text('run-to-rel-pos')
    while True:
        elapsed = time.monotonic()-began
        y, c = number(cart, 'position'), number(syringe, 'position')
        forward += max(0, c-previous)
        backward += max(0, previous-c)
        previous = c
        print('{:.3f},{:.2f},{:.2f},{:.2f},{:.2f}'.format(elapsed,
              (y-y0)*yscale, (c-c0)*cscale, forward*cscale, backward*cscale), flush=True)
        if elapsed > 0.3 and 'running' not in (cart/'state').read_text():
            print('CART STOPPED', flush=True)
            break
        if elapsed > 12 or abs(y-y0)*yscale > 1100:
            raise RuntimeError('Cart test time/travel bound reached')
        time.sleep(0.02)
finally:
    (cart/'command').write_text('stop')
