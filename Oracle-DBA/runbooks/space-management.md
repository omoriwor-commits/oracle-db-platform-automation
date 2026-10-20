# Space Management on Oracle 26ai RAC

**Last updated:** 2026-10-20  
**Status:** Reference reviewed against Oracle 26ai documentation; SQL and exercises below are **Verify / not yet run for this publication**. No new sizing, Flashback or restore results are claimed.  
**Environment:** Independent two-node lab, RAC1/RAC2, RACPDB1, Oracle/Grid 23.26.1, Oracle Linux 9.8, shared ASM DATA/FRA/OCR. The [build runbook](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/docs/runbooks/oracle-rac/oracle26ai-2node-rac-build-runbook.md) retains the open kernel/RU compatibility and other Verify items.

## Scope and execution context

This page preserves the improved storage topics from my supplied study/review notes: object allocation, tablespace capacity, TEMP, FRA, archive volume, Flashback sizing, physical limits and shared-storage tablespace operations. Legacy examples and the review notes are not treated as proof of lab execution. Additional read-only examples are reference procedures pending validation.

Run SQL through an authorized database account. Use RACPDB1 for application objects and CDB$ROOT for database-wide recovery and parameter checks. Verify each connection with `SHOW CON_NAME`. Execute ASM tools as grid. Nothing here was executed against the lab by the documentation update.

```sql
SET LINESIZE 200 PAGESIZE 100
SHOW CON_NAME;
SELECT instance_name, host_name, version_full FROM v$instance;
```

Sizes labeled MiB/GiB divide bytes by 2^20/2^30. Allocation, occupied blocks, configured growth limits and underlying disk capacity are different measurements. Do not sum identical shared-file observations from GV$ views across RAC instances.

## 1. Database and PDB file allocation

In CDB$ROOT, report permanent and temporary allocation separately. CDB visibility depends on privileges and open containers; record which PDBs were visible.

```sql
SELECT con_id, ROUND(SUM(bytes)/POWER(1024,3), 3) allocated_gib
FROM cdb_data_files GROUP BY con_id ORDER BY con_id;

SELECT con_id, ROUND(SUM(bytes)/POWER(1024,3), 3) allocated_temp_gib
FROM cdb_temp_files GROUP BY con_id ORDER BY con_id;
```

These are allocated file sizes, not live row data, ASM consumption or a complete backup-size estimate. Redo, control files, recovery files and ASM redundancy/metadata are separate.

## 2. Tables and associated segments

Connect to RACPDB1. Enter the owner and table separately, such as SCOTT and EMP; do not enter SCOTT.EMP as the segment name. Uppercasing suits ordinary unquoted identifiers. For quoted mixed-case names, use exact stored spelling and adapt the predicates deliberately. SQL*Plus substitution accepts trusted operator input; it is not a safe interface for untrusted text.

```sql
DEFINE owner = SCOTT
DEFINE table_name = EMP

WITH segment_keys AS (
  SELECT UPPER('&&owner') owner, UPPER('&&table_name') segment_name
  FROM dual
  UNION
  SELECT owner, index_name FROM dba_indexes
  WHERE table_owner = UPPER('&&owner')
    AND table_name = UPPER('&&table_name')
  UNION
  SELECT owner, segment_name FROM dba_lobs
  WHERE owner = UPPER('&&owner') AND table_name = UPPER('&&table_name')
  UNION
  SELECT owner, index_name FROM dba_lobs
  WHERE owner = UPPER('&&owner') AND table_name = UPPER('&&table_name')
)
SELECT CASE WHEN GROUPING(s.segment_type) = 1 THEN 'TOTAL'
            ELSE s.segment_type END segment_type,
       ROUND(SUM(s.bytes)/POWER(1024,2), 3) allocated_mib
FROM dba_segments s
JOIN segment_keys k ON k.owner = s.owner AND k.segment_name = s.segment_name
GROUP BY ROLLUP(s.segment_type);

-- Inspect the actual segment/partition layout before calling a total complete.
SELECT owner, segment_name, partition_name, segment_type,
       ROUND(bytes/POWER(1024,2), 3) allocated_mib
FROM dba_segments
WHERE owner = UPPER('&&owner')
ORDER BY segment_name, partition_name;

SELECT owner, table_name, column_name, segment_name, index_name
FROM dba_lobs
WHERE owner = UPPER('&&owner') AND table_name = UPPER('&&table_name');
```

