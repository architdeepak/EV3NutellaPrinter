# Historical baseline and dispensing notes

This records the earlier cleanup. The current active layout and wiring are in
[the project README](../../README.md). The original movement helpers remain;
main.py has since had unused code removed and now selects path 5. Archive paths
and physical-state descriptions below refer to that earlier snapshot.

## Preserve the original movement

The owner reports that the original plate movement and X/Y drawing were good
and accurate. They are the baseline for further work. Keep their port mapping,
motor directions, spans, speed calculation, sequencing, and timed plate moves.
Develop syringe dispensing around this flow. Do not substitute slow diagnostic
pulses, output caps, encoder-position lift targets, or a new X/Y controller for
these commands based on the mixed diagnostic results.

`main.py` source matches cloned commit `8338420`; the matching
file was copied to `/home/robot/EV3NutellaPrinter/main.py` on the brick. The
desktop drawing app and original experimental scripts are also unchanged.

## What the history establishes

- `80094e3` (2025-09-21), **V1 working - need to add syringe**: contains the
  original X/Y motion, touch-sensor homing, and plate helpers.
- `425be69` (2025-10-03), **syringe stuff**: disables the standalone syringe
  experiment at startup, changes the selected path, and adds `syringetest.py`.
- `8338420` (2025-10-14), **more changes/improvement - syringepush still not
  working**: adds the bread image, drawing background, corner test, more paths,
  and syringe experiments. It does not change `main.py` from `425be69`.

Comparing the working-V1 commit with the cloned commit shows that `Consts`,
`reset_motor`, `go_to_relative`, `plate_raise`, and `plate_lower` retain the same
code. The differences in `main.py` are whitespace, commenting out the startup
syringe experiment, and choosing path 1 rather than path 3. The working-V1
snapshot also contains a long startup syringe-test wait, so it should not be
blindly run as the drawing entry point. Use the cloned `main.py` baseline.

## Motors, switches, and command meanings

- **D / X**: top nozzle carriage, default positive motor direction. Full
  normalized travel is 27 motor rotations = 9,720 motor degrees.
- **A / Y**: bottom cart, `Direction.COUNTERCLOCKWISE` positive. Full normalized
  travel is 15 motor rotations = 5,400 motor degrees.
- **B / plate**: raise with `run_time(-400, 4000)`; lower with
  `run_time(400, 4000)`. Both use the motor's default control limits.
- **C / syringe**: motor winds the geared string drive to push the plunger.
  It is initialized by `main.py` but never commanded by its active draw loop.
- **S4**: X/top track home switch. **S1**: Y/bottom cart home switch.

`dc(-100)` in the original homing helper means negative 100 percent duty cycle.
It is different from `run(-100)`, which requests -100 degrees per second.
`run_time(400, 4000)` requests 400 degrees per second for 4,000 milliseconds;
400 is a speed, not a power percentage. The original program does not add a
60 percent actuation cap. Preserve these distinctions when diagnosing motors.

Plate rotation is time based, not a fixed encoder stroke. At 400 degrees/second,
four seconds nominally corresponds to 1,600 degrees (4.44 motor rotations).
Acceleration, load, and deceleration affect the actual result. Latest successful
tests recorded roughly 1,527-1,560 degrees (about 4.24-4.33 rotations). Those
readings corroborate the original command; they are not a new absolute target.
The early 1,260-degree observation came from a different start/assembly state
and should not replace the four-second command.

## Complete drawing flow

1. On the laptop, `draw.py` records normalized coordinates. X is mouse X divided
   by canvas width. Y is `1 - mouse Y / canvas height`.
2. Left-drag records `x,y,1` (draw). Right-click records `x,y,0` (travel).
   Releasing the mouse does not add a stop marker. Right-click at a new stroke
   start before dragging there.
3. Save writes the next numbered file in `paths/`. The selected file in
   `main.py` is controlled by `path_number`, currently 1. The app and robot
   controller run separately; there is no automatic save/upload/run pipeline.
