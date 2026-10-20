# RMAN Backup Automation on a Two-Node RAC

**Last updated:** 2026-10-19
**Status:** Draft. The script passes a bash syntax check; it has not yet been run against my 26ai RAC lab. Steps marked **Verify** are still to do.

Script: [`scripts/rman/rman_backup.sh`](../scripts/rman/rman_backup.sh)

## Design

| Decision | Why |
| -------- | --- |
| Back up to the Fast Recovery Area (`+FRA`, shared ASM) | Either node can restore. A backup on one node's local disk can't be used from the other. |
| Weekly incremental level 0, daily level 1, archivelogs every 4 hours | Less load than daily full backups; block change tracking keeps level 1 fast. |
| Retention, compression, parallelism and deletion policy set once with `CONFIGURE` | The script stays short, and `SHOW ALL` documents the policy. |
| Archivelog deletion policy instead of `DELETE INPUT` | Archivelogs are only removed once backed up; a standby or GoldenGate Extract would otherwise lose logs it still needs. |
| `DELETE OBSOLETE` after the backup succeeds | Never remove old backups before a new one exists. |
| Error check on RMAN's exit code and the `RMAN-00569` error-stack banner in the log | Catches failed commands without treating informational `RMAN-08xxx` warnings as failures. |
| `flock` lock, instance check, syslog messages, log cleanup | One backup at a time, a clear failure when the local instance is down, and a trail outside the log file. |

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
/home/oracle/rman/rman_backup.sh 0; echo "exit=$?"
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
0 1 * * 0    /home/oracle/rman/rman_backup.sh 0
0 1 * * 1-6  /home/oracle/rman/rman_backup.sh 1
30 */4 * * * /home/oracle/rman/rman_backup.sh arch
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

- The cron entries are on racnode1 only. If node 1 is down, the script exits with code 2 and no backup runs. A next step is to schedule on both nodes, or connect through a dedicated backup service.
- Basic compression costs CPU on 2-vCPU VMs. Watch backup duration.

## Common mistakes in simple backup scripts

- Writing backups to a node's local disk in RAC.
- Running `DELETE OBSOLETE` before the new backup.
- `BACKUP ARCHIVELOG ALL DELETE INPUT` on a database with a standby or GoldenGate capture.
- Using `%u` alone in the format string; `%U` is unique per piece.
- Twice-daily full backups instead of incremental levels.
- Scheduled scripts that prompt for passwords (`rman target sys@db`). Use OS authentication or a wallet.
