#!/usr/bin/env pybricks-micropython

"""
Script: Surprise for Squirrel (Stable + Debug Text)
- Prints clear syringe and plate actions
- No f-strings (uses .format for compatibility)
- Ensures syringe unholds before resuming
"""

from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor, TouchSensor
from pybricks.parameters import Port, Stop, Direction
from pybricks.tools import wait
from _thread import start_new_thread, allocate_lock


# =========================
#     Constants
# =========================

class Consts:
    x_axis = Port.D
    y_axis = Port.A
    z_axis = Port.B
    liquid = Port.C

    x_touch = Port.S4
    y_touch = Port.S1

    x_end = 27
    y_end = 15


# =========================
#     Globals
# =========================

ev3 = EV3Brick()
consts = Consts()

x_mtr = Motor(consts.x_axis)
y_mtr = Motor(consts.y_axis, positive_direction=Direction.COUNTERCLOCKWISE)
z_mtr = Motor(consts.z_axis)
s_mtr = Motor(consts.liquid)

x_sns = TouchSensor(consts.x_touch)
y_sns = TouchSensor(consts.y_touch)

# State
current_x, current_y = 0.0, 0.0
syringe_active = False
syringe_lock = allocate_lock()


# =========================
#     Helper Functions
# =========================

def load_path(path_num: int):
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
        print("Could not open file: {}".format(filepath))
    return points


def reset_motor(mtr: Motor, sns: TouchSensor, power: int, name: str):
    """Reset motor using touch sensor."""
    print("Resetting motor...")
    ev3.speaker.beep()
    mtr.dc(power)
    while not sns.pressed():
        wait(1)
    mtr.brake()
    print("motor reset complete.")
    ev3.speaker.beep()


def go_to_relative(x: float, y: float, speed: int = 800):
    """Move head to relative (x, y)."""
    global current_x, current_y
    dx = x - current_x
    dy = y - current_y

    x_degrees = int(dx * Consts.x_end * 360)
    y_degrees = int(dy * Consts.y_end * 360)

    max_deg = max(abs(x_degrees), abs(y_degrees))
    if max_deg == 0:
        return

    x_speed = speed * abs(x_degrees / max_deg)
    y_speed = speed * abs(y_degrees / max_deg)

    x_mtr.run_angle(x_speed, x_degrees, then=Stop.HOLD, wait=True)
    y_mtr.run_angle(y_speed, y_degrees, then=Stop.HOLD, wait=True)

    current_x, current_y = x, y


def plate_raise(sec=4):
    print("Going up (plate)")
    z_mtr.run_time(-400, 1000 * sec, then=Stop.HOLD, wait=True)
    print("Plate raised")


def plate_lower(sec=4):
    print("Going down (plate)")
    z_mtr.run_time(400, 1000 * sec, then=Stop.HOLD, wait=True)
    print("Plate lowered")


def set_syringe_state(state: bool):
    global syringe_active
    syringe_lock.acquire()
    syringe_active = state
    syringe_lock.release()


def get_syringe_state() -> bool:
    syringe_lock.acquire()
    state = syringe_active
    syringe_lock.release()
    return state


def syringe_push_from_path(path_num, total_deg=430):
    """Push syringe gradually while drawing."""
    path = load_path(path_num)
    draw_points = [p for p in path if p[2]]
    num_draw_points = len(draw_points)
    if num_draw_points == 0:
        print("No drawing points found.")
        return

    deg_per_point = total_deg / num_draw_points
    syringe_progress = 0

    print("Total drawing points: {}, deg per point: {:.2f}".format(num_draw_points, deg_per_point))

    for (x, y, draw) in path:
        while not get_syringe_state():
            print("Syringe paused - holding.")
            s_mtr.brake()
            wait(50)

        if draw:
            syringe_progress += deg_per_point
            # use .format for MicroPython
            print("Syringe pushing to {:.2f}°".format(syringe_progress))
            s_mtr.stop()  # unhold before next push
            s_mtr.run_target(100, syringe_progress, then=Stop.HOLD, wait=True)
        else:
            print("Stopping syringe (not drawing)")
            s_mtr.brake()
            wait(10)


# =========================
#       Main Script
# =========================

plate_lower()
reset_motor(x_mtr, x_sns, -100, "X")
reset_motor(y_mtr, y_sns, -100, "Y")

path_number = 3
path = load_path(path_number)
steps = 1

# Start syringe thread
start_new_thread(syringe_push_from_path, (path_number,))

is_drawing = False
for i in range(0, len(path), steps):
    entry = path[i]
    need_to_draw = entry[2]

    if not is_drawing and need_to_draw:
        plate_raise()
        print("Resuming syringe")
        set_syringe_state(True)
        is_drawing = True

    if is_drawing and not need_to_draw:
        plate_lower()
        print("Pausing syringe")
        set_syringe_state(False)
        is_drawing = False

    p = (entry[0], entry[1])
    print("Moving to: ({:.3f}, {:.3f})".format(p[0], p[1]))
    go_to_relative(*p)
    wait(50)