# EV3 Nutella Printer

A laptop and LEGO EV3 that draw with Nutella. Run `python main.py` to print the latest drawing in `paths/` (currently 12). Use `python main.py --draw` to open the editor.

## Continuous run

1. Leave the pusher near the chocolate with the mechanism ready. Its current
   position becomes this run's relative encoder zero; it is not the physical top.
2. The brick beeps. Only C moves, in short full-output forward nudges. Press DOWN
   when chocolate first emerges. UP cancels this stage.
3. C stops, the brick beeps, and C briefly reverses. The actual encoder movement
   is recorded. There is a ten-second pause with one beep each second.
4. The plate lowers, X homes to S4, then Y homes to S1.
5. The saved drawing runs. Original integer normalized coordinates, X-then-Y
   ordering, home commands and plate timings are preserved. X/Y speed is 1200
   degrees/second rather than the original 800, with acceleration 2400 deg/s/s.
   These are requested limits; actual achievable speed depends on the motors/load.
6. C runs in speed mode while a drawing axis moves, using axis speed, drawing
   distance, and observed C lag. It stops for travel/plate moves and briefly
   reverses 30 degrees between strokes at up to 800 deg/s. The measured reversal
   is taken up at the next stroke. End-of-drawing pullback is 60 degrees.
   Position-controlled pullbacks have a 600 ms completion window; achieved
   travel is logged and may be less than requested under load.
7. At completion all motors brake. DOWN stops the run after flow setup.

C stall reports, small endpoint errors, and invented syringe travel limits no
longer stop or hold up X/Y. The controller does not wait for C to reach a drawing
position. C stalling remains visible in the logs. A stopped syringe can therefore
produce a missing line while the drawing continues. No sensor detects actual
flow, force, slipping string, or the physical end of syringe travel. The operator
must watch the mechanism and press DOWN if needed. Reverse can release string
tension but does not prove that the string drive pulls the plunger upward.

## Calibration

The working estimate is the owner's confirmed 157 degrees net syringe advance
for the demonstrated 1080-degree Y line. That is 785 C degrees per normalized
axis distance, or about 29.1 C degrees/second at 200 Y degrees/second. The hand
movement and cart movement were recorded at different times, so this is an
owner-associated amount/line pairing, not a simultaneous flow-rate measurement.
The 100 mL syringe capacity and approximate diameter do not establish exact
volume per degree. String winding radius and tension can change the relationship.
The earlier 706-degree drawing trial and fixed 455-degree startup are superseded.

The screen's bread image is a placement guide, not calibrated centimetres. Full
normalized width maps to 27 X turns (9720 degrees); height maps to 15 Y turns
(5400 degrees). Physical X/Y spans still need ruler measurements for cm scale.

## Wiring and original baseline

- A: bottom cart Y, counterclockwise-positive.
- B: medium plate-lift motor.
- C: syringe drive.
- D: upper X carriage.
- S1: cart home switch. S4: upper carriage home switch.

Baseline is Git commit 8338420. Homing remains dc(-100) to each switch. Plate up
is -400 degrees/second for four seconds; down is +400 for four seconds. X/Y moves
use the original integer relative deltas and proportional speed calculation.
The old origin's active drawing loop did not dispense automatically.

## Logs and checks

Every run creates `tests/results/print-N.csv` on the brick. The laptop downloads
it as `tests/results/path-DRAW-print-N.csv`, including on an interrupted run.
Logs contain original source points, normalized requested positions, planned
axis deltas/speeds, command events, timestamps, actual angle/speed/stall status for
all four motors, calculated C feed target and speed, short-nudge actual travel,
flow confirmation, countdown/homing/plate phases, PWM duty when readable, battery
voltage when readable, and the final outcome. Normal samples are approximately
50 ms plus forced command/event rows; actual sample rate depends on brick load.
PWM duty is not a force measurement. Source points are copied into the log, so
one log can be traced to its drawing even if saved files later change.

Run `python -m unittest discover -s tests -p 'test_*.py' -v` for hardware-free
checks. The suite compares every saved-path motor command against the original
geometry, verifies the observed-flow/reverse/countdown/home ordering, verifies
DOWN/UP stops and motor braking, and proves a stalled C does not gate completion
of the XY drawing. Tests do not prove loaded food flow or print quality.
The previous controller and tests are preserved in
`tests/archive/before-continuous-rebuild/`. `dispensing.py` retains old diagnostic
classes for reference, but the main drawing loop no longer uses those controllers.

The laptop requires Pillow and Paramiko (`requirements.txt`). SSH uses the
verified known-host entry, robot/maker by default, and tries ev3dev.local then
10.0.0.223. EV3_HOST, EV3_USER and EV3_PASSWORD override those defaults.

Telemetry timing: source/point/command rows are metadata-only (motor fields blank).
Full motor samples and axis-end rows carry actual encoder data. Electrical
readings are cached for one second; their repeated values are not fresh samples.
Console summaries are throttled and buffers flush periodically. Axis commands
are logged before movement starts so logging cannot postpone the first feed
update until after a short move has already ended.

First-line take-up: C angle is captured immediately when DOWN marks flow. At
the end of the manual-pullback pause, the encoder difference is recorded. Just
before the first drawing axis starts, C is commanded forward by the current
difference to that flow mark at 800 deg/s with 100% output available. Actual
restoration is logged; a stalled motor may achieve less than requested. This
cannot measure plunger movement that does not rotate the motor/connected gears.
The take-up completion window grows with the measured distance, rather than
using the fixed short reversal window.

Latest loaded-test adjustment: drawing feed is 1.10 times the manual-line base
ratio, and the first-line restore includes an additional 30 degrees beyond the
measured pullback. These are trial increases, not new volume measurements.
Full output availability remains 100%; physical maximum torque is unchanged.

Current stroke-start rule (supersedes the previous first-line-only boost):
every travel-to-draw transition receives measured reverse take-up plus 45
additional degrees at 800 deg/s before XY drawing starts. This corresponds
to the stroke after a red travel marker, not every mouse sample. Drawing feed
is now 1.20 times the manual-line base ratio (9.1% above the previous 1.10
trial). C proportional position gain is 600 and output availability remains
100%; higher requested feed does not prove higher achieved flow or force.
