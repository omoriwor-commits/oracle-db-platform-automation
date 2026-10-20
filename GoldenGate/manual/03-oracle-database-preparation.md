# 03 — Oracle Database Preparation

**Scope:** Oracle-to-Oracle replication prerequisites: CDB/PDB identity, redo and archive configuration, supplemental logging, credentials and integrated capture readiness. Commands that alter databases require separate approval and recorded results.

## 1. Preparation boundaries

Integrated Extract needs supported redo/capture configuration and enough supplemental columns to identify affected rows. It also depends on source database privileges and a valid capture/initial-load position. Replicat needs a compatible target schema and appropriate apply privileges. The target does not automatically require identical capture-side logging unless reverse replication or another feature requires it.

**Do not configure unconditional ALL-column logging or blanket DBA grants merely to make an initial test pass.** Choose logging and grants for the actual object types, source version and topology.

[Oracle transaction-log requirements](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/prepare-transaction-logs-settings-and-requirements-ogg-oracle.html).

## 2. Database inventory (read-only)

Use the intended Oracle SQL*Plus/SQLcl session. For CDB-level queries and parameter changes, confirm the container and database identity before execution.

```sql
SHOW CON_NAME;
SHOW USER;

SELECT name, db_unique_name, database_role, open_mode, log_mode,
       force_logging, supplemental_log_data_min
FROM v$database;

SHOW PARAMETER enable_goldengate_replication;

-- CDB administrative context when applicable:
SELECT con_id, name, open_mode FROM v$pdbs ORDER BY con_id;
```

`LOG_MODE` reports archival mode; `FORCE_LOGGING` is distinct; `SUPPLEMENTAL_LOG_DATA_MIN` does not prove that all keys needed by GoldenGate are being logged.

## 3. Source table keys and logging inventory

In the approved PDB, replace `APP_SCHEMA` with the actual schema identifier:

```sql
SELECT owner, table_name, constraint_name, constraint_type, status
FROM dba_constraints
WHERE owner = 'APP_SCHEMA'
  AND constraint_type IN ('P','U')
ORDER BY table_name, constraint_type;

SELECT owner, table_name, log_group_name, log_group_type, always
FROM dba_log_groups
WHERE owner = 'APP_SCHEMA'
ORDER BY table_name, log_group_name;

SELECT owner, table_name, log_group_name, column_name, position
FROM dba_log_group_columns
WHERE owner = 'APP_SCHEMA'
ORDER BY table_name, log_group_name, position;
```

Target updates/deletes require dependable row-identification keys and compatible target data. Filtering, column transformations, parallel scheduling, supplemental logging and source/target definitions must be assessed as one design.

## 4. Redo archiving and force logging

### Read-only checks

```sql
ARCHIVE LOG LIST;
SELECT log_mode, force_logging FROM v$database;
```

Changing ARCHIVELOG mode may require downtime and coordination with RMAN, Data Guard and recovery policy. **Do not insert an unconditional ARCHIVELOG conversion script into a live DBA runbook.**

When required and approved, Oracle documents:

```sql
-- DATABASE CHANGE: evaluate redo overhead and downstream impacts.
ALTER DATABASE FORCE LOGGING;
```

Record pre-change state, instance/database scope, post-change validation and any effect on bulk-load performance or standby operations.

## 5. GoldenGate replication initialization parameter

Inspect first:

```sql
SHOW PARAMETER enable_goldengate_replication;
```

Oracle documents enabling the database functionality used by GoldenGate for appropriate source/target environments:

```sql
-- CHANGE CONTROL REQUIRED; verify supported scope and initialization settings.
ALTER SYSTEM SET enable_goldengate_replication=TRUE SCOPE=BOTH SID='*';
```

The `SID='*'` and `SCOPE` options must match the actual RAC/single-instance topology and parameter support. Recheck all intended instances/containers and parameter persistence.

