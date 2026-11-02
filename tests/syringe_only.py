from pybricks.ev3devices import Motor
from pybricks.hubs import EV3Brick
from pybricks.parameters import Port, Button
from pybricks.tools import wait, StopWatch

brick = EV3Brick()
motor = Motor(Port.C)
motor.reset_angle(0)
clock = StopWatch()
brick.screen.clear()
brick.screen.print("C forward; DOWN stops")
while Button.DOWN in brick.buttons.pressed():
    wait(20)
brick.speaker.beep()
motor.dc(100)
try:
    while Button.DOWN not in brick.buttons.pressed():
        if clock.time() >= 1000:
            print("SYRINGE ms={} angle={} speed={}".format(clock.time(), motor.angle(), motor.speed()))
            clock.reset()
        wait(20)
finally:
    motor.brake()
    print("SYRINGE STOP angle={}".format(motor.angle()))
