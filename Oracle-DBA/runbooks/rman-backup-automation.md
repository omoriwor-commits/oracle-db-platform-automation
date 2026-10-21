# RMAN Backup Automation on a Two-Node RAC

**Last updated:** 2026-10-21
**Status:** Draft. The launcher has failure-injection tests using fake Oracle tools; live backup and restore validation on the 26ai RAC lab remain pending. Steps marked **Verify** are still to do.

Script: [`scripts/rman/rman_backup.sh`](../scripts/rman/rman_backup.sh)

## Design

| Decision | Why |
| -------- | --- |
| Back up to the Fast Recovery Area (`+FRA`, shared ASM) | Either node can restore. A backup on one node's local disk can't be used from the other. |
| Weekly incremental level 0, daily level 1, archivelogs every 4 hours | Less load than daily full backups; block change tracking keeps level 1 fast. |
| Retention, compression, parallelism and deletion policy set once with `CONFIGURE` | The script stays short, and `SHOW ALL` documents the policy. |
| No deletion by default | Review recovery retention and actual Data Guard/GoldenGate consumers before enabling cleanup. A backup count alone does not prove downstream consumption. |
| Opt-in `--cleanup` in a separate RMAN invocation after backup success | Failed backup commands cannot enter the cleanup stage. Review `REPORT OBSOLETE` first. |
| Error check on RMAN's exit code and the `RMAN-00569` error-stack banner in the log | Catches failed commands without treating informational `RMAN-08xxx` warnings as failures. |
| Private local lock/logs and SQL identity checks | Exclude overlapping runs on one host; confirm the expected database, SID and open mode. Cross-node exclusion is not implemented. |

## One-time setup

RMAN settings (as oracle, `rman target /`):

```sql
CONFIGURE RETENTION POLICY TO RECOVERY WINDOW OF 7 DAYS;
CONFIGURE CONTROLFILE AUTOBACKUP ON;
CONFIGURE BACKUP OPTIMIZATION ON;
CONFIGURE DEVICE TYPE DISK PARALLELISM 2 BACKUP TYPE TO COMPRESSED BACKUPSET;
CONFIGURE ARCHIVELOG DELETION POLICY TO BACKED UP 1 TIMES TO DISK;
CONFIGURE SNAPSHOT CONTROLFILE NAME TO '+DATA/RAC/snapcf_RAC.f';
SHOW ALL;
```

In RAC the snapshot control file must be on shared storage; on a node's local disk, backups can fail with `ORA-00245`. Basic compression doesn't need the Advanced Compression option.

Block change tracking (`sqlplus / as sysdba`):

```sql
ALTER DATABASE ENABLE BLOCK CHANGE TRACKING USING FILE '+DATA';
SELECT status, filename FROM v$block_change_tracking;
```

## Install and test

```bash
mkdir -p /home/oracle/rman
chmod 750 /home/oracle/rman/rman_backup.sh
RMAN_SID=RAC1 /home/oracle/rman/rman_backup.sh 0; echo "exit=$?"
```

Exit codes: 0 success, 1 RMAN errors, 2 local instance not open, 3 usage, 4 another backup already running.

Prove the backup can be restored, not only that it was written:

```bash
rman target / <<'EOF'
LIST BACKUP SUMMARY;
RESTORE DATABASE VALIDATE;
RESTORE ARCHIVELOG ALL VALIDATE;
EOF
```

**Verify** the first level 0 run, the validate output and the RMAN `SHOW ALL` settings.

## Schedule (oracle's crontab on racnode1)

```text
0 1 * * 0    RMAN_SID=RAC1 /home/oracle/rman/rman_backup.sh 0
0 1 * * 1-6  RMAN_SID=RAC1 /home/oracle/rman/rman_backup.sh 1
30 */4 * * * RMAN_SID=RAC1 /home/oracle/rman/rman_backup.sh arch
```

## Monitoring

```sql
SELECT start_time, input_type, status, ROUND(output_bytes/1024/1024) out_mb
FROM v$rman_backup_job_details
WHERE start_time > SYSDATE - 2
ORDER BY start_time DESC;

SELECT * FROM v$recovery_area_usage;
```

My FRA is 25 GB on a 30 GB disk group. Check usage after the first week.

## Known limits

- Cron runs on racnode1 only. A down host cannot launch cron and produces no script exit code. Use external freshness monitoring. Do not schedule both nodes until cluster-wide coordination is implemented; the lock is local. If the host is up but the selected instance or identity check fails, the launcher returns 2.
- Basic compression costs CPU on 2-vCPU VMs. Watch backup duration.

## Common mistakes in simple backup scripts

- Writing backups to a node's local disk in RAC.
- Running `DELETE OBSOLETE` before the new backup.
- `BACKUP ARCHIVELOG ALL DELETE INPUT` on a database with a standby or GoldenGate capture.
- Using `%u` alone in the format string; `%U` is unique per piece.
- Twice-daily full backups instead of incremental levels.
- Scheduled scripts that prompt for passwords (`rman target sys@db`). Use OS authentication or a wallet.


## Cleanup and validation gates

Backups run without deletion by default. `--cleanup` is a separate, explicit opt-in after successful backup execution; it runs `DELETE NOPROMPT OBSOLETE`. Oracle documents that this command determines obsolescence from the backup retention policy, not the archived-log deletion policy. Do not rely on `BACKED UP 1 TIMES` to protect every downstream consumer. Review `REPORT OBSOLETE`, capture/standby requirements and restore objectives before choosing a policy. The setup example is for this lab, not a universal Data Guard or GoldenGate policy.

Logs and the local lock are kept in a user-owned 0700 directory; logs use 0600. No automatic log deletion is performed. Set `RMAN_LOG_DIR`, `RMAN_DB_UNIQUE_NAME`, `RMAN_SID` and `ORACLE_HOME` for another approved lab. Backup storage in shared ASM remains in the cluster failure domain; an independent backup copy and a real restore/recovery exercise are still needed.

Local tests: `python3 -m unittest discover -s Oracle-DBA/scripts/rman/tests -v`. These prove orchestration behavior, not Oracle backup or recovery. Live acceptance remains: retain SHOW ALL, level-0 output, restore validation, an isolated restore/recovery result and a freshness test.

Oracle references: [DELETE](https://docs.oracle.com/en/database/oracle/oracle-database/26/rcmrf/DELETE.html), [RMAN command sequencing](https://docs.oracle.com/en/database/oracle/oracle-database/26/bradv/managing-recovery-catalog.html).
