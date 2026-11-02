"""Path validation and C feed linked to the original sequential X/Y movement."""


def seek_flow(motor, buttons, down, up, clock, wait, log, limit, speed=90):
    """Advance until the operator sees flow and presses DOWN; UP cancels."""
    began = clock()
    stalled_since = None
    try:
        # A held button must not be mistaken for a fresh flow confirmation.
        while buttons():
            if up in buttons():
                raise RuntimeError('Flow check cancelled by operator')
            if clock()-began > 120000:
                raise RuntimeError('Flow check timed out waiting for button release')
            wait(20)
        motor.run(speed)
        while True:
            now = clock()
            pressed = buttons()
            if up in pressed:
                raise RuntimeError('Flow check cancelled by operator')
            if down in pressed:
                motor.hold()
                position = motor.angle()
                log('flow-confirmed', position)
                # DOWN is the normal stop button after this stage; consume release.
                while down in buttons():
                    if up in buttons():
                        raise RuntimeError('Flow check cancelled by operator')
                    if clock()-began > 120000:
                        raise RuntimeError('Flow check timed out waiting for button release')
                    wait(20)
                return position
            if motor.angle() >= limit:
                raise RuntimeError('Syringe reached its stroke limit before flow')
            if now-began > 120000:
                raise RuntimeError('Flow check timed out before flow was confirmed')
            if motor.control.stalled():
                if stalled_since is None:
                    stalled_since = now
                elif now-stalled_since >= 2000:
                    raise RuntimeError('Syringe stalled before flow was confirmed')
            else:
                stalled_since = None
            log('seek-flow', '')
            wait(20)
    except BaseException:
        motor.brake()
        raise


def load_path(filename):
    points = []
    with open(filename) as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                fields = line.strip().split(',')
                if len(fields) != 3 or fields[2] not in ('0', '1'):
                    raise ValueError()
                x, y = float(fields[0]), float(fields[1])
                if not 0 <= x <= 1 or not 0 <= y <= 1:
                    raise ValueError()
                points.append((x, y, fields[2] == '1'))
            except ValueError:
                raise ValueError('Invalid path row {}'.format(number))
    if len(points) < 2 or points[0][2]:
        raise ValueError('Path needs a right-click travel start, then drawing points')
    return points


def drawing_distance(points, x_span, y_span):
    """Normalized axis travel, using the original integer motor-degree deltas.

    X then Y is an L-shaped movement, so both legs count toward dispensing.
    This is not a physical millimeter or material-volume calibration.
    """
    x, y = 0.0, 0.0
    total = 0.0
    for nx, ny, draw in points:
        if draw:
            # Keep multiplication order identical to the original controller.
            total += abs(int((nx-x) * (x_span/360) * 360)) / x_span
            total += abs(int((ny-y) * (y_span/360) * 360)) / y_span
        x, y = nx, ny
    if total <= 0:
        raise ValueError('The path has no drawable movement')
    return total


