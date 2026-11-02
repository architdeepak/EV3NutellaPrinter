"""Upload and monitor the bounded C-dispense plus X/Y-home test."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import desktop

client = desktop.connect()
channel = None
try:
    with client.open_sftp() as sftp:
        sftp.put(str(ROOT / "tests/dispense_while_homing.py"),
                 desktop.REMOTE_ROOT + "/tests/dispense_while_homing.py")
    print("Starting bounded dispense while X/Y return home.", flush=True)
    _, out, err = client.exec_command(
        "cd " + desktop.REMOTE_ROOT +
        " && brickrun -r -- pybricks-micropython tests/dispense_while_homing.py",
        get_pty=True,
    )
    channel = out.channel
    for line in out:
        print(line.rstrip(), flush=True)
    error_text = err.read().decode(errors="replace").strip()
    if error_text:
        print(error_text, flush=True)
    result = channel.recv_exit_status()
    print("Sequence exit:", result, flush=True)
    if result:
        raise SystemExit(result)
except KeyboardInterrupt:
    if channel:
        channel.send("\x03")
    raise
finally:
    client.close()