The summary includes matching table, index and LOB metadata keys without counting the same key twice. Partition/subpartition segments require checking the actual segment and LOB partition metadata; special layouts such as nested tables, IOT overflow or domain-index auxiliary objects need additional mapping. Do not label this a universal complete table-footprint calculation until checked on representative objects. Deferred segment creation can legitimately produce no allocated segment.

Largest allocations in the current PDB:

```sql
SELECT owner, segment_name, partition_name, segment_type,
       ROUND(bytes/POWER(1024,2), 2) allocated_mib
FROM dba_segments
ORDER BY bytes DESC
FETCH FIRST 20 ROWS ONLY;
```

This ranks segments, not whole tables with every dependent object. BYTES is allocated space; it is not the byte count of live rows. See [DBA_SEGMENTS](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/DBA_SEGMENTS.html).

## 3. Tablespace capacity, files and TEMP

Run in the PDB for its tablespaces:

```sql
SELECT tablespace_name, bigfile, contents, block_size,
       extent_management, segment_space_management
FROM dba_tablespaces ORDER BY tablespace_name;

SELECT tablespace_name,
       ROUND(SUM(bytes)/POWER(1024,2)) allocated_mib,
       ROUND(SUM(CASE WHEN autoextensible = 'YES' THEN maxbytes
                      ELSE bytes END)/POWER(1024,2)) configured_max_mib
FROM dba_data_files
GROUP BY tablespace_name ORDER BY tablespace_name;

SELECT tablespace_name, ROUND(used_percent, 1) used_pct
FROM dba_tablespace_usage_metrics
ORDER BY used_percent DESC;

SELECT file_id, tablespace_name, file_name,
       ROUND(bytes/POWER(1024,2)) allocated_mib,
       autoextensible, ROUND(maxbytes/POWER(1024,2)) max_mib
FROM dba_data_files
WHERE tablespace_name = UPPER('&tablespace_name');

SELECT file_id, tablespace_name, file_name,
       ROUND(bytes/POWER(1024,2)) allocated_mib
FROM dba_temp_files ORDER BY tablespace_name, file_id;
```

Configured MAXBYTES is not reserved capacity. USED_PERCENT uses maximum possible tablespace size, which can account for available underlying storage and PDB storage limits; inspect current allocation as well. In CDB$ROOT use CDB views with CON_ID and record visibility. See [DBA_TABLESPACE_USAGE_METRICS](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/DBA_TABLESPACE_USAGE_METRICS.html).

TEMP file-header accounting on the connected instance:

```sql
SELECT tablespace_name, file_id,
       ROUND(bytes_used/POWER(1024,2), 2) used_mib,
       ROUND(bytes_free/POWER(1024,2), 2) free_mib
FROM v$temp_space_header ORDER BY tablespace_name, file_id;
```

For current consumers inspect GV$TEMPSEG_USAGE with INST_ID and CON_ID. Cached/allocated TEMP is not automatically an active space shortage. Do not sum shared tempfile capacity once per instance. See [V$TEMP_SPACE_HEADER](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/V-TEMP_SPACE_HEADER.html).

DBA_FREE_SPACE alone omits growth potential and does not describe TEMP activity or every PDB. UNDO metrics also require attention to active/unexpired retention needs.

## 4. FRA quota and underlying ASM capacity

Run in CDB$ROOT. Shared FRA quota is one database-level resource, not a separate quota per RAC instance.

```sql
COLUMN name FORMAT a35
SELECT name,
       ROUND(space_limit/POWER(1024,3), 3) limit_gib,
       ROUND(space_used/POWER(1024,3), 3) used_gib,
       ROUND(space_reclaimable/POWER(1024,3), 3) reclaimable_gib,
       ROUND(100*space_used/NULLIF(space_limit,0), 1) used_pct,
       ROUND(100*(space_used-space_reclaimable)/NULLIF(space_limit,0), 1)
         nonreclaimable_pct,
       number_of_files
FROM v$recovery_file_dest;

SELECT file_type, percent_space_used, percent_space_reclaimable, number_of_files
FROM v$recovery_area_usage
ORDER BY percent_space_used DESC;
```

