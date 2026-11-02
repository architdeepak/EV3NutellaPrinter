#!/usr/bin/env pybricks-micropython
"""Move X/Y from midpoint to their switches while C dispenses, then stop."""

from pybricks.ev3devices import Motor, TouchSensor
from pybricks.hubs import EV3Brick
from pybricks.parameters import Port, Direction, Stop
from pybricks.tools import StopWatch, wait


HOME_SPEED = 600
X_SPAN_DEG = 9720
Y_SPAN_DEG = 5400
C_SPEED = 250
C_MAX_DELTA = 1800  # five measured 360-degree turns


def main():
    brick = EV3Brick()
    cart = Motor(Port.D)
    gantry = Motor(Port.A, positive_direction=Direction.COUNTERCLOCKWISE)
    syringe = Motor(Port.C)
    cart_sensor = TouchSensor(Port.S4)
    gantry_sensor = TouchSensor(Port.S1)
    axes = (("cart", cart, cart_sensor), ("top gantry", gantry, gantry_sensor))
    clock = StopWatch()
    syringe.control.limits(speed=800, actuation=100)

    def home_axes():
        remaining = [axis for axis in axes if not axis[2].pressed()]
        for name, motor, sensor in axes:
            if sensor.pressed():
                motor.brake()
                print(name, "already at home")
            else:
                motor.run(-HOME_SPEED)
                print(name, "moving toward home switch")
        last_report = -1000
        while remaining:
            now = clock.time()
            for axis in remaining[:]:
                name, motor, sensor = axis
                if sensor.pressed():
                    motor.brake()
                    remaining.remove(axis)
                    brick.speaker.beep()
                    print(name, "home reached at", now, "ms; angle", motor.angle())
            if now - last_report >= 1000:
                print("homing", now, "ms; cart", cart.angle(), "gantry", gantry.angle(),
                      "C", syringe.angle())
                last_report = now
            wait(10)

    try:
        syringe.hold()
        # Establish physical home references before using the known travel spans.
        home_axes()
        cart.reset_angle(0)
        gantry.reset_angle(0)
        x_mid = X_SPAN_DEG // 2
        y_mid = Y_SPAN_DEG // 2
        print("Moving X/Y to midpoint:", x_mid, y_mid, "degrees")
        cart.run_angle(HOME_SPEED, x_mid, then=Stop.HOLD, wait=False)
        gantry.run_angle(HOME_SPEED, y_mid, then=Stop.HOLD, wait=False)
        while not cart.control.done() or not gantry.control.done():
            print("midpoint", clock.time(), "ms; X", cart.angle(), "Y", gantry.angle())
            wait(500)
        cart.hold()
        gantry.hold()
        print("At midpoint; dispensing C while X/Y return to touch sensors")

        c_start = syringe.angle()
        syringe.run(C_SPEED)
        home_remaining = [axis for axis in axes if not axis[2].pressed()]
        for name, motor, sensor in axes:
            if sensor.pressed():
                motor.brake()
                home_remaining = [axis for axis in home_remaining if axis[0] != name]
            else:
                motor.run(-HOME_SPEED)

        last_report = -1000
        while home_remaining:
            now = clock.time()
            c_delta = syringe.angle() - c_start
            if c_delta >= C_MAX_DELTA and not syringe.control.done():
                syringe.hold()
                print("C five-turn limit reached; keeping X/Y homing")
            for axis in home_remaining[:]:
                name, motor, sensor = axis
                if sensor.pressed():
                    motor.brake()
                    home_remaining.remove(axis)
                    brick.speaker.beep()
                    print(name, "home reached at", now, "ms; angle", motor.angle())
            if now - last_report >= 1000:
                print("dispense/homing", now, "ms; C delta", syringe.angle() - c_start,
                      "C speed", syringe.speed(), "X", cart.angle(), "Y", gantry.angle())
                last_report = now
            wait(10)

        syringe.brake()
        print("C stopped at delta", syringe.angle() - c_start,
              "degrees (", (syringe.angle() - c_start) / 360, "turns)")
    finally:
        cart.brake()
        gantry.brake()
        syringe.brake()

    brick.speaker.beep()
    brick.screen.clear()
    brick.screen.print("Test complete")
    print("Sequence complete; all motors stopped.")


main()
