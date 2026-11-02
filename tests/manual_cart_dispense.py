#!/usr/bin/env pybricks-micropython
"""Full-power C feed while the manually positioned cart slowly homes."""

from pybricks.ev3devices import Motor, TouchSensor
from pybricks.hubs import EV3Brick
from pybricks.parameters import Port, Direction
from pybricks.tools import StopWatch, wait


C_MAX_DELTA = 1800       # five measured turns, the syringe's full-stroke estimate
C_POWER = 100            # full DC duty for maximum available push
CART_SPEED = 250         # deg/s toward its home touch sensor
CART_TRAVEL_LIMIT = 9720 # stop if the switch fails before a full nominal track span


def main():
    brick = EV3Brick()
    cart = Motor(Port.A, positive_direction=Direction.COUNTERCLOCKWISE)
    syringe = Motor(Port.C)
    cart_sensor = TouchSensor(Port.S1)
    clock = StopWatch()
    cart_start = cart.angle()
    c_start = syringe.angle()
    c_limited = False

    try:
        if cart_sensor.pressed():
            print("Cart touch sensor is already pressed; nothing moved.")
            return

        syringe.dc(C_POWER)
        cart.run(-CART_SPEED)
        print("Running: syringe full power; cart toward touch sensor at",
              CART_SPEED, "deg/s")
        last_report = -1000
        while not cart_sensor.pressed():
            now = clock.time()
            c_delta = syringe.angle() - c_start
            cart_delta = cart.angle() - cart_start

            if c_delta >= C_MAX_DELTA and not c_limited:
                syringe.brake()
                c_limited = True
                print("Syringe reached five-turn travel limit; cart continues to sensor")

            if abs(cart_delta) >= CART_TRAVEL_LIMIT:
                print("Cart travel limit reached before touch sensor; stopping")
                break

            if now - last_report >= 250:
                print("RUN", now, "ms; C delta", c_delta, "deg; C speed",
                      syringe.speed(), "; cart delta", cart_delta,
                      "deg; cart speed", cart.speed())
                last_report = now
            wait(10)

        print("RESULT C delta", syringe.angle() - c_start,
              "deg; cart delta", cart.angle() - cart_start,
              "deg; switch", cart_sensor.pressed())
    finally:
        cart.brake()
        syringe.brake()
    print("Both motors stopped.")


main()
