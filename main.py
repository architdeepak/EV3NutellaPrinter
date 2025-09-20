#!/usr/bin/env pybricks-micropython
import sys
from pybricks.hubs import EV3Brick
from pybricks.ev3devices import (Motor, TouchSensor, ColorSensor,
                                 InfraredSensor, UltrasonicSensor, GyroSensor)
from pybricks.parameters import Port, Stop, Direction, Button, Color
from pybricks.tools import wait, StopWatch, DataLog
from pybricks.robotics import DriveBase
from pybricks.media.ev3dev import SoundFile, ImageFile


# This program requires LEGO EV3 MicroPython v2.0 or higher.
# Click "Open user guide" on the EV3 extension tab for more information.


# Create your objects here.
ev3dev = EV3Brick()
left_motor = Motor(Port.D)
forward_motor = Motor(Port.A)
upper_motor = Motor(Port.B)
down_motor = Motor(Port.C)

ev3dev.speaker.beep()


def move_forward(speed, target):
    forward_motor.run_target(speed, target)
def move_backward(speed, target):
    forward_motor.run_target(-1*speed, -1*target)
def move_left(speed, target):
    left_motor.run_target(-1*speed, -1*target)
def move_right(speed, target):
    left_motor.run_target(speed, target)
def down_syringe(speed, target):
    down_motor.run_target(speed, target)
def up_platform(speed, target):
    upper_motor.run_target(speed, target)

"""
lef
"""
SPEED = 500


def move_to_position(x, y):
    move_forward(500, x)
    move_right(500, y)

print("FORWARD MOTOR ANGLE UP",file=sys.stderr)
forward_motor.run_until_stalled(SPEED, then=Stop.COAST, duty_limit=None)
angle = forward_motor.angle()

print("FORWARD MOTOR ANGLE UP",file=sys.stderr)
forward_motor.run_until_stalled(-1*SPEED, then=Stop.COAST, duty_limit=None)
angle = forward_motor.angle()
print("FORWARD MOTOR ANGLE BOTTOM",file=sys.stderr)