class Syringe:
    """Advance C only as the current X/Y leg physically advances.

    No independent path thread, automatic syringe rewind, or X/Y rescaling.
    Clock, wait, stop mode, and logging are injected for EV3 and desktop checks.
    """

    def __init__(self, motor, dose, distance, limit, clock, wait, abort,
                 hold_mode, log=None):
        self.motor = motor
        self.target = float(motor.angle())
        self.dose = dose
        self.distance = distance
        self.limit = limit
        self.clock, self.wait, self.abort = clock, wait, abort
        self.hold_mode = hold_mode
        self.log = log or (lambda *args: None)
        self.retracted = False
        if (dose <= 0 or distance <= 0 or self.target < -2
                or self.target + dose > limit):
            raise ValueError('Not enough syringe stroke left after priming')

    def check(self):
        if self.abort():
            raise RuntimeError('Stopped by operator')
        if self.motor.angle() > self.limit:
            raise RuntimeError('Syringe reached its stroke limit')

    def pause(self):
        if not self.retracted:
            self.motor.run_angle(800, -2, then=self.hold_mode, wait=False)
            began = self.clock()
            while not self.motor.control.done():
                self.check()
                if self.clock()-began > 3000:
                    self.motor.brake()
                    raise RuntimeError('Small syringe reverse timed out')
                self.wait(20)
            self.retracted = True
        self.motor.hold()

    def move_axis(self, axis, label, speed, degrees, span, drawing):
        start = axis.angle()
        initial = self.target
        end = initial
        if drawing:
            end += self.dose * (abs(degrees) / span) / self.distance
        if end > self.limit + 0.00001:
            raise RuntimeError('Drawing exceeds remaining syringe stroke')
        end = min(end, self.limit)
        began = self.clock()
        deadline = abs(degrees) / max(abs(speed), 1) * 3000 + 10000
        progress = 0.0
        last_log = began - 100
        stalled_since = None
        try:
            self.check()
            if not drawing:
                self.pause()
            else:
                self.retracted = False
            # Same angle, speed, and HOLD as the original; poll while it runs
            # so C can follow encoder progress before the next axis starts.
            axis.run_angle(speed, degrees, then=self.hold_mode, wait=False)
            while True:
                self.check()
                now = self.clock()
                if drawing and self.motor.control.stalled():
                    if stalled_since is None:
                        stalled_since = now
                    elif now - stalled_since >= 500:
                        # Brief full-output retry, bounded by the current leg's
                        # final dose, the stroke cap, and the operator stop.
                        if self.motor.angle() < end-1:
                            boosted = self.clock()
                            self.motor.dc(100)
                            try:
                                while self.clock()-boosted < 80 and self.motor.angle() < end-1:
                                    self.check()
                                    self.wait(5)
                            finally:
                                self.motor.brake()
                            self.log('feed-retry', axis.angle(), end,
                                     self.motor.angle(), self.motor.control.stalled())
                        stalled_since = None
                else:
                    stalled_since = None
                if now - began > deadline:
                    raise RuntimeError('Axis or syringe timed out: ' + label)
                if degrees:
                    progress = max(progress, min(1.0, max(
                        0.0, (axis.angle() - start) / degrees)))
                else:
                    progress = 1.0
                done = axis.control.done()
                if done:
                    if abs(axis.angle() - start - degrees) > 10:
                        raise RuntimeError('Axis stopped short: ' + label)
                    progress = 1.0
                reference = initial + (end-initial) * progress
                if drawing:
                    # The reference only advances. Let PID correct overshoot;
                    # chasing the actual angle would accept unwanted extra feed.
                    target = int(round(reference))
                    if target > self.limit:
                        raise RuntimeError('Syringe target exceeds stroke limit')
                    self.motor.track_target(target)
                if now - last_log >= 100:
                    self.log(('draw-' if drawing else 'travel-') + label, axis.angle(), reference,
                             self.motor.angle(), self.motor.control.stalled())
                    last_log = now
                if done and (not drawing or (abs(self.motor.angle()-end) <= 2
                                             and abs(self.motor.speed()) <= 10)):
                    self.target = end
                    return
                self.wait(20)
        except BaseException:
            axis.brake()
            self.motor.brake()
            raise


class PulseSyringe(Syringe):
    """Trial pulsed feed while preserving the original sequential X/Y moves."""
    def __init__(self, motor, dose, distance, limit, clock, wait, abort,
                 hold_mode, log=None):
        super().__init__(motor, min(dose, limit-motor.angle()), distance, limit,
                         clock, wait, abort, hold_mode, log)
        self.phase = 'waiting'
        self.stalled_since = None

    def pause(self):
        self.motor.hold()
        self.phase = 'waiting'

    def move_axis(self, axis, label, speed, degrees, span, drawing):
        began = self.clock()
        deadline = abs(degrees) / max(abs(speed), 1) * 3000 + 10000
        start = axis.angle()
        last_log = began - 100
        try:
            self.check()
            if not drawing:
                self.pause()
            axis.run_angle(speed, degrees, then=self.hold_mode, wait=False)
            while True:
                self.check()
                now = self.clock()
                if now-began > deadline:
                    raise RuntimeError('Axis timed out: ' + label)
                if drawing:
                    if self.motor.control.stalled():
                        if self.stalled_since is None:
                            self.stalled_since = now
                        elif now-self.stalled_since >= 1000:
                            self.motor.brake()
                            self.motor.run_angle(800, -2, then=self.hold_mode, wait=False)
                            self.phase = 'reverse'
                            self.stalled_since = None
                    else:
                        self.stalled_since = None
                    if self.phase == 'forward' and self.motor.control.done():
                        self.motor.run_angle(800, -2, then=self.hold_mode, wait=False)
                        self.phase = 'reverse'
                    elif self.phase == 'reverse' and self.motor.control.done():
                        self.phase = 'waiting'
                    elif self.phase == 'waiting':
                        if self.motor.angle()+80 > self.limit:
                            raise RuntimeError('Remaining syringe stroke exhausted')
                        self.motor.run_angle(300, 80, then=self.hold_mode, wait=False)
                        self.phase = 'forward'
                    self.target = float(self.motor.angle())
                if now-last_log >= 100:
                    self.log(('draw-' if drawing else 'travel-') + label,
                             axis.angle(), self.target, self.motor.angle(),
                             self.motor.control.stalled())
                    last_log = now
                if axis.control.done():
                    if abs(axis.angle()-start-degrees) > 10:
                        raise RuntimeError('Axis stopped short: ' + label)
                    return
                self.wait(20)
        except BaseException:
            axis.brake()
            self.motor.brake()
            raise
