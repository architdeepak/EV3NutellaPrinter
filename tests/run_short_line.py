"""Upload and monitor the bounded two-motor line test."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import desktop

client = desktop.connect()
remote_log = None
channel = None
try:
    with client.open_sftp() as sftp:
        sftp.put(str(ROOT/'tests/pulse_line.py'), desktop.REMOTE_ROOT+'/tests/pulse_line.py')
    _, out, err = client.exec_command('cd '+desktop.REMOTE_ROOT+
        ' && brickrun -r -- pybricks-micropython tests/pulse_line.py', get_pty=True)
    channel = out.channel
    for line in out:
        print(line.rstrip(), flush=True)
        if line.startswith('LOG: tests/results/pulse-line-'):
            remote_log = line.strip()[5:]
    print('Test exit:', channel.recv_exit_status(), flush=True)
except KeyboardInterrupt:
    if channel:
        channel.send('\x03')
    raise
finally:
    if remote_log:
        with client.open_sftp() as sftp:
            sftp.get(desktop.REMOTE_ROOT+'/'+remote_log, str(ROOT/remote_log))
        print('Saved:', ROOT/remote_log, flush=True)
    client.close()
