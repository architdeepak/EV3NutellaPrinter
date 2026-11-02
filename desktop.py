"""Laptop flow: draw, save, upload, then run the original printer sequence."""

import hashlib
import os
from pathlib import Path
import re
import shlex

from dispensing import drawing_distance, load_path

ROOT = Path(__file__).resolve().parent
REMOTE_ROOT = '/home/robot/EV3NutellaPrinter'


def save_motor_log(client, relative, drawing, results_dir=None):
    if not re.fullmatch(r'tests/results/print-\d+\.csv', relative):
        raise ValueError('Unexpected motor log path')
    results = Path(results_dir) if results_dir else ROOT/'tests/results'
    results.mkdir(parents=True, exist_ok=True)
    destination = results/('path-{}-{}'.format(Path(drawing).stem, Path(relative).name))
    with client.open_sftp() as sftp:
        with sftp.open(REMOTE_ROOT+'/'+relative, 'rb') as source:
            destination.write_bytes(source.read())
    print('Motor log saved: {}'.format(destination), flush=True)
    return destination


def connect():
    import paramiko

    configured = os.environ.get('EV3_HOST')
    hosts = [configured] if configured else ['ev3dev.local', '10.0.0.223']
    error = None
    for host in hosts:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        try:
            print('Connecting to EV3 at {}...'.format(host), flush=True)
            client.connect(host, username=os.environ.get('EV3_USER', 'robot'),
                           password=os.environ.get('EV3_PASSWORD', 'maker'),
                           look_for_keys=False, allow_agent=False, timeout=5,
                           auth_timeout=10, banner_timeout=10)
            return client
        except paramiko.BadHostKeyException:
            client.close()
            raise
        except (OSError, paramiko.SSHException) as exc:
            error = exc
            client.close()
    raise RuntimeError('Could not connect to EV3. Check power/Wi-Fi or EV3_HOST. {}'.format(error))


def upload_and_print(path, client=None, skip_flow=False):
    path = Path(path).resolve()
    if not path.stem.isdigit() or path.suffix != '.txt':
        raise ValueError('Expected a numbered drawing file')
    points = load_path(str(path))
    drawing_distance(points, 27*360, 15*360)
    client = client or connect()
    channel = None
    motor_log = None
    try:
        with client.open_sftp() as sftp:
            for directory in (REMOTE_ROOT, REMOTE_ROOT+'/paths'):
                try:
                    sftp.stat(directory)
                except OSError:
                    sftp.mkdir(directory)
            files = [(ROOT/'main.py', 'main.py'), (ROOT/'dispensing.py', 'dispensing.py'),
                     (path, 'paths/'+path.name)]
            for local, relative in files:
                remote = REMOTE_ROOT+'/'+relative
                sftp.put(str(local), remote)
                with sftp.open(remote, 'rb') as handle:
                    actual = hashlib.sha256(handle.read()).digest()
                if actual != hashlib.sha256(local.read_bytes()).digest():
                    raise RuntimeError('Upload verification failed: '+relative)
        print('Drawing uploaded and verified. Using manually positioned syringe; homing then printing.', flush=True)
        command = 'cd {} && brickrun -r -- pybricks-micropython main.py --auto {}'.format(
            shlex.quote(REMOTE_ROOT), int(path.stem))
        stdin, stdout, stderr = client.exec_command(command, get_pty=True)
        channel = stdout.channel
        for line in stdout:
            if line.strip().startswith('Telemetry: '):
                motor_log = line.strip().split('Telemetry: ', 1)[1]
            print(line.rstrip(), flush=True)
        result = channel.recv_exit_status()
        if result:
            raise RuntimeError('EV3 stopped with exit code {}'.format(result))
        print('Print complete.', flush=True)
    except KeyboardInterrupt:
        if channel is not None:
            channel.send('\x03')
        raise
    finally:
        if motor_log:
            try:
                save_motor_log(client, motor_log, path)
            except Exception as error:
                print('Could not copy motor log: {}'.format(error), flush=True)
        client.close()


def run(draw_new=False):
    if draw_new:
        from draw import run as draw
        path = draw(print_on_save=True)
    else:
        candidates = [p for p in (ROOT/'paths').glob('*.txt') if p.stem.isdigit()]
        if not candidates:
            raise RuntimeError('No saved drawing exists; run python main.py --draw')
        path = max(candidates, key=lambda p: int(p.stem))
        print('Using saved drawing:', path, flush=True)
    if path is None:
        print('Drawing cancelled; printer was not started.', flush=True)
        return
    try:
        upload_and_print(path)
    except Exception as error:
        print('Printer stopped: {}'.format(error), flush=True)
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('Nutella printer', str(error), parent=root)
        root.destroy()
        raise
