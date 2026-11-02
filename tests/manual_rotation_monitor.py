"""Record hand-driven C encoder movement with the motor released, never powered."""
from pathlib import Path
import shlex
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import desktop

REMOTE = r'''
import glob, time
from pathlib import Path
motors = [Path(p) for p in glob.glob('/sys/class/tacho-motor/motor*')]
motor = next(p for p in motors if (p/'address').read_text().strip().endswith('outC'))
if any((p/'speed').read_text().strip() != '0' or
       'running' in (p/'state').read_text() for p in motors):
    raise RuntimeError('A motor is still running; passive measurement not started')
(motor/'stop_action').write_text('coast')
(motor/'command').write_text('stop')
start = int((motor/'position').read_text())
counts = int((motor/'count_per_rot').read_text())
began = time.monotonic()
print('READY: C released; relative zero is current position, NOT physical top', flush=True)
print('seconds,relative_degrees,relative_turns,speed_counts_s,forward_degrees,backward_degrees', flush=True)
previous = start
forward = backward = 0
last_report = -1
while time.monotonic()-began < 1800:
    position = int((motor/'position').read_text())
    change = position-previous
    forward += max(0, change)
    backward += max(0, -change)
    previous = position
    delta = position-start
    speed = int((motor/'speed').read_text())
    elapsed = time.monotonic()-began
    if elapsed-last_report >= 0.25:
        print('{:.2f},{:.2f},{:.5f},{},{:.2f},{:.2f}'.format(elapsed,
              delta*360/counts, delta/counts, speed, forward*360/counts,
              backward*360/counts), flush=True)
        last_report = elapsed
    time.sleep(0.02)
'''

if __name__ == '__main__':
    results = ROOT/'tests/results'
    results.mkdir(exist_ok=True)
    filename = results/('manual-C-{}.csv'.format(time.strftime('%Y%m%d-%H%M%S')))
    client = desktop.connect()
    try:
        _, output, errors = client.exec_command('python3 -u -c '+shlex.quote(REMOTE))
        with filename.open('w') as log:
            for line in output:
                log.write(line)
                log.flush()
                print(line.rstrip(), flush=True)
        error = errors.read().decode()
        if error:
            print(error, flush=True)
        if output.channel.recv_exit_status():
            raise RuntimeError('Passive monitor failed')
    finally:
        client.close()
        print('Rotation log:', filename, flush=True)
