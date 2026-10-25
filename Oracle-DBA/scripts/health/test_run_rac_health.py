"""Linux integration tests using disposable fake collectors, never Oracle."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import pwd
import tempfile
import time
import unittest

spec = importlib.util.spec_from_file_location(
    "health_runner", str(Path(__file__).with_name("run_rac_health.py")))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.old_umask = os.umask(0o077)
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.out = self.root / "private"
        self.checker = self.root / "fake collector.py"

    def tearDown(self):
        self.temp.cleanup()
        os.umask(self.old_umask)

    def collector(self, code=0, write_report=True, wrong_database=False):
        self.checker.write_text(
            "import json, os, sys\n"
            "assert 'ORACLE_HOME' not in os.environ\n"
            "assert 'TWO_TASK' not in os.environ\n"
            "a = sys.argv\n"
            "path = a[a.index('--json-out')+1]\n"
            "db = a[a.index('--db')+1]\n"
            + ("db = 'WRONG'\n" if wrong_database else "")
            + ("with open(path, 'w') as f:\n"
               "    json.dump({'schema_version':1, 'database':db, "
               "'coverage':{}, 'exit_code':" + str(code) + "}, f)\n"
               if write_report else "")
            + "print('fake collector output')\n"
            + "sys.exit(" + str(code) + ")\n",
            encoding="utf-8")

    def args(self):
        return runner.parser().parse_args([
            "--checker", str(self.checker), "--output-dir", str(self.out),
            "--expected-user", pwd.getpwuid(os.getuid()).pw_name])

    def test_preserves_all_checker_exit_classes(self):
        for code in (0, 1, 2, 3):
            with self.subTest(code=code):
                self.collector(code, write_report=(code != 3))
                self.assertEqual(runner.run_once(self.args()), code)
                meta = json.loads((self.out / "last-run.json").read_text())
                self.assertEqual(meta["exit_code"], code)
                self.assertIn("finished_at", meta)

    def test_missing_report_cannot_be_ok(self):
        self.collector(0, write_report=False)
        self.assertEqual(runner.run_once(self.args()), 70)

    def test_wrong_database_cannot_be_ok(self):
        self.collector(0, wrong_database=True)
        self.assertEqual(runner.run_once(self.args()), 70)

    def test_local_overlap_skips_without_overwriting_last_run(self):
        self.collector()
        runner.private_directory(self.out)
        marker = self.out / "last-run.json"
        marker.write_text('{"status":"RUNNING"}')
        with runner.private_open(self.out / "runner.lock") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(runner.run_once(self.args()), 75)
        self.assertEqual(marker.read_text(), '{"status":"RUNNING"}')

    def test_artifacts_are_private_and_collector_sees_clean_environment(self):
        self.collector()
        old = {k: os.environ.get(k) for k in ("ORACLE_HOME", "TWO_TASK")}
        try:
            os.environ.update(ORACLE_HOME="/wrong", TWO_TASK="wrong")
            self.assertEqual(runner.run_once(self.args()), 0)
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual(self.out.stat().st_mode & 0o777, 0o700)
        for path in self.out.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_shared_output_directory_is_rejected(self):
        self.collector()
        self.out.mkdir(mode=0o700)
        self.out.chmod(0o755)
        with self.assertRaises(ValueError):
            runner.run_once(self.args())

    def test_symlink_lock_is_rejected(self):
        self.collector()
        runner.private_directory(self.out)
        target = self.root / "untouched"
        target.write_text("keep")
        (self.out / "runner.lock").symlink_to(target)
        with self.assertRaises(OSError):
            runner.run_once(self.args())
        self.assertEqual(target.read_text(), "keep")

    def test_retention_only_removes_old_matching_regular_artifacts(self):
        runner.private_directory(self.out)
        old = self.out / "health-20200101T010101000000Z-123.log"
        keep = self.out / "unrelated.log"
        old.write_text("old")
        keep.write_text("keep")
        linked = self.out / "health-20200101T010101000000Z-456.log"
        linked.symlink_to(keep)
        timestamp = time.time() - 40 * 86400
        os.utime(str(old), (timestamp, timestamp))
        os.utime(str(keep), (timestamp, timestamp))
        runner.prune(self.out, 30)
        self.assertFalse(old.exists())
        self.assertEqual(keep.read_text(), "keep")
        self.assertTrue(linked.is_symlink())

if __name__ == "__main__":
    unittest.main()
