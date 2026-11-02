# Hardware observations - 2026-10-24

Hardware tests are stopped. This cleanup did not run motors. The original
movement settings remain the baseline; see [the program flow](working-baseline.md).

## Original wiring and initial checks

Initial inventory identified A large/cart, B medium/plate lift, C large/syringe,
D large/top carriage, and touch sensors on S1/S4. The owner pressed both touch
sensors while their outputs were monitored; S1 and S4 both registered presses
and releases. X and Y later reached their home switches and moved away, which
the owner confirmed. This was a homing check, not a complete drawing accuracy
retest. The owner's previous successful X/Y drawing remains the baseline.

The brick runs EV3 MicroPython and is reachable over Wi-Fi SSH at
`robot@ev3dev.local`. The laptop has the EV3 extensions and drawing dependencies.
The battery initially reported low voltage, about 6.48 V; after the owner
connected the wall charger a later reading was about 6.95 V. This was not a
full-charge determination.

## Plate movement

The lift was moved between ports while troubleshooting and is currently on C.
Some short, slower position-target tests stalled; motor movement succeeded
with the gears removed and also after reconnection. Those mixed observations
do not establish a single cause for the earlier failures.

Returning to the original timed commands produced successful full movement:

- Up: `run_time(-400, 4000)`; successful later runs measured around -1560 degrees.
- Down: `run_time(400, 4000)`; one successful return measured +1527 degrees.
- Latest complete down/up cycle: +1550 degrees down, then -1559 degrees up.
- Two additional supervised 200 ms upward pulses moved -39 and -38 degrees
  before that final down/up cycle.

The owner confirmed that the original upward command lifted the plate. The
latest cycle ended near its starting raised position, with motors stopped.
Physical position can change if the mechanism is subsequently moved manually.

An earlier lift stopped around -1262 degrees from its particular starting
position; a +1262-degree position-target return completed around +1260 degrees.
That early result is not a reliable general stroke calibration. The later
successful original-command runs show why replacing the timed commands with
a fixed 1260-degree target would have been premature. Preserve the original
400 degrees/second, four-second plate commands.

## Current wiring and limits of what was established

The last read-only inventory detected a medium lift motor on C and a large
motor on D. Both had speed zero and no running state. A/B motors were absent.
The original main program expects A=cart, B=plate, C=syringe, D=top carriage;
restore those connections before running the full controller.

No loaded syringe/flow test has been completed. The 430-degree total in the
syringe experiments is a code parameter, not a measured successful dispensing
stroke. Full drawing with extrusion has not been established in this session.

The detailed troubleshooting record and superseded controller are preserved
locally under `.local/archive/controller-rewrite-20261024/`, including
`docs/hardware-test-log-full.md`. The active `main.py` on laptop and brick has
MD5 `cb0e45f8bf454e71de9ac2bd289a9f20` and matches the cloned original source.

## Later full-system and syringe checks

After wiring was restored, the brick detected A/C/D large motors, B medium,
and touch sensors S1/S4. The original main program reached drawing movement;
the owner reported that it looked normal except for the stationary syringe
pusher. That pusher was inactive because main.py never commanded it. The trace
was interrupted to open the laptop drawing app, and all four motors then
reported zero speed. The latest saved drawing is now paths/5.txt (303 points).

Subsequent C-only checks recorded: +80 degrees in a one-second request at
90 degrees/second; another +96 degrees before a stall in a longer 90-degree/
second request; +46 degrees before stall detection during a short 720-degree/
second request; and +66 degrees during a five-second 720-degree/second request
that stopped after two seconds with no further encoder progress. Requested
speed and actual shaft speed are different measurements. These results do not
establish how far the plunger moved or its full travel.

The owner then stopped testing and requested a manual reset followed by a new
high-speed timed measurement with halfway/bottom observations. No further
motor movement is authorized until the owner explicitly says to start.
Historical controller/notes are now under tests/archive/; photos are under
tests/reference/photos/. Main.py has only been cleaned, retaining the original
movement helpers and selecting the user's latest drawing, path 5.

## Encoder-linked dispensing integration verified

The active program now uses main.py plus dispensing.py. Thirteen desktop
regression/integration checks passed, including full trace and print/prime
flows with simulated hardware, original X/Y commands for all 303 path-5 points,
original plate +/-400 for 4000 ms, no travel extrusion, encoder-linked C feed,
remaining-stroke budgeting, timeout braking, and operator stop.

Both modules and path 5 were uploaded to the EV3; SHA256 hashes matched the
laptop. Actual EV3 MicroPython imported both modules and all required hardware
APIs without running main or constructing motors. A separate stationary C
configuration check returned factory limits (800,1600,100) and print limits
(720,1600,100). Both switches read released. A/C/D large and B medium motors
were detected stopped; the battery read about 7.66 V. These checks did not move
motors. Actual loaded dispensing and final line quality remain to be tested.
