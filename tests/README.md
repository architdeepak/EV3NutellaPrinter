# Tests and reference material

The active printer uses `../main.py`, `../desktop.py`, `../dispensing.py`, `../draw.py`, `../bread.png`, and
`../paths/`. This directory contains the remaining experimental and historical
material so it does not clutter the active program.

- `legacy/rangetest.py`: original X/Y corner test.
- `legacy/syringetest.py`, `legacy/syringetest2.py`: original syringe-thread
  experiments. Their independent path cursors do not synchronize syringe
  progress with X/Y, so they are references rather than the printer entry point.
- `legacy/paths/0.txt` through `4.txt`: original examples and the earlier drawing.
  The legacy syringe scripts expect their `paths/` relative to the working
  directory, so their original layout is preserved here.
- `reference/working-baseline.md`: history and original movement explanation.
- `reference/mechanics.md`: observations from the supplied mechanical photos.
- `reference/hardware-test-log.md`: hardware observations; older entries are
  historical snapshots, not the current wiring or program configuration.
- `reference/photos/`: supplied photo zip, extracted photos, and inspection
  crops. Large local reference assets are ignored by Git.
- `archive/controller-rewrite-20261024/`: the previous added controller,
  calibration tools, their software tests, and superseded notes. It is ignored
  by Git and excluded from EV3 uploads.
- `results/`: reserved for measured motor-time/rotation logs; ignored by Git.
- `syringe_timing.py`: supervised C-only measurement, logging elapsed time,
  encoder angle, rotations, speed, and stall status. Its timed-run limit is not
  a full-stroke or material-dose calibration.
- `syringe_bench.py`, `run_syringe_bench.py`: actual dry C-only position/feed
  benchmark. Starts at a manually confirmed top and logs angle, speed, reported
  PWM duty and battery voltage. X/Y/Z are not initialized. The laptop runner
  uploads it and retrieves the CSV. A `--step START DEGREES` measurement restores
  an explicitly known prior coordinate; it is only valid if the mechanism has
  not been moved since that recorded stop.
- `test_printing.py`: desktop checks with simulated motors; full trace/print
  startup and priming, original X/Y and plate regression, stroke limits, actual
  encoder-linked feed, travel, and stopping. Run from the project root with
  `python -m unittest discover -s tests -p test_printing.py -v`.

Several legacy scripts start motors as soon as they run. They are not launched
by the active VS Code configuration. No calibration or experiment runs as part
of ordinary repository checks.

- `test_desktop_flow.py`: Save & Print uploads/verifies the newly saved file,
  starts the automatic brick command, and does nothing if drawing is cancelled.
