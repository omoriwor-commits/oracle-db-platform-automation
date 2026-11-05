# Automate the existing RAC health snapshot

**Updated:** 2026-11-05 (whole-run timeout, checker trust checks and eighteen added tests; earlier lab results remain dated 2026-10-20).
**Status:** Eight runner tests passed and one manual RAC snapshot completed on racnode1 on 2026-10-20 (from my terminal output). On 2026-11-05 the original eight tests passed again on racnode1 with Python 3.9.25 at commit d6d988d, before the hardening changes ("Ran 8 tests in 0.768s … OK", per my terminal output). The suite now has twenty-six tests; the eighteen added on 2026-11-05 are set to run in CI on Python 3.9 and 3.12 and have not yet been run on racnode1. Racnode2 runner tests/manual validation and scheduled cron runs remain pending; no schedule has been activated by this change.

## What runs

The runner invokes the existing read-only [RAC checker](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/scripts/oracle-rac/rac_health_check.py), revision 2026-10-19.3. It does not duplicate its SQL or change its thresholds.

Coverage remains OS, Clusterware, listeners/network, database/PDB, ASM, FRA and local bounded alert logs. Run on both nodes to collect both local histories. Cluster-wide observations are intentionally repeated. Tablespace, RMAN-job, blocking-session, invalid-object and failed-Scheduler-job SQL listed as planned in the [health runbook](database-health-checks.md) remain separate work.

Use the OS scheduler for this snapshot: it must be able to launch while Oracle is unavailable. Database discovery may then return CONFIG_ERROR, which is a failed collection, never an all-clear. DBMS_SCHEDULER remains suitable for later database-only checks; do not schedule this collector through both systems.

## Files and controls

- [run_rac_health.py](../scripts/health/run_rac_health.py): password-free launcher using existing authorized OS authentication.
- [test_run_rac_health.py](../scripts/health/test_run_rac_health.py): Linux tests with disposable fake collectors, no Oracle.
- Local exclusive lock prevents overlapping normal runs; inherited lock descriptor stays held by the collector if the launcher exits. The lock and log files are opened non-blocking, so a FIFO or other non-regular file planted at those paths is rejected instead of hanging the runner.
- Logs/reports are private: directory 0700, artifacts 0600. A SHA-256 identifies the checker version used.
- Exit codes 0/1/2/3 preserve OK/warning/critical/configuration-error outcomes. Missing or invalid JSON cannot produce OK.
- The checker must be an absolute path to a regular file (not a symlink), owned by the runner account or root, and neither the file nor its directory may be group- or other-writable. Otherwise the run stops before launching anything.
- --max-runtime (default 600 seconds) is a whole-run deadline. The collector runs in its own process group; at the deadline every member of the group receives SIGTERM, then SIGKILL after 10 seconds, so a descendant that ignores SIGTERM is still stopped. The run records status TIMEOUT with the elapsed time and exits 70. If the collector exits normally but leaves processes in its group (for example, a command its own per-command timeout abandoned), they are stopped the same way and recorded as leftover_pids; the checker's result is kept. Any member that survives SIGKILL or cannot be signaled by this account (for example, a process in uninterruptible I/O or a setuid program) is recorded as surviving_pids, and the runner returns instead of waiting on it. A run with surviving_pids always exits 70 (RUNNER_ERROR, or TIMEOUT if the deadline was hit), never OK; checker_exit_code still records what the checker itself returned. Such a process may still hold the lock, so investigate before the next run. A descendant that starts its own session escapes the group and is not covered.
- Exit 70 means runner/report failure or timeout; 75 means an overlapping run was skipped. Skips do not overwrite the previous run status.
- Matching owned regular artifacts older than 30 days are removed under the lock. Unrelated files and symlinks are not pruned. Adjust --keep-days before retaining audit evidence longer.
- last-run.json records RUNNING before launch and completion afterward; per-run metadata preserves completed history. Unexpected termination can leave RUNNING as evidence of interruption.

