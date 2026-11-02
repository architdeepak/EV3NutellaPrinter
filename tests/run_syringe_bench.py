"""Upload/run the dry C benchmark and retrieve its CSV, with Ctrl+C stop."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import desktop


def run(start_angle=None, step=None):
    client = desktop.connect()
    channel = None
    remote_log = None
    try:
        with client.open_sftp() as sftp:
            for name in ('dispensing.py', 'tests/syringe_bench.py'):
                sftp.put(str(ROOT/name), desktop.REMOTE_ROOT+'/'+name)
        command = ('cd '+desktop.REMOTE_ROOT+
                   ' && brickrun -r -- pybricks-micropython tests/syringe_bench.py')
        if step is not None:
            command += ' --step {} {}'.format(int(start_angle), int(step))
        stdin, stdout, stderr = client.exec_command(command, get_pty=True)
        channel = stdout.channel
        for line in stdout:
            print(line.rstrip(), flush=True)
            match = re.search(r'LOG: (tests/results/c-bench-\d+\.csv)', line)
            if match:
                remote_log = match.group(1)
        code = channel.recv_exit_status()
        print('Benchmark exit code:', code, flush=True)
        return code
    except KeyboardInterrupt:
        if channel:
            channel.send('\x03')
        raise
    finally:
        if remote_log:
            local = ROOT/remote_log
            local.parent.mkdir(parents=True, exist_ok=True)
            with client.open_sftp() as sftp:
                sftp.get(desktop.REMOTE_ROOT+'/'+remote_log, str(local))
            print('Saved:', local, flush=True)
        client.close()


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--step':
        raise SystemExit(run(int(sys.argv[2]), int(sys.argv[3])))
    raise SystemExit(run())
