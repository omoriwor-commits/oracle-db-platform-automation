# Automate the existing RAC health snapshot

**Updated:** 2026-10-20.  
**Status:** Implementation prepared; new runner tests and live cron validation not yet executed. No schedule has been activated by this change.

## What runs

The runner invokes the existing read-only [RAC checker](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/scripts/oracle-rac/rac_health_check.py), revision 2026-10-19.3. It does not duplicate its SQL or change its thresholds.

Coverage remains OS, Clusterware, listeners/network, database/PDB, ASM, FRA and local bounded alert logs. Run on both nodes to collect both local histories. Cluster-wide observations are intentionally repeated. Tablespace, RMAN-job, blocking-session, invalid-object and failed-Scheduler-job SQL listed as planned in the [health runbook](database-health-checks.md) remain separate work.

Use the OS scheduler for this snapshot: it must be able to launch while Oracle is unavailable. Database discovery may then return CONFIG_ERROR, which is a failed collection, never an all-clear. DBMS_SCHEDULER remains suitable for later database-only checks; do not schedule this collector through both systems.

## Files and controls

- [run_rac_health.py](../scripts/health/run_rac_health.py): password-free launcher using existing authorized OS authentication.
- [test_run_rac_health.py](../scripts/health/test_run_rac_health.py): Linux tests with disposable fake collectors, no Oracle.
- Local exclusive lock prevents overlapping normal runs; inherited lock descriptor stays held by the collector if the launcher exits.
- Logs/reports are private: directory 0700, artifacts 0600. A SHA-256 identifies the checker version used.
- Exit codes 0/1/2/3 preserve OK/warning/critical/configuration-error outcomes. Missing or invalid JSON cannot produce OK.
- Exit 70 means runner/report failure; 75 means an overlapping run was skipped. Skips do not overwrite the previous run status.
- Matching owned regular artifacts older than 30 days are removed under the lock. Unrelated files and symlinks are not pruned. Adjust --keep-days before retaining audit evidence longer.
- last-run.json records RUNNING before launch and completion afterward; per-run metadata preserves completed history. Unexpected termination can leave RUNNING as evidence of interruption.

No automatic restart, repair, account changes, backup deletion or external notification is included. This is scheduled collection, not an alert-delivery system. A completely down VM/host cannot run cron; external heartbeat monitoring is a separate requirement.

## 1. Stage on both nodes as grid

Keep the existing grid authorization; do not add DBA/ASM privileges to make reports green. Stage reviewed checkouts at these example paths:

| Repository | Local path |
|---|---|
| oracle-db-platform-automation | /home/grid/src/oracle-db-platform-automation |
| enterprise-multicloud-database-platform-lab | /home/grid/src/enterprise-multicloud-database-platform-lab |

Use the feature branch for testing, or main after merge. The code and tests must be checked out together. Install nothing as root. Confirm /usr/bin/python3 exists, then inspect identity/paths:

```bash
whoami
/usr/bin/python3 --version
ls -l /home/grid/src/oracle-db-platform-automation/Oracle-DBA/scripts/health/
/usr/bin/python3 /home/grid/src/enterprise-multicloud-database-platform-lab/scripts/oracle-rac/rac_health_check.py --version
```

The collector must report the reviewed revision. Review/pin any newer revision before activation. Use local storage, not NFS, for the output/lock directory.

## 2. Run the new runner tests first

These exercise real child-process exit handling, missing/mismatched reports, local lock exclusion, environment cleanup, file privacy, symlink rejection and retention scope:

```bash
/usr/bin/python3 -m unittest discover -s /home/grid/src/oracle-db-platform-automation/Oracle-DBA/scripts/health -p 'test_*.py' -v
```

Stop on test failure. These tests have not been run in this session because no usable execution environment is available.

## 3. One manual snapshot on each node

As grid, on racnode1 and then racnode2:

```bash
/usr/bin/python3 /home/grid/src/oracle-db-platform-automation/Oracle-DBA/scripts/health/run_rac_health.py \
  --checker /home/grid/src/enterprise-multicloud-database-platform-lab/scripts/oracle-rac/rac_health_check.py \
  --output-dir /home/grid/.local/state/oracle-health
echo "runner_exit=$?"
```

Inspect the metadata and the exact log/report it names:

```bash
cat /home/grid/.local/state/oracle-health/last-run.json
ls -lt /home/grid/.local/state/oracle-health/
```

A known compatibility or historical-alert warning can legitimately return 1. Record the finding; do not change thresholds or suppress it. An exit of 3/70, missing output, wrong database or incomplete permissions must be resolved before scheduling. Confirm no credential prompts occur and both node reports have their local alert coverage.

The collector has per-command timeouts, not a whole-run deadline. A hung runner holds the local lock; repeated 75 exits or a stale RUNNING record require investigation. Do not delete the lock file to bypass an active run.

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
0,15,30,45 * * * * umask 077; /usr/bin/python3 /home/grid/src/oracle-db-platform-automation/Oracle-DBA/scripts/health/run_rac_health.py --checker /home/grid/src/enterprise-multicloud-database-platform-lab/scripts/oracle-rac/rac_health_check.py --output-dir /home/grid/.local/state/oracle-health > /home/grid/.local/state/oracle-health/cron-last.log 2>&1
```

Add **one** entry on racnode2, staggered seven minutes:

```cron
7,22,37,52 * * * * umask 077; /usr/bin/python3 /home/grid/src/oracle-db-platform-automation/Oracle-DBA/scripts/health/run_rac_health.py --checker /home/grid/src/enterprise-multicloud-database-platform-lab/scripts/oracle-rac/rac_health_check.py --output-dir /home/grid/.local/state/oracle-health > /home/grid/.local/state/oracle-health/cron-last.log 2>&1
```

The private directory must already exist from the manual run. cron-last.log contains only the latest trigger's launcher output; detailed snapshots are separately retained. No mail configuration is assumed. Monitor disk use; retention is age-based, not a hard size cap.

## 5. Prove operation and maintain it

After each node's next interval, verify a new completed last-run.json, fresh per-run metadata and the expected checker exit/findings. Compare one cron run with a manual run to confirm discovery works without login-profile variables. Observe duration and load before keeping the 15-minute cadence; increase the interval if needed.

Review last-run.json freshness as well as exit status. A suggested local review threshold is no completed result in 30 minutes, but this is not implemented alerting. Cron daemon, host outages and launch-before-script failures require separate monitoring.

Record test results, node, runner/checker commit hashes, schedule and sanitized manual/cron results before changing this status to Verified. Do not publish raw alert excerpts or internal identifiers without review.

Rollback: remove/comment only these health entries with crontab -e on each node. Preserve reports. Removing a schedule does not terminate an active collector; inspect it separately.

References: [Python flock](https://docs.python.org/3/library/fcntl.html), [Oracle JOB_QUEUE_PROCESSES](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/JOB_QUEUE_PROCESSES.html).