No automatic restart, repair, account changes, backup deletion or external notification is included. This is scheduled collection, not an alert-delivery system. A completely down VM/host cannot run cron; external heartbeat monitoring is a separate requirement.

## 1. Stage on both nodes as grid

Keep the existing grid authorization; do not add DBA/ASM privileges to make reports green. Use the checkout and existing checker paths confirmed on racnode1; verify both paths on racnode2:

| Repository | Local path |
|---|---|
| oracle-db-platform-automation | /home/grid/oracle-health-automation |
| Existing validated RAC checker | /home/grid/scripts/rac_health_check.py |

Use the feature branch for testing, or main after merge. The code and tests must be checked out together. Install nothing as root. Confirm /usr/bin/python3 exists, then inspect identity/paths:

```bash
whoami
/usr/bin/python3 --version
ls -l /home/grid/oracle-health-automation/Oracle-DBA/scripts/health/
ls -ld /home/grid/scripts /home/grid/scripts/rac_health_check.py
/usr/bin/python3 /home/grid/scripts/rac_health_check.py --version
```

Neither the checker nor /home/grid/scripts may show group or other write permission (no `w` in the last six mode characters); the runner refuses to launch it otherwise. The collector must report the reviewed revision. Review/pin any newer revision before activation. Use local storage, not NFS, for the output/lock directory.

## 2. Run the new runner tests first

These exercise real child-process exit handling, missing/mismatched reports, local lock exclusion (including a collector orphaned by a killed launcher), environment cleanup, file privacy, symlink rejection, retention scope, the whole-run timeout and checker trust checks:

```bash
/usr/bin/python3 -m unittest discover -s /home/grid/oracle-health-automation/Oracle-DBA/scripts/health -p 'test_*.py' -v
```

All eight tests passed on racnode1 in 0.656 seconds on 2026-10-20, per my terminal output. Expect twenty-six tests from 2026-11-05 onward; the full set is pending on racnode1. Repeat on racnode2; stop on test failure. These are fake-collector tests, not Oracle availability tests.

## 3. One manual snapshot on each node

As grid, on racnode1 and then racnode2:

```bash
/usr/bin/python3 /home/grid/oracle-health-automation/Oracle-DBA/scripts/health/run_rac_health.py \
  --checker /home/grid/scripts/rac_health_check.py \
  --output-dir /home/grid/.local/state/oracle-health
echo "runner_exit=$?"
```

Inspect the metadata and the exact log/report it names:

```bash
cat /home/grid/.local/state/oracle-health/last-run.json
ls -lt /home/grid/.local/state/oracle-health/
```

A known compatibility or historical-alert warning can legitimately return 1. Record the finding; do not change thresholds or suppress it. An exit of 3/70, missing output, wrong database or incomplete permissions must be resolved before scheduling. Confirm no credential prompts occur and both node reports have their local alert coverage.

The collector has per-command timeouts, and the runner adds a whole-run deadline (--max-runtime). A TIMEOUT result, repeated 75 exits or a stale RUNNING record require investigation. Keep --max-runtime well below the cron interval multiplied by the number of runs you can tolerate skipping; observe real run duration before tightening it. Do not delete the lock file to bypass an active run.

## 4. Activate only after tests and manual review pass

On each node, confirm crond is active and inspect existing jobs before editing the grid user's crontab:

```bash
systemctl is-active crond
crontab -l
crontab -e
```

If no crontab exists, crontab -l can return a nonzero status; do not overwrite unrelated jobs. Check the host's cron timezone with timedatectl. UTC artifact filenames are independent of that timezone.

Add **one** entry on racnode1:

```cron
0,15,30,45 * * * * umask 077; /usr/bin/python3 /home/grid/oracle-health-automation/Oracle-DBA/scripts/health/run_rac_health.py --checker /home/grid/scripts/rac_health_check.py --output-dir /home/grid/.local/state/oracle-health > /home/grid/.local/state/oracle-health/cron-last.log 2>&1
```

