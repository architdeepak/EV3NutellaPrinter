#!/usr/bin/env pybricks-micropython
"""Move cart and top gantry toward their home switches, then stop."""

from pybricks.ev3devices import Motor, TouchSensor
from pybricks.hubs import EV3Brick
from pybricks.parameters import Port, Direction
from pybricks.tools import StopWatch, wait


# Same hardware mapping and homing direction as the printer's original sequence.
HOME_SPEED = 600  # deg/s; a typical full-track move should take about 5 seconds.


def main():
    brick = EV3Brick()
    cart = Motor(Port.D)
    gantry = Motor(Port.A, positive_direction=Direction.COUNTERCLOCKWISE)
    cart_sensor = TouchSensor(Port.S4)
    gantry_sensor = TouchSensor(Port.S1)
    axes = (
        ("cart", cart, cart_sensor),
        ("top gantry", gantry, gantry_sensor),
    )
    clock = StopWatch()

    for name, motor, sensor in axes:
        if sensor.pressed():
            motor.brake()
            print(name, "already at home")
        else:
            motor.run(-HOME_SPEED)
            print(name, "moving toward touch sensor")

    remaining = [axis for axis in axes if not axis[2].pressed()]
    last_report = -1000
    try:
        while remaining:
            now = clock.time()
            for axis in remaining[:]:
                name, motor, sensor = axis
                if sensor.pressed():
                    motor.brake()
                    remaining.remove(axis)
                    brick.speaker.beep()
                    print(name, "home switch reached at", now, "ms; angle", motor.angle())
            if now - last_report >= 1000:
                print("homing", now, "ms", "cart", cart.angle(), "gantry", gantry.angle())
                last_report = now
            wait(10)
    finally:
        cart.brake()
        gantry.brake()

    brick.speaker.beep()
    brick.screen.clear()
    brick.screen.print("X/Y homed")
    print("Both home switches reached; motors stopped.")


main()