4. `main.py` initializes four motors and two switches, lowers the plate for
   four seconds, then homes X and Y in sequence using `dc(-100)` until their
   respective switches are pressed. It brakes each motor at the switch.
5. It sets the logical normalized position to `(0, 0)`. The original program
   does not call `reset_angle(0)` after homing; relative moves do not require
   the raw motor encoder to read zero at this point.
6. For each path row, it raises the plate on a transition into drawing and
   lowers it on a transition into travel, before moving to that row's X/Y.
7. It computes normalized deltas from the previous requested point:
   `x_degrees = int(dx * 9720)` and `y_degrees = int(dy * 5400)`.
   The larger delta gets the default 800 degrees/second; the other gets the
   same speed multiplied by its relative motor-degree delta. It runs **X to
   completion, then Y to completion**, with `Stop.HOLD`, and updates the logical
   coordinates. This is the original sequencing and remains unchanged.
8. It visits every saved point (`steps = 1`). Plate moves depend on flags in
   the file. The program has no extra unconditional lowering at the end; a
   path ending in a draw point leaves the plate raised.

Pybricks performs feedback inside the motor position commands. The original
program's separate logical coordinates represent requested positions; they do
not measure string tension, actual nozzle flow, gear slip, or plunger position.
The original code comments mention drift, but the owner's working calibration
is retained while dispensing is addressed.

## What remains to fix in dispensing

The physical nozzle is attached to the syringe barrel. The dispensing motor
pulls a string through gears to force the plunger down; the plate lift controls
the nozzle-to-bread gap. These are different mechanisms. The plunger is manually
reset with its two beams vertical and the upper gray cylinders at the yellow
marker. Reproducing that reference and winding arrangement improves consistency.

The original files contain three dispensing approaches:

- `main.py` has a helper that runs the syringe at 90 degrees/second for 20
  seconds by default (nominally 1,800 degrees / 5 rotations). Its call is
  commented out, so it is not a working automatic dispensing setting.
- `syringetest.py` uses path 2 and a separate thread, dividing a total 430 motor
  degrees (1.19 rotations) over draw points. Each target uses 100 degrees/second.
- `syringetest2.py` uses path 3, similar 430-degree targets, a lock around a
  boolean active flag, debug messages, and an added 50 ms X/Y-loop delay.

Neither experiment shares the current X/Y path index with the syringe thread.
The thread can consume points at its own pace while X/Y is still moving; a
boolean active flag only pauses/resumes it. The lock protects that boolean but
does not synchronize path progress. In both experiments the plate is lowered
before the syringe-active flag is cleared, allowing dispensing during that
lowering interval. The syringe targets are absolute angles that assume motor
zero corresponds to the intended plunger reference; the experiments do not
establish that physical reference through manual alignment and priming.
Thus 430 degrees and 100 degrees/second are
experimental parameters, not established material-flow calibration.

Future dispensing changes should start with a repeatable manual plunger reset
and observed priming to take up slack, establish usable motor rotation/flow,
then tie dispensing progress to the existing drawing loop's progress. Keep
travel and plate transitions free of commanded additional syringe advance.
Motor encoders alone cannot compensate for slipping string or detect actual
flow. A dispensing rate based on drawing distance would also avoid making
material quantity depend on how densely the mouse recorded points. This is
future syringe work; it has not been inserted into the preserved controller.

## Current physical state and local archive

Tests are stopped. The last successful command pair lowered about +1550 degrees
and raised about -1559 degrees on C. The plate ended near its starting raised
position. The final device read reported C and D stopped at speed zero. The
physical lift is still on C for diagnostics, while the original code requires
B=plate and C=syringe. Restore the original wiring before starting the full
program; only C/D motors were detected in the final inventory.

The added alternate controller, calibration tools, tests, and superseded setup
documents are in `.local/archive/controller-rewrite-20261024/`. The photo zip
and extracted photos are in `.local/printer-photos/`. These local archives are
ignored by Git. The original scripts, saved paths, image, and Git history are
preserved. No motor tests form part of this cleanup.