Add **one** entry on racnode2, staggered seven minutes:

```cron
7,22,37,52 * * * * umask 077; /usr/bin/python3 /home/grid/oracle-health-automation/Oracle-DBA/scripts/health/run_rac_health.py --checker /home/grid/scripts/rac_health_check.py --output-dir /home/grid/.local/state/oracle-health > /home/grid/.local/state/oracle-health/cron-last.log 2>&1
```

The private directory must already exist from the manual run. cron-last.log contains only the latest trigger's launcher output; detailed snapshots are separately retained. No mail configuration is assumed. Monitor disk use; retention is age-based, not a hard size cap.

## 5. Prove operation and maintain it

After each node's next interval, verify a new completed last-run.json, fresh per-run metadata and the expected checker exit/findings. Compare one cron run with a manual run to confirm discovery works without login-profile variables. Observe duration and load before keeping the 15-minute cadence; increase the interval if needed.

Review last-run.json freshness as well as exit status. A suggested local review threshold is no completed result in 30 minutes, but this is not implemented alerting. Cron daemon, host outages and launch-before-script failures require separate monitoring.

Record node, runner/checker commit hashes, schedule and sanitized manual/cron results. Racnode1 tests/manual output are recorded below; retain Pending for racnode2 and cron until observed. Do not publish raw alert excerpts or internal identifiers without review.

Rollback: remove/comment only these health entries with crontab -e on each node. Preserve reports. Removing a schedule does not terminate an active collector; inspect it separately.

References: [Python flock](https://docs.python.org/3/library/fcntl.html), [Oracle JOB_QUEUE_PROCESSES](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/JOB_QUEUE_PROCESSES.html).

## Observed validation: racnode1, 2026-10-20

Summary of my racnode1 run (raw alert excerpts left out):

| Check | Observed result |
|---|---|
| Runner tests | All 8 passed in 0.656 seconds |
| Manual snapshot | 16:25:06–16:26:00 America/Chicago; about 53 seconds |
| Exit handling | Checker 1, runner 1, final status WARNING |
| Output | Unique log/JSON filenames and completed last-run.json recorded |
| Checker SHA-256 | 0f1d1f78fb839ceaeb017cdcfb12b10fdb3e397e1c73907379f2cc248d08d954 |
| Collection | Both OS nodes, Clusterware, database SQL/services and ASM collected; alert sample local to racnode1 |
| Findings | 0 critical, 4 warnings; not an all-clear |
| ASM | DATA/FRA/OCR mounted on both instances; listed disks ONLINE/NORMAL |
| Remaining validation | Racnode2 tests/manual collection, both-node cron operation and freshness |

Warnings to retain and investigate:
- RAC1 recorded a new ORA-29770 LMON no-progress event at 08:15:21 CDT on October 20. This is distinct from the October 19 ASM history. Current OPEN instances do not explain the earlier hang; correlate the alert, LMHB incident trace and host timeline. Root cause is not established. The Hyper-V "snail mode" cause confirmed in the [October 2026 incident reports](../../Oracle-Database-Platform-Automation/incident-reports/2026-10-18-rac26-node2-root-script-vm-freeze.md) was corrected on October 18 (native VT-x confirmed), so it is not assumed to explain this October 20 event. Tracked in [Issue 23](https://github.com/omoriwor-commits/oracle-db-platform-automation/issues/23).
- Three undated seed-datafile error lines need surrounding context; the sample reports zero future timestamps. This alone does not prove clock drift or a current missing datafile.
- One compatibility warning per node: reported 23.26.1 runtime with OL9 UEK8, with the checker flagging documented support from RU 23.26.2. Existing compatibility work remains open.

Node 2's SELinux troubleshooting processes briefly used up to 94.3% of one core in the sample. No paging was observed during sampled intervals. Neither observation establishes the hang's cause. Do not suppress these findings to obtain exit 0.

No cron execution, notification delivery, failover or restore result is established by this manual snapshot.
