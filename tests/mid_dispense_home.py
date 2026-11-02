#!/usr/bin/env pybricks-micropython
"""Move X/Y to midpoint, make a short C dispense during a short X move, rehome."""

from pybricks.ev3devices import Motor, TouchSensor
from pybricks.hubs import EV3Brick
from pybricks.parameters import Port, Direction, Stop
from pybricks.tools import StopWatch, wait


HOME_SPEED = 600
X_SPAN_DEG = 9720
Y_SPAN_DEG = 5400
X_SHORT_MOVE_DEG = 120
C_PUSH_SPEED = 800
C_PUSH_MS = 250


def main():
    brick = EV3Brick()
    cart = Motor(Port.D)
    gantry = Motor(Port.A, positive_direction=Direction.COUNTERCLOCKWISE)
    syringe = Motor(Port.C)
    cart_sensor = TouchSensor(Port.S4)
    gantry_sensor = TouchSensor(Port.S1)
    axes = (("cart", cart, cart_sensor), ("top gantry", gantry, gantry_sensor))
    clock = StopWatch()

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
                print("homing", now, "ms cart", cart.angle(), "gantry", gantry.angle())
                last_report = now
            wait(10)

    try:
        syringe.hold()
        # Ensure the encoders are referenced at the physical switches before
        # using the known travel spans to calculate each midpoint.
        home_axes()
        cart.reset_angle(0)
        gantry.reset_angle(0)
        x_mid = X_SPAN_DEG // 2
        y_mid = Y_SPAN_DEG // 2
        print("Moving to midpoint: cart", x_mid, "deg; gantry", y_mid, "deg")
        cart.run_angle(HOME_SPEED, x_mid, then=Stop.HOLD, wait=False)
        gantry.run_angle(HOME_SPEED, y_mid, then=Stop.HOLD, wait=False)
        while not cart.control.done() or not gantry.control.done():
            print("midpoint move", clock.time(), "ms cart", cart.angle(), "gantry", gantry.angle())
            wait(250)
        cart.hold()
        gantry.hold()
        print("At midpoint; short dispense and cart move starting")

        c_start = syringe.angle()
        x_start = cart.angle()
        syringe.run_time(C_PUSH_SPEED, C_PUSH_MS, then=Stop.HOLD, wait=False)
        cart.run_angle(HOME_SPEED, X_SHORT_MOVE_DEG, then=Stop.HOLD, wait=False)
        while not syringe.control.done() or not cart.control.done():
            print("short dispense", clock.time(), "ms C", syringe.angle(), "X", cart.angle())
            wait(50)
        syringe.hold()
        cart.hold()
        print("Dispense ended: C delta", syringe.angle() - c_start,
              "deg; cart delta", cart.angle() - x_start, "deg")

        print("Returning X/Y to touch sensors")
        home_axes()
    finally:
        cart.brake()
        gantry.brake()
        syringe.brake()

    brick.speaker.beep()
    brick.screen.clear()
    brick.screen.print("X/Y homed")
    print("Sequence complete; all motors stopped.")


main()