Track both gross use and nonreclaimable use, storage headroom and growth rate. Reclaimable files may be eligible for Oracle-managed deletion, but this is not reserved free disk or permission for manual deletion. Protect standby, GoldenGate capture, recovery and restore-point needs. NULL percentages require checking whether FRA/quota is configured. The RAC health script revision 2026-10-19.3 reports the nonreclaimable percentage; this page adds gross use for context.

As grid:

```bash
asmcmd lsdg
```

Compare usable ASM capacity with all databases sharing the group. Raising the FRA quota does not create storage. Never remove archive/backup files with OS or ASMCMD deletion as routine space cleanup. See [V$RECOVERY_FILE_DEST](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/V-RECOVERY_FILE_DEST.html) and the [RMAN runbook](rman-backup-automation.md).

## 5. Archive volume by day and RAC thread

Use BLOCKS times BLOCK_SIZE, date comparisons on date columns and chronological sorting. Choose the actual archive destination after inspecting it; DEST_ID 1 is not universal.

```sql
SELECT dest_id, status, destination, target
FROM v$archive_dest
WHERE status <> 'INACTIVE'
ORDER BY dest_id;

DEFINE archive_dest_id = 1

WITH logs AS (
  SELECT resetlogs_change#, thread#, sequence#,
         MIN(completion_time) completed_at,
         MAX(blocks * block_size) bytes
  FROM v$archived_log
  WHERE dest_id = &&archive_dest_id
    AND archived = 'YES'
    AND completion_time IS NOT NULL
    AND resetlogs_change# = (SELECT resetlogs_change# FROM v$database)
  GROUP BY resetlogs_change#, thread#, sequence#
)
SELECT TRUNC(completed_at) day, thread#,
       GROUPING(TRUNC(completed_at)) all_days,
       GROUPING(thread#) all_threads,
       COUNT(*) logs, ROUND(SUM(bytes)/POWER(1024,3), 3) gib
FROM logs
WHERE completed_at >= TRUNC(SYSDATE) - 7
GROUP BY ROLLUP(TRUNC(completed_at), thread#)
ORDER BY day NULLS LAST, thread# NULLS LAST;
```

Archive/copy/restore operations can create duplicate control-file rows. This query groups by incarnation, thread and sequence for one destination before aggregation, using the first retained completion timestamp. It reports logical archived-log volume, not current FRA occupancy or exact redo-generation timing. Restored metadata and aged-out control-file records can affect completeness. The date window includes the current partial day plus seven preceding midnight boundaries; choose an explicit closed interval when comparing full days. GROUPING flags identify daily and grand totals. See [V$ARCHIVED_LOG](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/V-ARCHIVED_LOG.html).

## 6. Flashback sizing — planned exercise

Archive volume is not an equality for Flashback volume. Flashback uses block images; measure a representative workload and budget alongside backups and archives. A normal retention target is not a guaranteed window. Guaranteed restore points can pin required logs and exhaust available space.

Read-only checks in CDB$ROOT:

```sql
SELECT name, log_mode, flashback_on FROM v$database;
SHOW PARAMETER db_recovery_file_dest
SHOW PARAMETER db_flashback_retention_target

SELECT oldest_flashback_time, retention_target,
       ROUND(flashback_size/POWER(1024,2)) current_mib,
       ROUND(estimated_flashback_size/POWER(1024,2)) estimated_mib
FROM v$flashback_database_log;
```

The estimate applies to the configured retention and observed workload. An absent or unrepresentative estimate does not establish sufficient space. Re-measure after changing retention; do not assume linear scaling. No current Flashback state or current FRA-used value is established by the supplied notes.

Optional configuration example, **not executed**: first confirm ARCHIVELOG, recoverable backups, shared storage, exact-release prerequisites and acceptable storage budget. Run in the correct CDB context with an approved lab change:

