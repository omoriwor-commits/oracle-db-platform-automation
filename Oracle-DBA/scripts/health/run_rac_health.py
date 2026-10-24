#!/usr/bin/env python3
"""Schedule the existing read-only RAC checker; Linux, Python 3.6+.

Exit 0/1/2/3: checker OK/warning/critical/configuration error.
Exit 70: runner/report failure; 75: another local run holds the lock.
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
    checker = Path(args.checker)
    directory = Path(args.output_dir)
    if not checker.is_absolute() or not checker.is_file():
        raise ValueError("checker must be an existing absolute trusted Python file")
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
        try:
            with private_open(log, exclusive=True) as handle:
                child_code = subprocess.call(
                    command, stdin=subprocess.DEVNULL, stdout=handle,
                    stderr=subprocess.STDOUT, env=env, pass_fds=(lock.fileno(),))
            if child_code == 3:
                result = 3  # Discovery/configuration failures can precede JSON output.
            elif child_code in (0, 1, 2) and report_valid(report, child_code, args.db):
                result = child_code
            else:
                result = 70  # Never turn missing/invalid evidence into OK.
            meta.update(status={0: "OK", 1: "WARNING", 2: "CRITICAL",
                                3: "CONFIG_ERROR", 70: "RUNNER_ERROR"}[result],
                        exit_code=result, checker_exit_code=child_code)
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
