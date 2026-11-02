"""Run and retain the cart/manual-syringe calibration recording."""
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import desktop
client = desktop.connect()
filename = ROOT/'tests/results'/('manual-feed-cart-'+time.strftime('%Y%m%d-%H%M%S')+'.csv')
try:
    with client.open_sftp() as sftp:
        sftp.put(str(ROOT/'tests/manual_feed_cart.py'), desktop.REMOTE_ROOT+'/tests/manual_feed_cart.py')
    _, out, err = client.exec_command('python3 -u '+desktop.REMOTE_ROOT+'/tests/manual_feed_cart.py')
    with filename.open('w') as log:
        for line in out:
            log.write(line)
            log.flush()
            if not line[:1].isdigit():
                print(line.rstrip(), flush=True)
    print(err.read().decode(), flush=True)
    print('Exit:', out.channel.recv_exit_status(), 'Recording:', filename, flush=True)
finally:
    client.close()
