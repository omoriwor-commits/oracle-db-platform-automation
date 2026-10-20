# Daily and Weekly Database Health Checks (Oracle 26ai RAC, Multitenant)

**Last updated:** 2026-10-20
**Status:** Partly automated. Cluster, network, database, ASM, FRA and alert-log checks run in my RAC health-check script (`scripts/oracle-rac/rac_health_check.py` in the enterprise-multicloud-database-platform-lab repo), validated on my 26ai RAC lab. The SQL checks below that the script doesn't cover yet are marked **Planned**.

**Scheduled collection:** [RAC health automation](rac-health-automation.md) adds a private logging/retention runner and staggered cron activation instructions for both nodes. New runner tests and live scheduling are pending; no schedule has been activated by this change.

Many health-check lists online date from before 12c. They check one instance, read `background_dump_dest` and sum `DBA_FREE_SPACE`. On a RAC container database those checks miss most of the picture.

## Daily

| Check | How on 26ai RAC | In my script |
| ----- | --------------- | ------------ |
| Instances and database | `srvctl status database -db RAC`, `gv$instance`, `gv$pdbs` | Yes |
| Listeners, SCAN, VIPs | `srvctl status listener`, `srvctl status scan_listener`, `srvctl status vip` | Yes |
| Clusterware and ASM | `crsctl check cluster -all`, `crsctl stat res -t`, `asmcmd lsdg` | Yes |
| Alert logs (database, ASM) | ADR, from `v$diag_info` or `adrci`; old `background_dump_dest` is deprecated | Yes (node 1, last 24 hours) |
| Archiving and FRA | ARCHIVELOG mode; `v$recovery_file_dest`, `v$recovery_area_usage` | Yes |
| Tablespace usage | `CDB_TABLESPACE_USAGE_METRICS` (percent of maximum size, per container) | Planned |
| Last backups | `v$rman_backup_job_details` | Planned |
| Blocking sessions | `gv$session` | Planned |
| Invalid objects | `CDB_OBJECTS` | Planned |
| Failed scheduler jobs | `CDB_SCHEDULER_JOB_RUN_DETAILS` | Planned |
| Unusable indexes | `CDB_INDEXES`, `CDB_IND_PARTITIONS` | Planned |

## SQL for the planned checks

```sql
-- Tablespace usage as % of max size, per container
SELECT c.name container, m.tablespace_name, ROUND(m.used_percent, 1) used_pct
FROM cdb_tablespace_usage_metrics m
JOIN v$containers c ON c.con_id = m.con_id
ORDER BY used_pct DESC;

-- RMAN jobs in the last two days
SELECT start_time, input_type, status, ROUND(output_bytes/1024/1024) out_mb
FROM v$rman_backup_job_details
WHERE start_time > SYSDATE - 2
ORDER BY start_time DESC;

-- Blocking sessions across instances
SELECT inst_id, sid, blocking_instance, blocking_session, event, seconds_in_wait
FROM gv$session
WHERE blocking_session IS NOT NULL;

-- Invalid objects by container and owner
SELECT con_id, owner, object_type, COUNT(*)
FROM cdb_objects
WHERE status = 'INVALID'
GROUP BY con_id, owner, object_type;

-- Failed scheduler jobs in the last day
SELECT con_id, owner, job_name, log_date, error#
FROM cdb_scheduler_job_run_details
WHERE status = 'FAILED' AND log_date > SYSTIMESTAMP - INTERVAL '1' DAY;

-- Unusable indexes
SELECT con_id, owner, index_name FROM cdb_indexes WHERE status = 'UNUSABLE';
```

`DBA_FREE_SPACE` alone is misleading: it ignores autoextend up to `MAXBYTES`, leaves out TEMP and, in a CDB, only covers the current container.

## Weekly

| Check | Notes |
| ----- | ----- |
| Statistics | Oracle gathers them nightly in the maintenance windows. Check the job runs (`dba_autotask_client`) rather than gathering by hand, except after large data loads. |
| Indexes | Routine rebuilds rarely help and cost redo. Rebuild for a reason: an unusable index, or measured bloat after a large delete. |
| Backup restore test | `RESTORE DATABASE VALIDATE` from RMAN |
| OCR backup | `ocrconfig -showbackup` (see [OCR and OLR administration](ocr-olr-administration.md)) |
| Growth trends | Tablespace and FRA usage compared with last week |

## Not a health check

- Twice-daily AWR comparisons. AWR needs the Diagnostics Pack; use AWR or ASH when there is a performance problem, and `awrddrpt.sql` to compare two periods.
- Database refreshes. A task, not a check.