```sql
ALTER SYSTEM SET db_flashback_retention_target = 1440 SCOPE=BOTH SID='*';
ALTER DATABASE FLASHBACK ON;
```

After representative activity, retain the estimate and actual oldest recoverable time. The planned restore-point exercise needs a separate coordinated RAC shutdown/mount/recovery/open plan and explicit validation; do not rewind this working cluster merely to collect sizing output. Flashback does not replace backups or recover a physically deleted datafile. Do not claim a successful Flashback restore from these examples.

Sources: [Flashback configuration and restore points](https://docs.oracle.com/en/database/oracle/oracle-database/26/bradv/using-flasback-database-restore-points.html), [V$FLASHBACK_DATABASE_LOG](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/V-FLASHBACK_DATABASE_LOG.html).

## 7. Physical limits: correct the legacy figures

Oracle's 26ai reference gives the following platform-dependent upper bounds; inspect actual configuration rather than provisioning to a theoretical maximum.

| Item | Reference boundary |
|---|---|
| Smallfile | Approximately 2^22 blocks per file; up to 1,023 files per tablespace |
| Bigfile | One file, approximately 2^32 blocks; about 32 TiB at 8 KiB or 128 TiB at 32 KiB |
| Smallfile file size | About 32 GiB at 8 KiB; about 128 GiB at 32 KiB, subject to exact/platform limits |
| Database files | Up to 65,533, also constrained by OS, block size and DB_FILES |
| Block size | Minimum 2 KiB; maximum OS-dependent and never above 32 KiB |
| Redo file | Minimum 4 MB; maximum OS-dependent, typically 2 TB, not 2 GB |
| Control file | Maximum 201,031,680 logical blocks; do not reuse the old 25,000-times-block-size assertion |

Do not prescribe one universal redo log-switch interval. Measure redo rate, recovery objectives, archiving/checkpoint behavior and available capacity. DB_FILES is static and must be consistent across RAC instances; changing it is a planned restart/configuration task.

```sql
SHOW PARAMETER db_block_size
SELECT inst_id, value FROM gv$parameter
WHERE name = 'db_files' ORDER BY inst_id;
SELECT tablespace_name, bigfile FROM dba_tablespaces ORDER BY tablespace_name;
SELECT property_name, property_value FROM database_properties
WHERE property_name = 'DEFAULT_TBS_TYPE';
```

26ai DBCA templates default newly created databases to bigfile tablespaces; upgraded databases retain their existing type. Do not generalize this to every 23ai installation or assume the current default without checking.

Sources: [Physical Database Limits](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/physical-database-limits.html), [DB_FILES](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/DB_FILES.html), [Managing Tablespaces](https://docs.oracle.com/en/database/oracle/oracle-database/26/admin/managing-tablespaces.html).

## 8. Shared-storage tablespace exercise — Verify

Use RACPDB1 and an isolated disposable tablespace name. Confirm shared capacity as grid before each growth operation. As oracle, check the effective OMF destination and existing names:

```sql
ALTER SESSION SET CONTAINER = RACPDB1;
SHOW CON_NAME;
SHOW PARAMETER db_create_file_dest
SELECT tablespace_name, bigfile FROM dba_tablespaces
WHERE tablespace_name IN ('SPACE_LAB_BIG', 'SPACE_LAB_SMALL');
```

No-path DATAFILE examples require a verified shared OMF destination such as +DATA. If that prerequisite is not met, stop and configure the approved shared destination separately. A local /u01 datafile path is unsuitable for a normal shared RAC datafile unless that path is genuinely shared on all nodes.

The following are separate **write operations**, not a block to paste during health checking:

```sql
CREATE BIGFILE TABLESPACE space_lab_big
  DATAFILE SIZE 100M AUTOEXTEND ON NEXT 100M MAXSIZE 2G;

ALTER TABLESPACE space_lab_big RESIZE 1G;
ALTER TABLESPACE space_lab_big AUTOEXTEND ON NEXT 100M MAXSIZE 4G;

-- Separate smallfile example; do not run ADD DATAFILE against the bigfile.
CREATE SMALLFILE TABLESPACE space_lab_small
  DATAFILE SIZE 100M AUTOEXTEND ON NEXT 100M MAXSIZE 2G;
ALTER TABLESPACE space_lab_small ADD DATAFILE SIZE 100M
  AUTOEXTEND ON NEXT 100M MAXSIZE 2G;
```

Inspect DBA_DATA_FILES to verify the generated +DATA paths and actual attributes. Bigfile growth uses its existing file; smallfile can add files. For a confirmed existing file, ALTER DATABASE DATAFILE with its exact file ID/name can resize it; shrinking is constrained by allocated blocks/high-water marks.

Before cleanup, confirm the PDB, exact test names, contents, quotas, user defaults and dependencies. Obtain any required recoverable backup. Never add CASCADE CONSTRAINTS automatically to bypass an unexplained dependency.

```sql
SELECT owner, segment_type, COUNT(*) segments
FROM dba_segments
WHERE tablespace_name IN ('SPACE_LAB_BIG', 'SPACE_LAB_SMALL')
GROUP BY owner, segment_type;

SELECT username, default_tablespace FROM dba_users
WHERE default_tablespace IN ('SPACE_LAB_BIG', 'SPACE_LAB_SMALL');

SELECT username, tablespace_name, bytes, max_bytes FROM dba_ts_quotas
WHERE tablespace_name IN ('SPACE_LAB_BIG', 'SPACE_LAB_SMALL');
```

Cleanup is deliberately outside the example block. Only after those checks, drop the exact disposable tablespace using the matching release's DROP TABLESPACE procedure and retain results. INCLUDING CONTENTS AND DATAFILES deletes data; CASCADE CONSTRAINTS adds further effects. Do not use these against retained application tablespaces.

Locally managed tablespaces do not need routine COALESCE. Reference: [Managing Tablespaces](https://docs.oracle.com/en/database/oracle/oracle-database/26/admin/managing-tablespaces.html) and [Using Oracle Managed Files](https://docs.oracle.com/en/database/oracle/oracle-database/26/admin/using-oracle-managed-files.html).

## 9. Reclaiming space and memory context

Deleting rows does not necessarily reduce allocated segment or datafile size. Distinguish reusable space within a segment, free extents within a tablespace and capacity returned to ASM. Assess object type, row movement, locks, indexes, high-water marks and recovery before a shrink/move/resize operation; no generic reclaim command is approved by this page.

Use the existing health check for interval CPU/paging observations. Record free -m, vmstat intervals, HugePages/THP and actual SGA/PGA configuration before changing memory. Allocated swap alone does not establish active paging. File free space and database buffer capacity are different resources. Memory sizing and HugePages remain separate exercises in the build runbook.

## 10. Evidence to add after the lab

| Area | Evidence still required |
|---|---|
| Object sizes | Container, owner/table, layout, segment rows and reconciled totals |
| Capacity | Allocated/max sizes, tablespace metrics, TEMP and ASM headroom |
| FRA | Quota, gross/nonreclaimable use, file categories and timestamp |
| Archive volume | Destination, incarnation, per-thread/day results and coverage limits |
| Flashback | Actual state, workload period, retention/estimate and separate recovery outcome |
| Tablespace exercise | OMF destination, shared file paths, growth results and checked cleanup |

Retain sanitized output with timestamps, versions and container/instance identity. Never insert expected output as observed results. Update individual sections to Verified only after executing and checking their evidence; this publication preserves reference knowledge, not a new completed recovery exercise.

## Provenance and related material

Adapted from my supplied storage review notes, which included legacy DBA Genesis material and AI-generated corrections. The old article wording and transient chat/usage-limit text are not republished as an authoritative runbook. Oracle 26ai documentation is linked next to the reviewed topics. Corrections include file-count/control-file/redo limits, DBCA bigfile defaults, dual FRA metrics, archive-record deduplication and explicit shared-OMF prerequisites.

- [Oracle DBA runbook index](README.md)
- [Daily and weekly checks](database-health-checks.md)
- [RMAN backup automation](rman-backup-automation.md)
- [RAC health script and coverage](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/scripts/README.md)
