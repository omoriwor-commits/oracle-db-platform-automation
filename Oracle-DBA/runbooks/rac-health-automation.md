# Automate the existing RAC health snapshot

**Updated:** 2026-11-06 (both-node 27-test results, live manual collection and first completed cron runs).
**Status:** The hardened runner's 27 fake-collector tests passed on both lab nodes as grid with Python 3.9.25. Manual collection and the first staggered cron execution completed on both nodes, preserving WARNING / exit 1. This establishes initial scheduled collection, not an all-clear or sustained monitoring reliability. The November evidence and remaining warnings are recorded below; historical October results remain separate.

Runner code/tests correspond to 0fb29c8. On racnode1 the tested checkout was base 036968c plus the reviewed incremental patch (SHA-256 937f1f112d5007de3fd9bfdb5b0146fef2723d6b1272a9a6485d787ce0b1875f); its runner/test files were compared with 0fb29c8 before cron activation. Racnode2 used a checkout of 0fb29c8. GitHub Actions [run 42171377748](https://github.com/omoriwor-commits/oracle-db-platform-automation/actions/runs/42171377748) passed on that revision, including Python 3.9 and 3.12 health tests. The checks job uses Ubuntu 24.04 for Python 3.9 compatibility. Evidence below comes from supplied lab terminal transcripts/screenshots, not remote execution by the documentation editor. Follow-up remains tracked in [Issue #24](https://github.com/omoriwor-commits/oracle-db-platform-automation/issues/24).

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
- --max-runtime (default 600 seconds) is a whole-run deadline. The collector runs in its own process group; at the deadline every member of the group receives SIGTERM, then SIGKILL after 10 seconds, so a descendant that ignores SIGTERM is still stopped. Cleanup allows up to 10 seconds after each group signal and up to 10 further seconds to reap the direct child; elapsed time can therefore exceed --max-runtime. The run records status TIMEOUT with the elapsed time and exits 70. If the collector exits normally but leaves processes in its group (for example, a command its own per-command timeout abandoned), they are stopped the same way and recorded as leftover_pids; the checker's result is kept. Any member that survives SIGKILL or cannot be signaled by this account (for example, a process in uninterruptible I/O or a setuid program) is recorded as surviving_pids, and the runner returns instead of waiting on it. A run with surviving_pids always exits 70 (RUNNER_ERROR, or TIMEOUT if the deadline was hit), never OK; checker_exit_code still records what the checker itself returned. Such a process may still hold the lock, so investigate before the next run. A descendant that starts its own session escapes the group and is not covered.
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

All eight tests passed on racnode1 in 0.656 seconds on 2026-10-20, per my terminal output. The earlier twenty-six tests all passed on racnode1 as grid with Python 3.9.25 at commit c31f788 on 2026-11-05 in 12.326 seconds. The expanded 27-test suite subsequently passed on racnode1 in 13.662 seconds with Python 3.9.25 and ResourceWarnings treated as errors (see the status evidence above). All 27 tests also passed on racnode2 at 0fb29c8 in 14.481 seconds with Python 3.9.25 and ResourceWarnings treated as errors. Stop on test failure when repeating validation. These are fake-collector tests, not Oracle availability tests.

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
0,15,30,45 * * * * umask 077; /usr/bin/python3 /home/grid/oracle-health-automation/Oracle-DBA/scripts/health/run_rac_health.py --checker /home/grid/scripts/rac_health_check.py --output-dir /home/grid/.local/state/oracle-health --max-runtime 600 > /home/grid/.local/state/oracle-health/cron-last.log 2>&1
```

Add **one** entry on racnode2, staggered seven minutes:

```cron
7,22,37,52 * * * * umask 077; /usr/bin/python3 /home/grid/oracle-health-automation/Oracle-DBA/scripts/health/run_rac_health.py --checker /home/grid/scripts/rac_health_check.py --output-dir /home/grid/.local/state/oracle-health --max-runtime 600 > /home/grid/.local/state/oracle-health/cron-last.log 2>&1
```

Create the private directory before installing the schedule; shell redirection opens cron-last.log before the runner can create its output directory:

```bash
install -d -m 700 /home/grid/.local/state/oracle-health
```

The directory must be owned by grid. cron-last.log contains only the latest trigger's launcher output; detailed snapshots are separately retained. No mail configuration is assumed. Monitor disk use; retention is age-based, not a hard size cap.

## 5. Prove operation and maintain it

After each node's next interval, verify a new completed last-run.json, fresh per-run metadata and the expected checker exit/findings. Compare one cron run with a manual run to confirm discovery works without login-profile variables. Observe duration and load before keeping the 15-minute cadence; increase the interval if needed.

Review last-run.json freshness as well as exit status. A suggested local review threshold is no completed result in 30 minutes, but this is not implemented alerting. Cron daemon, host outages and launch-before-script failures require separate monitoring.

Record node, runner/checker commit hashes, schedule and sanitized manual/cron results. Initial tests, manual collection and completed cron results for both nodes are recorded below. Repeated scheduled completion/freshness and load observation remain follow-up work. Do not publish raw alert excerpts or internal identifiers without review.

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

## Observed validation: both nodes, 2026-11-06

Self-directed lab evidence from the operator's terminal output. Both nodes used Python 3.9.25 as grid and checker revision 2026-10-19.3, SHA-256 `0f1d1f78fb839ceaeb017cdcfb12b10fdb3e397e1c73907379f2cc248d08d954`. The older racnode2 collector was preserved in a private local backup before replacement; raw logs remain on the lab hosts.

### Regression tests

| Node | Source | Result |
|---|---|---|
| racnode1 | 036968c plus reviewed patch; runner/tests match 0fb29c8 | 27 tests, 13.662 seconds, OK; run began 2026-11-06 05:53 UTC (November 5 locally) |
| racnode2 | 0fb29c8 | 27 tests, 14.481 seconds, OK; run began 2026-11-06 06:43 UTC |

Both runs used `-W error::ResourceWarning`; no ResourceWarnings appeared in the supplied output. RUNNER_ERROR, TIMEOUT and overlap-skip messages inside these tests are expected negative cases. These are fake-collector tests, not Oracle availability tests.

### Manual collection

| Node / case | UTC start–finish | Checker / runner | Findings |
|---|---|---|---|
| racnode1, database intentionally stopped | 06:03:40–06:04:40 | 2 / 2, CRITICAL | 2 critical, 4 warnings; database SQL and alert coverage incomplete |
| racnode1, after database startup | 06:32:17–06:35:00 | 1 / 1, WARNING | 0 critical, 12 warnings |
| racnode2, database open | 06:48:31–06:49:34 | 1 / 1, WARNING | 0 critical, 11 warnings |

The stopped-database result was an intentional lab state, not evidence of an unexplained crash. Subsequent SRVCTL output showed RAC1/RAC2 OPEN with RAC_RACPDB1 online on both nodes. Open-database manual runs collected OS nodes, Clusterware, database SQL/services and ASM; alert coverage was bounded and local to the executing node. Racnode2's missing local DBCA completion log was informational, not a current availability failure.

### First completed scheduled runs

crond was active on both nodes. Initially neither grid account had a crontab. Installed schedules use America/Chicago time, a 600-second maximum runtime, absolute paths and a private output directory. Racnode1 runs at :00/:15/:30/:45; racnode2 runs at :07/:22/:37/:52.

| Node | started_at (UTC) | finished_at (UTC) | Duration | Result |
|---|---|---|---|---|
| racnode1 | 2026-11-06T07:00:01.981362+00:00 | 2026-11-06T07:01:24.818417+00:00 | 82.837 seconds | Checker 1 / runner 1, WARNING; 0 critical, 11 warnings |
| racnode2 | 2026-11-06T07:07:02.846646+00:00 | 2026-11-06T07:09:41.506789+00:00 | 158.660 seconds | Checker 1 / runner 1, WARNING; 0 critical, 12 warnings |

These correspond to 01:00–01:01 and 01:07–01:09 CST. Each cron-last.log and completed last-run.json agreed on WARNING / exit 1 and the checker hash above. Per-run log/report stems retained locally:

- racnode1: `health-20261106T070001981362Z-1375414`
- racnode2: `health-20261106T070702846646Z-436531`

This verifies one completed scheduled execution per node. Subsequent cadence, freshness over time, per-run metadata/file-mode inspection and external heartbeat/notification delivery are not established by these terminal excerpts.

### Findings and remaining limits

- Eight warnings in each scheduled run concern four mounted PDBs on each instance. Their intended open-state policy remains to be confirmed; do not open them merely to clear warnings.
- Two compatibility warnings flag reported 23.26.1 runtime with OL9 UEK8. The checker's support claim still needs independent confirmation against full Grid/DB patch inventories and authoritative certification information; it is not a completed compliance assessment.
- Racnode1's scheduled run found 18 matching RAC1 alert-log lines in the lookback window. Correlate timestamps and surrounding events before declaring an active fault; matching lines are not incident counts or an established root cause.
- Racnode2's scheduled run observed CPU at or above 85% in all three sampled intervals on both nodes. Review processes and host load, then assess the 15-minute cadence; the short sample does not establish the cause.
- Manual snapshots also observed intermittent paging. Do not equate allocated swap or a short paging sample with proven thrashing. SELinux/HugePages observations do not justify automatic configuration changes.
- Local alerts remain sampled, not exhaustive. SCAN client connectivity, failover, backup recoverability, certification and sustained monitoring reliability were not tested by these health runs. Planned tablespace/RMAN coverage and overall Phase 1 completion remain separate.

The initial scheduling execution gate is evidenced; warning investigation and continued freshness/load observation remain open. No automatic repair or notifications were enabled.
