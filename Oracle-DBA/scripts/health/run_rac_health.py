#!/usr/bin/env python3
"""Schedule the existing read-only RAC checker; Linux, tested on Python 3.9 and 3.12.

Exit 0/1/2/3: checker OK/warning/critical/configuration error.
Exit 70: runner/report failure or whole-run timeout; 75: another local run holds the lock.
No Oracle configuration changes, automatic repairs or notifications.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time

ARTIFACT = re.compile(r"^health-\d{8}T\d{12}Z-\d+\.(log|json|run\.json)$")
CLEAN_ENV = (
    "ORACLE_HOME", "ORACLE_BASE", "ORACLE_SID", "TWO_TASK", "LOCAL",
    "GRID_HOME", "GRID_BASE", "DB_HOME", "DB_BASE", "DB_UNIQUE_NAME",
    "DB_SID", "ASM_SID", "EXPECTED_NODES", "EXPECTED_PDBS", "OSASM_GROUP",
    "DBCA_LOG_DIR", "DB_ALERT_LOG", "ASM_ALERT_LOG", "ALERT_LOOKBACK_HOURS",
    "ALERT_LOG_LINES", "COMMAND_TIMEOUT", "PYTHONPATH", "PYTHONHOME",
    "LD_LIBRARY_PATH", "LD_PRELOAD",
)
TERM_GRACE_SECONDS = 10  # Wait after SIGTERM before SIGKILL on a timed-out collector.

def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checker", required=True, help="Absolute trusted rac_health_check.py path")
    p.add_argument("--output-dir", required=True, help="Private local directory; not NFS/shared ASM")
    p.add_argument("--expected-user", default="grid")
    p.add_argument("--db", default="RAC")
    p.add_argument("--pdb", default="RACPDB1")
    p.add_argument("--nodes", default="racnode1,racnode2")
    p.add_argument("--dbca-node", default="racnode1")
    p.add_argument("--keep-days", type=int, default=30)
    p.add_argument("--max-runtime", type=int, default=600,
                   help="Whole-run deadline in seconds; the collector is stopped after it")
    return p

def private_directory(path):
    if not path.is_absolute():
        raise ValueError("output-dir must be absolute")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("output-dir must be a real directory owned by this account")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError("output-dir must have mode 0700")
    # Advisory file locking is for this local runner, not cross-node exclusion.

def private_open(path, exclusive=False):
    # O_NONBLOCK: a FIFO planted at this path must fail (ENXIO) or open at once,
    # never block before fstat() can reject it.
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
    if exclusive:
        flags |= os.O_EXCL
    fd = os.open(str(path), flags, 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        os.close(fd)
        raise ValueError("Unsafe file owner/type")
    if stat.S_IMODE(info.st_mode) & 0o077:
        os.close(fd)
        raise ValueError("File must be private (0600)")
    return os.fdopen(fd, "w", encoding="utf-8")

def trusted_checker(path):
    """Reject a checker that someone other than this account or root could replace."""
    if not path.is_absolute():
        raise ValueError("checker must be an absolute path")
    try:
        info = path.lstat()
        parent = path.parent.stat()
    except OSError:
        raise ValueError("checker must be an existing absolute trusted Python file")
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("checker must be a regular file, not a symlink")
    for item, label in ((info, "checker"), (parent, "checker directory")):
        if item.st_uid not in (os.getuid(), 0):
            raise ValueError(label + " must be owned by this account or root")
        if stat.S_IMODE(item.st_mode) & 0o022:
            raise ValueError(label + " must not be group- or other-writable")

def live_group_members(pgid):
    """PIDs still running in a process group; zombies are ignored (Linux /proc)."""
    members = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open("/proc/" + entry + "/stat") as handle:
                data = handle.read()
        except OSError:
            continue
        fields = data[data.rfind(")") + 2:].split()
        if len(fields) > 2 and fields[0] != "Z" and int(fields[2]) == pgid:
            members.append(int(entry))
    return members

def signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError):
        pass  # Group gone, or only members this account may not signal (e.g. setuid).

def reap(child):
    """Reap the direct child; True once it has exited and been collected."""
    try:
        child.wait(timeout=TERM_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass  # Still running (e.g. uninterruptible I/O); reported via surviving_pids.
    return child.returncode is not None

def stop_group(child):
    """Stop every member of the collector's process group: SIGTERM, then SIGKILL.

    Escalation tracks the whole group, not just the direct child, so a
    descendant that ignores SIGTERM is still killed. Never blocks beyond the
    two group grace periods and one final reap grace period; returns the PIDs
    of any members still running or an unreaped direct child.
    """
    pgid = child.pid
    for sig in (signal.SIGTERM, signal.SIGKILL):
        signal_group(pgid, sig)
        deadline = time.monotonic() + TERM_GRACE_SECONDS
        while True:
            child.poll()  # reap the direct child so it does not count as alive
            if not live_group_members(pgid):
                # /proc hides zombies, so the child may have exited after poll();
                # reap it before reporting success, never leave it unreaped.
                return [] if reap(child) else [child.pid]
            if time.monotonic() >= deadline:
                break
            time.sleep(0.1)
    reaped = reap(child)
    survivors = live_group_members(pgid)
    if not reaped and child.pid not in survivors:
        survivors.append(child.pid)
    return survivors

def atomic_json(path, data):
    fd, name = tempfile.mkstemp(prefix=".health-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(name, str(path))
    finally:
        if os.path.exists(name):
            os.unlink(name)

def prune(directory, keep_days):
    cutoff = time.time() - keep_days * 86400
    for path in directory.iterdir():
        if not ARTIFACT.fullmatch(path.name):
            continue
        info = path.lstat()
        if (stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and info.st_mtime < cutoff):
            path.unlink()

def report_valid(path, returncode, database):
    try:
        if path.is_symlink():
            return False
        info = path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_size > 16 * 1024 * 1024
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
            return False
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return (isinstance(data, dict) and data.get("schema_version") == 1
                and data.get("exit_code") == returncode
                and data.get("database") == database
                and isinstance(data.get("coverage"), dict))
    except (OSError, ValueError):
        return False

def run_once(args):
    os.umask(0o077)
    if pwd.getpwuid(os.getuid()).pw_name != args.expected_user:
        raise ValueError("Run as the approved account: " + args.expected_user)
    if args.keep_days < 1:
        raise ValueError("keep-days must be positive")
    if args.max_runtime < 1:
        raise ValueError("max-runtime must be positive")
    checker = Path(args.checker)
    directory = Path(args.output_dir)
    trusted_checker(checker)
    private_directory(directory)
    with private_open(directory / "runner.lock") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("SKIPPED: another local health check is still running", file=sys.stderr)
            return 75
        prune(directory, args.keep_days)
        now = datetime.datetime.now(datetime.timezone.utc)
        stem = "health-" + now.strftime("%Y%m%dT%H%M%S%fZ") + "-" + str(os.getpid())
        log = directory / (stem + ".log")
        report = directory / (stem + ".json")
        meta = {
            "started_at": now.isoformat(), "status": "RUNNING",
            "log": log.name, "report": report.name, "database": args.db,
            "checker_sha256": hashlib.sha256(checker.read_bytes()).hexdigest(),
        }
        atomic_json(directory / "last-run.json", meta)
        env = os.environ.copy()
        for name in CLEAN_ENV:
            env.pop(name, None)
        env.update(PATH="/usr/bin:/bin", LC_ALL="C", LANG="C")
        command = [sys.executable, str(checker), "--db", args.db,
                   "--pdb", args.pdb, "--nodes", args.nodes,
                   "--dbca-node", args.dbca_node, "--alert-hours", "24",
                   "--timeout", "45", "--json-out", str(report)]
        child_code = None
        timed_out = False
        survivors = []
        started = time.monotonic()
        try:
            with private_open(log, exclusive=True) as handle:
                # Own process group, so a timeout also stops the collector's children.
                child = subprocess.Popen(
                    command, stdin=subprocess.DEVNULL, stdout=handle,
                    stderr=subprocess.STDOUT, env=env, pass_fds=(lock.fileno(),),
                    start_new_session=True)
                try:
                    child_code = child.wait(timeout=args.max_runtime)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    survivors = stop_group(child)
                    child_code = child.returncode
                else:
                    leftovers = live_group_members(child.pid)
                    if leftovers:  # e.g. a command the checker's own timeout abandoned
                        meta["leftover_pids"] = leftovers
                        survivors = stop_group(child)
            if timed_out:
                result = 70  # A collector stopped at the deadline is never OK.
            elif survivors:
                result = 70  # Cleanup failed; a survivor may still hold the lock.
            elif child_code == 3:
                result = 3  # Discovery/configuration failures can precede JSON output.
            elif child_code in (0, 1, 2) and report_valid(report, child_code, args.db):
                result = child_code
            else:
                result = 70  # Never turn missing/invalid evidence into OK.
            status = {0: "OK", 1: "WARNING", 2: "CRITICAL",
                      3: "CONFIG_ERROR", 70: "RUNNER_ERROR"}[result]
            if timed_out:
                status = "TIMEOUT"
                meta.update(max_runtime_seconds=args.max_runtime,
                            elapsed_seconds=round(time.monotonic() - started, 1))
            if survivors:  # e.g. uninterruptible I/O or setuid; they may still hold the lock
                meta["surviving_pids"] = survivors
            meta.update(status=status, exit_code=result, checker_exit_code=child_code)
        except OSError as exc:
            result = 70
            meta.update(status="RUNNER_ERROR", exit_code=result, error=str(exc))
        meta["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        atomic_json(directory / (stem + ".run.json"), meta)
        atomic_json(directory / "last-run.json", meta)
        print("{} exit={} log={}".format(meta["status"], result, log))
        return result

def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return run_once(args)
    except (OSError, ValueError) as exc:
        print("RUNNER ERROR: " + str(exc), file=sys.stderr)
        return 70

if __name__ == "__main__":
    sys.exit(main())
