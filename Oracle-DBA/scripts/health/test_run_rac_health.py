"""Linux integration tests using disposable fake collectors, never Oracle."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import pwd
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

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

class HardeningTests(unittest.TestCase):
    """Whole-run timeout, checker trust and previously untested behaviour."""

    setUp = RunnerTests.setUp
    tearDown = RunnerTests.tearDown
    collector = RunnerTests.collector
    args = RunnerTests.args

    @staticmethod
    def ready(pidfile):
        """Readiness handshake for fake collectors: wait until the descendant
        has written its PID, so cleanup can never race the PID file."""
        return ("import os as _os, time as _time\n"
                "_deadline = _time.time() + 10\n"
                "while _time.time() < _deadline:\n"
                "    try:\n"
                "        if open(" + repr(str(pidfile)) + ").read().strip():\n"
                "            break\n"
                "    except OSError:\n"
                "        pass\n"
                "    _time.sleep(0.01)\n")

    def write_checker(self, body):
        self.checker.write_text(body, encoding="utf-8")

    def args_with(self, *extra):
        return runner.parser().parse_args([
            "--checker", str(self.checker), "--output-dir", str(self.out),
            "--expected-user", pwd.getpwuid(os.getuid()).pw_name] + list(extra))

    def last_run(self):
        return json.loads((self.out / "last-run.json").read_text())

    def wait_for(self, path, seconds=10):
        deadline = time.time() + seconds
        while time.time() < deadline:
            if path.exists() and path.read_text().strip():
                return int(path.read_text().split()[0])
            time.sleep(0.05)
        self.fail("timed out waiting for " + str(path))

    @staticmethod
    def alive(pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        # A zombie still answers signal 0; treat it as gone.
        try:
            with open("/proc/{}/stat".format(pid)) as handle:
                return handle.read().split()[2] != "Z"
        except OSError:
            return False

    def test_timeout_stops_collector_and_children_and_is_never_ok(self):
        pids = self.root / "pids"
        self.write_checker(
            "import subprocess, sys, time\n"
            "child = subprocess.Popen(['sleep', '60'])\n"
            "open(" + repr(str(pids)) + ", 'w').write('{} {}'.format(__import__('os').getpid(), child.pid))\n"
            "time.sleep(60)\n")
        old_grace = runner.TERM_GRACE_SECONDS
        runner.TERM_GRACE_SECONDS = 1
        try:
            self.assertEqual(runner.run_once(self.args_with("--max-runtime", "2")), 70)
        finally:
            runner.TERM_GRACE_SECONDS = old_grace
        meta = self.last_run()
        self.assertEqual(meta["status"], "TIMEOUT")
        self.assertEqual(meta["exit_code"], 70)
        self.assertEqual(meta["max_runtime_seconds"], 2)
        self.assertGreaterEqual(meta["elapsed_seconds"], 2)
        collector, grandchild = (int(x) for x in pids.read_text().split())
        time.sleep(0.2)
        self.assertFalse(self.alive(collector))
        self.assertFalse(self.alive(grandchild))
        self.collector(0)
        self.assertEqual(runner.run_once(self.args()), 0)  # lock was released

    def test_non_positive_max_runtime_is_rejected(self):
        self.collector()
        self.assertEqual(runner.main(["--checker", str(self.checker),
                                      "--output-dir", str(self.out),
                                      "--expected-user", pwd.getpwuid(os.getuid()).pw_name,
                                      "--max-runtime", "0"]), 70)

    def test_symlinked_checker_is_rejected(self):
        self.collector()
        link = self.root / "link.py"
        link.symlink_to(self.checker)
        self.checker = link
        with self.assertRaises(ValueError):
            runner.run_once(self.args())

    def test_group_writable_checker_is_rejected(self):
        self.collector()
        self.checker.chmod(0o620)
        with self.assertRaises(ValueError):
            runner.run_once(self.args())

    def test_world_writable_checker_is_rejected(self):
        self.collector()
        self.checker.chmod(0o666)
        with self.assertRaises(ValueError):
            runner.run_once(self.args())

    def test_checker_in_group_writable_directory_is_rejected(self):
        shared = self.root / "shared"
        shared.mkdir()
        shared.chmod(0o770)
        self.checker = shared / "checker.py"
        self.collector()
        with self.assertRaises(ValueError):
            runner.run_once(self.args())

    def test_checker_killed_by_signal_is_runner_error(self):
        self.write_checker("import os, signal\nos.kill(os.getpid(), signal.SIGKILL)\n")
        self.assertEqual(runner.run_once(self.args()), 70)
        self.assertEqual(self.last_run()["checker_exit_code"], -signal.SIGKILL)

    def test_report_exit_code_mismatch_cannot_pass(self):
        self.write_checker(
            "import json, sys\n"
            "a = sys.argv\n"
            "json.dump({'schema_version': 1, 'database': a[a.index('--db')+1], "
            "'coverage': {}, 'exit_code': 0}, open(a[a.index('--json-out')+1], 'w'))\n"
            "sys.exit(1)\n")
        self.assertEqual(runner.run_once(self.args()), 70)

    def test_wrong_expected_user_fails_through_main(self):
        self.collector()
        self.assertEqual(runner.main(["--checker", str(self.checker),
                                      "--output-dir", str(self.out),
                                      "--expected-user", "not-" + pwd.getpwuid(os.getuid()).pw_name]), 70)

    def test_relative_checker_fails_through_main(self):
        self.collector()
        self.assertEqual(runner.main(["--checker", "fake collector.py",
                                      "--output-dir", str(self.out),
                                      "--expected-user", pwd.getpwuid(os.getuid()).pw_name]), 70)

    def test_orphaned_collector_keeps_lock_after_launcher_is_killed(self):
        pidfile = self.root / "collector.pid"
        self.write_checker(
            "import os, time\n"
            "open(" + repr(str(pidfile)) + ", 'w').write(str(os.getpid()))\n"
            "time.sleep(60)\n")
        launcher = subprocess.Popen(
            [sys.executable, str(Path(runner.__file__)),
             "--checker", str(self.checker), "--output-dir", str(self.out),
             "--expected-user", pwd.getpwuid(os.getuid()).pw_name],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        collector = self.wait_for(pidfile)
        try:
            launcher.kill()
            launcher.wait()
            self.assertEqual(runner.run_once(self.args()), 75)
        finally:
            os.kill(collector, signal.SIGKILL)
            time.sleep(0.2)

    def test_timeout_kills_descendant_that_ignores_sigterm(self):
        pidfile = self.root / "descendant.pid"
        # The descendant ignores SIGTERM and inherits the lock descriptor;
        # the collector itself exits on SIGTERM. Escalation must still reach it.
        self.write_checker(
            "import subprocess, sys, time\n"
            "subprocess.Popen([sys.executable, '-c', "
            "\"import os, signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "open(" + repr(str(pidfile)) + ", 'w').write(str(os.getpid())); time.sleep(60)\"], "
            "close_fds=False)\n"
            + self.ready(pidfile) +
            "time.sleep(60)\n")
        old_grace = runner.TERM_GRACE_SECONDS
        runner.TERM_GRACE_SECONDS = 1
        try:
            self.assertEqual(runner.run_once(self.args_with("--max-runtime", "2")), 70)
        finally:
            runner.TERM_GRACE_SECONDS = old_grace
        descendant = self.wait_for(pidfile)
        try:
            meta = self.last_run()
            self.assertEqual(meta["status"], "TIMEOUT")
            self.assertNotIn("surviving_pids", meta)
            self.assertFalse(self.alive(descendant))
            self.collector(0)
            self.assertEqual(runner.run_once(self.args()), 0)  # lock not inherited by a survivor
        finally:
            if self.alive(descendant):
                os.kill(descendant, signal.SIGKILL)

    def test_leftover_child_after_normal_exit_is_stopped_and_recorded(self):
        pidfile = self.root / "leftover.pid"
        self.write_checker(
            "import json, subprocess, sys\n"
            "subprocess.Popen([sys.executable, '-c', "
            "\"import os, time; open(" + repr(str(pidfile)) + ", 'w').write(str(os.getpid())); "
            "time.sleep(60)\"], close_fds=False)\n"
            + self.ready(pidfile) +
            "a = sys.argv\n"
            "json.dump({'schema_version': 1, 'database': a[a.index('--db')+1], "
            "'coverage': {}, 'exit_code': 0}, open(a[a.index('--json-out')+1], 'w'))\n")
        old_grace = runner.TERM_GRACE_SECONDS
        runner.TERM_GRACE_SECONDS = 1
        try:
            leftover = None
            self.assertEqual(runner.run_once(self.args()), 0)
            leftover = self.wait_for(pidfile)
            meta = self.last_run()
            self.assertIn(leftover, meta["leftover_pids"])
            self.assertNotIn("surviving_pids", meta)
            self.assertFalse(self.alive(leftover))
            self.collector(0)
            self.assertEqual(runner.run_once(self.args()), 0)  # lock not held by the leftover
        finally:
            runner.TERM_GRACE_SECONDS = old_grace
            if leftover and self.alive(leftover):
                os.kill(leftover, signal.SIGKILL)

    def test_failed_cleanup_after_normal_exit_is_never_ok(self):
        pidfile = self.root / "survivor.pid"
        self.write_checker(
            "import json, subprocess, sys\n"
            "subprocess.Popen([sys.executable, '-c', "
            "\"import os, time; open(" + repr(str(pidfile)) + ", 'w').write(str(os.getpid())); "
            "time.sleep(60)\"], close_fds=False)\n"
            + self.ready(pidfile) +
            "a = sys.argv\n"
            "json.dump({'schema_version': 1, 'database': a[a.index('--db')+1], "
            "'coverage': {}, 'exit_code': 0}, open(a[a.index('--json-out')+1], 'w'))\n")
        real_killpg, old_grace = runner.os.killpg, runner.TERM_GRACE_SECONDS

        def denied(pgid, sig):
            raise PermissionError(1, "Operation not permitted")
        survivor = None
        runner.os.killpg, runner.TERM_GRACE_SECONDS = denied, 1
        try:
            result = runner.run_once(self.args())
            survivor = self.wait_for(pidfile)
            meta = self.last_run()
            self.assertEqual(result, 70)
            self.assertEqual(meta["status"], "RUNNER_ERROR")
            self.assertEqual(meta["exit_code"], 70)
            self.assertEqual(meta["checker_exit_code"], 0)  # the checker's own result is kept
            self.assertIn(survivor, meta["surviving_pids"])
        finally:
            runner.os.killpg, runner.TERM_GRACE_SECONDS = real_killpg, old_grace
            if survivor and self.alive(survivor):
                os.kill(survivor, signal.SIGKILL)

    def test_successful_cleanup_reaps_direct_child_that_exits_after_poll(self):
        child = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
        deadline = time.time() + 10
        while time.time() < deadline and runner.live_group_members(child.pid):
            time.sleep(0.01)  # now a zombie: hidden from /proc membership, not yet reaped

        class ExitsJustAfterPoll:
            """poll() reports 'still running', as if the child exited a moment later."""
            pid = child.pid
            returncode = None

            def poll(self):
                return None

            def wait(self, timeout=None):
                self.returncode = child.wait(timeout=timeout)
                return self.returncode
        self.assertEqual(runner.stop_group(ExitsJustAfterPoll()), [])
        self.assertIsNotNone(child.returncode)  # reaped, no ResourceWarning

    def test_group_cleanup_tolerates_unsignalable_members_without_blocking(self):
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                 start_new_session=True)
        real_killpg, old_grace = runner.os.killpg, runner.TERM_GRACE_SECONDS

        def denied(pgid, sig):
            raise PermissionError(1, "Operation not permitted")
        runner.os.killpg, runner.TERM_GRACE_SECONDS = denied, 1
        try:
            started = time.monotonic()
            survivors = runner.stop_group(child)
            self.assertLess(time.monotonic() - started, 10)
            self.assertEqual(survivors, [child.pid])
        finally:
            runner.os.killpg, runner.TERM_GRACE_SECONDS = real_killpg, old_grace
            child.kill()
            child.wait()

    def test_final_cleanup_boundary_reaps_child_or_reports_it_as_survivor(self):
        # Exhaust both group grace periods, then model the child exiting after
        # the final poll: /proc can omit its zombie before wait() has reaped it.
        for can_reap in (True, False):
            with self.subTest(can_reap=can_reap):
                child = mock.Mock(pid=123456, returncode=None)

                def wait(timeout=None):
                    if not can_reap:
                        raise subprocess.TimeoutExpired("fake collector", timeout)
                    child.returncode = 0
                    return 0

                child.wait.side_effect = wait
                with mock.patch.object(runner, "TERM_GRACE_SECONDS", 0), \
                        mock.patch.object(runner, "signal_group"), \
                        mock.patch.object(runner, "live_group_members",
                                          side_effect=[[child.pid], [child.pid], []]):
                    survivors = runner.stop_group(child)
                child.wait.assert_called_once_with(timeout=0)
                self.assertEqual(survivors, [] if can_reap else [child.pid])

    def test_fifo_at_lock_path_is_rejected_without_blocking(self):
        self.collector()
        runner.private_directory(self.out)
        os.mkfifo(str(self.out / "runner.lock"), 0o600)
        command = [sys.executable, str(Path(runner.__file__)),
                   "--checker", str(self.checker), "--output-dir", str(self.out),
                   "--expected-user", pwd.getpwuid(os.getuid()).pw_name]
        try:
            result = subprocess.run(command, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, timeout=10)
        except subprocess.TimeoutExpired:
            self.fail("runner blocked opening a FIFO lock path")
        self.assertEqual(result.returncode, 70)

    def test_last_run_records_checker_sha256(self):
        import hashlib
        self.collector()
        self.assertEqual(runner.run_once(self.args()), 0)
        self.assertEqual(self.last_run()["checker_sha256"],
                         hashlib.sha256(self.checker.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
