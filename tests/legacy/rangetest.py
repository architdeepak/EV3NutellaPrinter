#!/usr/bin/env pybricks-micropython
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor, TouchSensor
from pybricks.parameters import Port, Direction, Stop
from pybricks.tools import wait

# --- Setup ---
class Consts:
    x_axis = Port.D
    y_axis = Port.A
    x_touch = Port.S4
    y_touch = Port.S1
    x_end = 27  # rotations
    y_end = 15  # rotations

ev3 = EV3Brick()
consts = Consts()

x_mtr = Motor(consts.x_axis)
y_mtr = Motor(consts.y_axis, positive_direction=Direction.COUNTERCLOCKWISE)
x_sns = TouchSensor(consts.x_touch)
y_sns = TouchSensor(consts.y_touch)

# --- Helper Functions ---
def reset_motor(mtr: Motor, sns: TouchSensor, power: int):
    ev3.speaker.beep()
    mtr.dc(power)
    while not sns.pressed():
        wait(10)
    mtr.brake()
    ev3.speaker.beep()

def go_to_relative(x, y, speed=800):
    global current_x, current_y
    dx = x - current_x
    dy = y - current_y
    x_deg = int(dx * consts.x_end * 360)
    y_deg = int(dy * consts.y_end * 360)
    x_mtr.run_angle(speed, x_deg, then=Stop.HOLD, wait=True)
    y_mtr.run_angle(speed, y_deg, then=Stop.HOLD, wait=True)
    current_x, current_y = x, y

# --- Main Test ---
reset_motor(x_mtr, x_sns, -100)
reset_motor(y_mtr, y_sns, -100)
current_x, current_y = 0.0, 0.0

# Move to test points
points = [(0,0), (1,0), (1,1), (0,1), (0,0)]  # corners of full area

for p in points:
    x, y = p
    ev3.speaker.say("Moving to {}, {}".format(x, y))
    print("Going to:", p)
    go_to_relative(x, y)
    wait(1000)

ev3.speaker.say("Done testing")
print("✅ Test complete.")