[Oracle source/target database setup](https://docs.oracle.com/en/database/goldengate/core/26/ggmah/task-1-configure-source-and-target-databases.html).

## 6. Supplemental logging strategy

Oracle redo may not otherwise contain every unchanged key column needed for logical replication. Choose the minimum suitable database, schema or table logging strategy and estimate extra redo volume.

### Database-level logging (when appropriate)

```sql
-- CHANGE CONTROL REQUIRED:
ALTER DATABASE ADD SUPPLEMENTAL LOG DATA;
```

Oracle AI Database 26ai also documents newer subset database replication logging alternatives, including PDB-specific usage. Select the vendor-supported option for the actual database release/container; do not run multiple alternatives blindly.

### Table-level GoldenGate commands

Run after supported Admin Client database login:

```text
DBLOGIN USERIDALIAS gg_source
ADD TRANDATA pdb1.app_schema.orders
INFO TRANDATA pdb1.app_schema.orders
```

### Schema-level alternative

```text
ADD SCHEMATRANDATA pdb1.app_schema
INFO SCHEMATRANDATA pdb1.app_schema
```

Schema-level logging may cover new tables and DDL replication scenarios; table-level logging can limit scope. Verify keys, object naming, permissions, logged column sets and the deployed release before selecting a command.

[Oracle ADD TRANDATA](https://docs.oracle.com/en/database/goldengate/core/26/gclir/add-trandata.html).

## 7. Service, operating-system and database identity separation

| Identity | Function |
|---|---|
| Linux GoldenGate user | Owns approved software/runtime files |
| Service administrator | Controls GoldenGate MA services and process configuration |
| Source database account | Capture registration, appropriate logging/capture privileges |
| Target database account | Apply operations against mapped target objects |
| Application schema owner | Owns source/target table definitions |

Oracle Database 19c and Oracle AI Database 26ai differ in privilege-granting procedures. In supported earlier releases, inspect `DBMS_GOLDENGATE_AUTH.GRANT_ADMIN_PRIVILEGE`; Oracle AI Database 26ai has documented `OGG_CAPTURE`/`OGG_APPLY` privilege models. **Do not use a single universal C## account or DBA grant script across database versions.**

Document each identity's container, privilege scope, credential rotation, password policy and account ownership; keep secret values out of GitHub.

## 8. Database credential aliases

Create source and target DB Connections through Administration Service with distinct credential aliases and correctly scoped service names. Validate actual connection targets.

```text
DBLOGIN USERIDALIAS gg_source
```

The alias is illustrative. It needs to be configured first. Do not place database passwords in source-controlled commands, shell history or screenshots.

## 9. Integrated capture readiness

After an authorized database login:

```sql
SELECT capture_name, status FROM dba_capture ORDER BY capture_name;
```

Zero rows **before** registration can be normal. After registering the intended Integrated Extract, confirm the correct capture exists and investigate reported state in the source/mining database. This query cannot prove that source trails contain records or that Replicat applied changes.

## 10. Operational verification checklist

- [ ] Confirm source/target release compatibility and database role.
- [ ] Record CDB/PDB and database service context.
- [ ] Record archived redo availability and retention.
- [ ] Validate force logging and supplemental logging requirements.
- [ ] Inventory primary/unique keys and selected replication objects.
- [ ] Approve minimum source capture and target apply privileges.
- [ ] Confirm DB aliases connect to intended containers.
- [ ] Define source capture starting position and consistent initial-load method.
- [ ] Retain executed SQL, reports and any errors in a sanitized project evidence folder.

### Evidence status

This page provides reference commands and verification criteria. No new database change or source/target validation has been performed as part of this rewrite. An actual deployment record should show before/after SQL output, container identity, change approval and successful subsequent capture.

## Oracle references

- [Transaction log settings](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/prepare-transaction-logs-settings-and-requirements-ogg-oracle.html)
- [Configure source and target databases](https://docs.oracle.com/en/database/goldengate/core/26/ggmah/task-1-configure-source-and-target-databases.html)
- [ADD TRANDATA](https://docs.oracle.com/en/database/goldengate/core/26/gclir/add-trandata.html)
- [Prerequisites before Extract and Replicat](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/configure-ogg-adding-extract-and-replicat.html)

**Next:** [04 — Integrated Extract and Source Trails](04-integrated-extract-and-source-trails.md)
