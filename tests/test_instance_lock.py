import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from instance_lock import single_instance


class InstanceLockTests(unittest.TestCase):
    def child(self, path, crash=False):
        code = (
            "import os, sys\n"
            "from pathlib import Path\n"
            "from instance_lock import single_instance, AlreadyRunningError\n"
            "try:\n"
            "    with single_instance(Path(sys.argv[1])):\n"
            + ("        os._exit(0)\n" if crash else "        pass\n")
            + "except AlreadyRunningError:\n"
            "    sys.exit(23)\n"
        )
        return subprocess.run(
            [sys.executable, "-c", code, str(path)],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True, text=True, timeout=10,
        )

    def test_second_process_is_blocked_and_can_start_after_release(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bot.lock"
            with single_instance(path):
                result = self.child(path)
                self.assertEqual(result.returncode, 23, result.stderr)
            result = self.child(path)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_crash_does_not_leave_a_stale_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bot.lock"
            result = self.child(path, crash=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with single_instance(path):
                pass

    def test_exception_releases_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bot.lock"
            with self.assertRaises(ValueError):
                with single_instance(path):
                    raise ValueError("test")
            result = self.child(path)
            self.assertEqual(result.returncode, 0, result.stderr)
