#!/usr/bin/env pybricks-micropython

"""

Script: Surprise for Squirrel

TODO: 
- Every so often, have it re-zero the motors --> noticing significant drift over time
- Add background of bread slice to drawing app (`draw.py`)
- Add smoothing algorithm to the points before starting (i.e make it low res then scale to high res)

"""

from pybricks.hubs import EV3Brick
from pybricks.ev3devices import (Motor, TouchSensor, ColorSensor,
                                 InfraredSensor, UltrasonicSensor, GyroSensor)
from pybricks.parameters import Port, Stop, Direction, Button, Color
from pybricks.tools import wait, StopWatch, DataLog
from pybricks.robotics import DriveBase
from pybricks.media.ev3dev import SoundFile, ImageFile
from _thread import start_new_thread
from pybricks.tools import wait

# NOTE: https://pybricks.com/ev3-micropython/ev3devices.html

class Consts:

    # Motor Ports
    x_axis = Port.D # Top Beam Left/Right
    y_axis = Port.A # Cart Forward/Back
    z_axis = Port.B # Plate Up/Down
    liquid = Port.C # Syringe Push Down

    x_touch = Port.S4
    y_touch = Port.S1

    x_end = 27 # Rotations
    y_end = 15 # Rotations


""" Global Variables """

ev3 = EV3Brick()
consts = Consts()

x_mtr = Motor(consts.x_axis)
y_mtr = Motor(consts.y_axis, positive_direction=Direction.COUNTERCLOCKWISE)
z_mtr = Motor(consts.z_axis)
s_mtr = Motor(consts.liquid)

x_sns = TouchSensor(consts.x_touch)
y_sns = TouchSensor(consts.y_touch)

# =========================
#     Helper Functions 
# =========================

def load_path(path_num: int):
    """Load a path file (e.g., paths/0.txt) and return list of (x,y) tuples."""
    filepath = "paths/{}.txt".format(path_num)
    points = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                x_str, y_str, z_str = line.split(",")
                points.append((float(x_str), float(y_str), bool(int(z_str))))
    except OSError:
        print("Could not open file:", filepath)
    return points


def reset_motor(mtr: Motor, sns: TouchSensor, power: int):
    """ Reset a motor to its zero position using a touch sensor """
    ev3.speaker.beep()
    mtr.dc(power)
    while not sns.pressed():
        wait(0.1)
    mtr.brake()
    ev3.speaker.beep()


def _move_to_end():
    """ (Debugging) Move both axes to their end positions. """
    x_mtr.run_angle(speed=500, rotation_angle=360*Consts.x_end, then=Stop.HOLD, wait=False)
    y_mtr.run_angle(speed=500, rotation_angle=360*Consts.y_end, then=Stop.HOLD, wait=True)


def go_to_relative(x: float, y: float, speed: int = 800):
    """ Move printer head to (x,y) normalized coord using RELATIVE movement. """
    global current_x, current_y

    dx = x - current_x
    dy = y - current_y

    # Convert to degrees
    x_degrees = int(dx * Consts.x_end * 360)
    y_degrees = int(dy * Consts.y_end * 360)

    max_degrees = max(abs(x_degrees), abs(y_degrees))
    x_speed = speed * abs(x_degrees / max_degrees) if max_degrees != 0 else speed 
    y_speed = speed * abs(y_degrees / max_degrees) if max_degrees != 0 else speed

    x_mtr.run_angle(x_speed, x_degrees, then=Stop.HOLD, wait=True)
    y_mtr.run_angle(y_speed, y_degrees, then=Stop.HOLD, wait=True)

    current_x, current_y = x, y


def plate_raise(sec=4):
     z_mtr.run_time(-400, 1000*sec)


def plate_lower(sec=4):
    z_mtr.run_time(400, 1000*sec)

def syringe_push(sec=20, power=100):
    # s_mtr.run_time(50, 1000*sec)

    ev3.speaker.beep()
    # s_mtr.dc(power)
    s_mtr.run(90)
    wait(1000*sec)
    s_mtr.brake()
    ev3.speaker.beep()

syringe_active = False

def syringe_push_from_path(path_num, total_deg=430):
    """
    Gradually push syringe according to drawing points.
    Pauses when syringe_active is False.
    """
    global syringe_active

    path = load_path(path_num)
    draw_points = [p for p in path if p[2]]
    num_draw_points = len(draw_points)
    deg_per_point = total_deg / num_draw_points
    syringe_progress = 0

    print("Total drawing points: {}, deg per point: {:.2f}".format(num_draw_points, deg_per_point))

    for i, (x, y, draw) in enumerate(path):
        # Wait until active
        while not syringe_active:
            wait(50)  # prevent blocking the CPU loop

        if draw:
            syringe_progress += deg_per_point
            s_mtr.run_target(100, syringe_progress, then=Stop.HOLD, wait=True)
        else:
            s_mtr.hold()
            
# =========================
#       Main Script
# =========================

#syringe_push()
#wait(1000000)

# # Reset Both X/Y Axes to (0,0)
plate_lower()
reset_motor(x_mtr, x_sns, -100)
reset_motor(y_mtr, y_sns, -100)

# # Track head position (normalized)
current_x, current_y = 0.0, 0.0

path_number = 2
path = load_path(path_number)
steps = 1 # Take every Nth point

start_new_thread(syringe_push_from_path, (path_number,))

is_drawing = False 
for i in range(0, len(path), steps):
    entry = path[i]
    need_to_draw = entry[2]

    if not is_drawing and need_to_draw:
        plate_raise()
        syringe_active = True   # resume
        is_drawing = True

    if is_drawing and not need_to_draw:
        plate_lower()
        syringe_active = False  # pasuse
        is_drawing = False

    p = (entry[0], entry[1])
    print("Going to: {}, {}".format(p[0], p[1]))
    go_to_relative(*p)

    # ev3.speaker.beep(); wait(100)
