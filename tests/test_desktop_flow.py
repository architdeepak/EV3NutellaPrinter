"""Verify Save -> upload -> automatic run, without moving hardware or opening UI."""

import io
from pathlib import Path
import types
import tempfile
import unittest
from unittest.mock import patch

import desktop


class SFTP:
    def __init__(self):
        self.files = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def stat(self, path):
        return object()

    def put(self, local, remote):
        self.files[remote] = Path(local).read_bytes()

    def open(self, path, mode):
        return io.BytesIO(self.files[path])


class DesktopFlowTests(unittest.TestCase):
    def test_latest_saved_path_is_uploaded_and_started_automatically(self):
        sftp = SFTP()
        commands = []
        closed = []
        def execute(command, **kwargs):
            commands.append((command, kwargs))
            output = io.StringIO('Complete\n')
            output.channel = types.SimpleNamespace(recv_exit_status=lambda: 0)
            return None, output, io.StringIO()
        client = types.SimpleNamespace(open_sftp=lambda: sftp,
                                       exec_command=execute,
                                       close=lambda: closed.append(True))
        with patch('builtins.print'):
            desktop.upload_and_print(desktop.ROOT/'paths/5.txt', client)
        self.assertTrue(closed)
        self.assertEqual(len(sftp.files), 3)
        self.assertTrue(commands[0][0].endswith('main.py --auto 5'))
        self.assertTrue(commands[0][1]['get_pty'])

    def test_cancelled_drawing_never_connects_or_prints(self):
        with patch('draw.run', return_value=None), patch('desktop.upload_and_print') as upload:
            desktop.run(draw_new=True)
        upload.assert_not_called()

    def test_save_immediately_starts_selected_drawing(self):
        path = desktop.ROOT/'paths/5.txt'
        with patch('draw.run', return_value=path) as draw, patch('desktop.upload_and_print') as upload:
            desktop.run(draw_new=True)
        draw.assert_called_once_with(print_on_save=True)
        upload.assert_called_once_with(path)

    def test_default_run_uses_owner_selected_saved_drawing(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'paths').mkdir()
            (root/'paths/12.txt').touch()
            (root/'paths/13.txt').touch()
            with patch('desktop.ROOT',root), patch('desktop.upload_and_print') as upload:
                desktop.run()
            upload.assert_called_once_with(root/'paths/13.txt')

    def test_motor_log_download_retains_recorded_samples(self):
        sftp = SFTP()
        relative = 'tests/results/print-9.csv'
        sftp.files[desktop.REMOTE_ROOT+'/'+relative] = b'ms,c_angle\n100,42\n'
        client = types.SimpleNamespace(open_sftp=lambda: sftp)
        with tempfile.TemporaryDirectory() as directory, patch('builtins.print'):
            saved = desktop.save_motor_log(client, relative, '6.txt', directory)
            self.assertEqual(saved.name, 'path-6-print-9.csv')
            self.assertEqual(saved.read_bytes(), sftp.files[desktop.REMOTE_ROOT+'/'+relative])


if __name__ == '__main__':
    unittest.main()
