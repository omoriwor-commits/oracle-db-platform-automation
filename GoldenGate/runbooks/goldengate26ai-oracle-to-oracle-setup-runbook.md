# Oracle GoldenGate 26ai Setup Runbook

**Author:** Rotimi Ezekiel  
**Last revised:** 2026-10-16  
**Status:** Draft — reviewed against Oracle documentation; not yet validated end to end in this lab.  
**Scope:** Lab only. This is a proposed procedure, not evidence of a completed build.

## Architecture and assumptions

One-way Oracle 26ai PDB-to-PDB replication. A single GoldenGate 26ai Microservices deployment on the target host runs remote Integrated Extract and local Integrated Replicat. Integrated capture uses the source database's log-mining server; the hub does not directly read source redo files.

| Item | Value |
|---|---|
| Source | `srchost`, Oracle 26ai, PDB service `srcpdb`, container `SRCPDB`, schema `APP` |
| Target | `tgthost`, Oracle 26ai, PDB service `tgtpdb`, container `TGTPDB`, schema `APP` |
| GoldenGate hub | `tgthost`, Oracle Linux 9, OS user `oracle` |
| Software home | `/u01/ogg26ai_home` |
| Service Manager home | `/u01/ogg26ai_deploy` |
| Deployment home | `/u01/ogg26ai_deploy/dep1` |
| Deployment | `dep1` |
| Service ports | Manager `7809`; Admin `7810`; Distribution `7811`; Receiver `7812`; Metrics `7813` |
| Database aliases | `gg_source`, `gg_target`; domain `OracleGoldenGate` |
| Processes / trail | `EXT1` / `ea` / `REP1` |

```text
SRCPDB -> source log-mining server -> EXT1 -> local trail ea -> REP1 -> TGTPDB
                                     [ deployment dep1 on tgthost ]
```

All names are examples. Replace `<...>` placeholders before running commands. Do not paste placeholders literally into a shell. Passwords are supplied interactively and must not be stored in Git, logs, screenshots, or command history.

Prerequisites:

- Separate source and target databases, correct 26ai media/patch compatibility, supported OL9 configuration, adequate memory and disk space.
- Both PDBs open READ WRITE; working PDB services and name resolution from `tgthost`.
- Existing source `APP` schema, usable tablespaces on the target, and a clean target `APP` schema for this initial import. Stop if target objects/data already exist; do not silently merge or replace them.
- Source application writes and schema changes can be paused for the entire initial-load window. This first-build procedure deliberately uses that pause; it does not demonstrate a zero-downtime migration.
- No application writes directly to target `APP` while replication is in use.
- Source archived redo and flashback undo are retained long enough for capture and export; monitor FRA, undo and trail storage throughout.
- Database clocks and the hub clock are synchronized. `BEGIN NOW` depends on correct time settings.

**Verify** every installation-specific service name, directory, account privilege, release prerequisite, and command outcome during the first build. Stop on an unexpected error.

## Step 1: Prepare databases and privileges

### Source CDB root — SYSDBA

```sql
SHOW CON_NAME;
SELECT log_mode, force_logging, supplemental_log_data_min FROM v$database;
```

If NOARCHIVELOG, schedule a database outage and perform the following separately. This affects the whole CDB, not only SRCPDB:

```sql
SHUTDOWN IMMEDIATE;
STARTUP MOUNT;
ALTER DATABASE ARCHIVELOG;
ALTER DATABASE OPEN;
```

Then:

```sql
ALTER SYSTEM SET enable_goldengate_replication=TRUE SCOPE=BOTH;
ALTER DATABASE FORCE LOGGING;
ALTER DATABASE ADD SUPPLEMENTAL LOG DATA;
ALTER SYSTEM SWITCH LOGFILE;
SELECT log_mode, force_logging, supplemental_log_data_min FROM v$database;
SHOW PARAMETER streams_pool_size;
```

Expected logging state: ARCHIVELOG, YES, YES. **Verify** Streams pool capacity for the exact release and workload; `256M` is not a universal sizing requirement. Size memory explicitly and record the decision rather than blindly replacing an existing setting.

### Target CDB root — SYSDBA

```sql
SHOW CON_NAME;
ALTER SYSTEM SET enable_goldengate_replication=TRUE SCOPE=BOTH;
SHOW PARAMETER streams_pool_size;
```

**Verify** memory available for integrated apply. Open the target PDB READ WRITE and confirm its service before continuing.

### Source SRCPDB — SYSDBA

```sql
ALTER SESSION SET CONTAINER=SRCPDB;
SHOW CON_NAME;
CREATE USER ggadmin IDENTIFIED BY "<source_ggadmin_password>"
  DEFAULT TABLESPACE users QUOTA UNLIMITED ON users;
GRANT CREATE SESSION, CREATE TABLE, OGG_CAPTURE TO ggadmin;
```

`OGG_CAPTURE` is the 26ai capture role. This runbook uses a local PDB user and per-PDB capture; do not silently substitute CDB-root capture. **Verify** that DBLOGIN and registration use SRCPDB and that schema supplemental logging succeeds with these grants.

### Target TGTPDB — SYSDBA

```sql
ALTER SESSION SET CONTAINER=TGTPDB;
SHOW CON_NAME;
CREATE USER ggadmin IDENTIFIED BY "<target_ggadmin_password>"
  DEFAULT TABLESPACE users QUOTA UNLIMITED ON users;
GRANT CREATE SESSION, CREATE TABLE, OGG_APPLY TO ggadmin;
```

`OGG_APPLY` grants GoldenGate apply administration privileges; it does not replace application-object privileges. Because this lab includes newly created APP tables and cross-schema DDL, the following broad privileges are an explicit **lab-only** choice, granted locally in TGTPDB:

```sql
GRANT SELECT ANY TABLE, INSERT ANY TABLE, UPDATE ANY TABLE,
      DELETE ANY TABLE TO ggadmin;
GRANT CREATE ANY TABLE, ALTER ANY TABLE, DROP ANY TABLE,
      CREATE ANY INDEX, ALTER ANY INDEX, DROP ANY INDEX TO ggadmin;
```

These privileges reach other ordinary schemas within TGTPDB. They are not an APP-only least-privilege policy. A production design needs reviewed object/schema-scoped grants and a separate DDL authorization decision. This example covers ordinary table/index DDL only, not all possible APP object types. **Verify** privileges for additional replicated object types before adding them.

After import, verify APP exists, has sufficient target tablespace quota, and has no active application writers. Never grant DBA merely to hide a missing privilege.

### Source key checks — privileged session in SRCPDB

For this lab, require enabled, validated primary keys or usable unique keys. This diagnostic is only a first screen:

```sql
SELECT t.table_name
FROM dba_tables t
WHERE t.owner='APP'
  AND NOT EXISTS (
    SELECT 1 FROM dba_constraints c
    WHERE c.owner=t.owner AND c.table_name=t.table_name
      AND c.constraint_type IN ('P','U')
      AND c.status='ENABLED' AND c.validated='VALIDATED'
  )
ORDER BY t.table_name;
```

Investigate every result. Also inspect nullable unique-key columns, unsupported datatypes and the key GoldenGate actually selects. Passing this query alone does not prove that every table has a suitable replication key.

## Step 2: Install GoldenGate software

On `tgthost`, as `oracle`, use the Oracle GoldenGate 26ai **for Oracle** Linux x86-64 Microservices media. Verify its integrity against Oracle's download information.

```bash
mkdir -p /u01/ogg26ai_home /u01/ogg26ai_deploy /u01/stage
cd /u01/stage
unzip -q <ogg26ai_for_oracle_linux_x64>.zip
cd <unzipped_dir>/Disk1
./runInstaller
```

| Installer field | Value |
|---|---|
| Software location | `/u01/ogg26ai_home` |
| Inventory | Existing `/u01/app/oraInventory`, with correct group permissions |

Add to the oracle environment and reload it:

```bash
export OGG_HOME=/u01/ogg26ai_home
export PATH="$OGG_HOME/bin:$PATH"
```

Do not open the entire management port range to all sources. This single-host capture/apply flow does not need an external Distribution-to-Receiver connection.

## Step 3: Create Service Manager and deployment

```bash
$OGG_HOME/bin/oggca.sh
```

| Configuration | Value |
|---|---|
| Service Manager | New; home `/u01/ogg26ai_deploy`; host `tgthost`; port `7809` |
| System service | Register; run the generated privileged script when prompted |
| Deployment | `dep1`; home `/u01/ogg26ai_deploy/dep1` |
| Administrator | `oggadmin`; unique password supplied interactively |
| Services | Admin `7810`, Distribution `7811`, Receiver `7812`, Metrics `7813` |
| Replication schema | `ggadmin` |
| Transport security | TLS preferred. Non-TLS is acceptable here only for an isolated lab with SSH-tunnel management access |

Discover and record the generated service unit instead of assuming its name:

```bash
systemctl list-unit-files --type=service | grep -Ei 'goldengate|ogg'
systemctl status <actual_service_unit> --no-pager
ss -lnt | grep -E '78(09|10|11|12|13)'
```

**Verify** the unit against the OGGCA registration output, service bind addresses, and effective host/cloud firewall policy. Management endpoints must not be publicly accessible. Do not disable firewalld or SELinux as a routine workaround.

For a non-TLS isolated lab, run this on the administration workstation and keep the session open:

```bash
ssh -N \
  -L 127.0.0.1:7809:tgthost:7809 \
  -L 127.0.0.1:7810:tgthost:7810 \
  oracle@tgthost
```

Open `http://127.0.0.1:7809` for Service Manager and `http://127.0.0.1:7810` for Administration. If the workstation ports are busy, select other local ports and record the mapping. For TLS deployments, use HTTPS with valid certificate verification instead of these HTTP examples.

## Step 4: Credentials, supplemental logging and checkpoint table

Run Admin Client locally on `tgthost`. The following HTTP connection assumes the isolated non-TLS lab configuration above:

```bash
$OGG_HOME/bin/adminclient
```

```text
CONNECT http://tgthost:7809 DEPLOYMENT dep1 AS oggadmin
ALTER CREDENTIALSTORE ADD USER ggadmin@//srchost:1521/srcpdb ALIAS gg_source DOMAIN OracleGoldenGate
ALTER CREDENTIALSTORE ADD USER ggadmin@//tgthost:1521/tgtpdb ALIAS gg_target DOMAIN OracleGoldenGate
INFO CREDENTIALSTORE
DBLOGIN USERIDALIAS gg_source DOMAIN OracleGoldenGate
ADD SCHEMATRANDATA APP
INFO SCHEMATRANDATA APP
DBLOGIN USERIDALIAS gg_target DOMAIN OracleGoldenGate
ADD CHECKPOINTTABLE ggadmin.ggs_checkpoint
```

Supply passwords at the interactive prompts. **Verify** credential-store initialization and prompting on the installed build; do not add literal passwords to this file if initialization is needed. Both DBLOGIN operations and the logging/checkpoint commands must succeed. Record PDB service identities and the deployment's actual `OGG_DATA_HOME`.

## Step 5: Freeze source writes and start capture with DDL disabled

Pause **all APP DML and DDL writers**, including jobs and manual sessions, and drain outstanding APP transactions before registration. Keep this pause through Step 7. An empty transaction query does not prevent a new transaction: enforce the pause at the application/job/session level.

Privileged session in SRCPDB:

```sql
SELECT s.sid, s.serial#, s.username, t.start_time, t.start_scn
FROM v$transaction t
JOIN v$session s ON s.saddr=t.ses_addr
ORDER BY t.start_scn;
```

Investigate outstanding transactions and cross-schema writers to APP. On RAC, inspect all instances with the corresponding GV$ views and INST_ID join. Do not assume a local V$ query proves a cluster-wide drain.

Admin Client:

```text
DBLOGIN USERIDALIAS gg_source DOMAIN OracleGoldenGate
REGISTER EXTRACT EXT1 DATABASE
ADD EXTRACT EXT1, INTEGRATED TRANLOG, BEGIN NOW
ADD EXTTRAIL ea, EXTRACT EXT1, MEGABYTES 200
EDIT PARAMS EXT1
```

Initial Extract parameters:

```text
EXTRACT EXT1
USERIDALIAS gg_source DOMAIN OracleGoldenGate
EXTTRAIL ea
DDL EXCLUDE ALL
TABLE APP.*;
```

```text
START EXTRACT EXT1
INFO EXTRACT EXT1, DETAIL
VIEW REPORT EXT1
```

**Verify** per-PDB capture registration against SRCPDB and successful process initialization. `ea` is a logical trail name in the deployment data area. Record the actual path and sequence from INFO/report output; do not assume a `dirdat` directory or a particular first sequence number. Confirm trail creation once captured activity is available.

## Step 6: Data Pump initial load at a recorded SCN

APP writers remain paused. Extract remains running. DDL capture remains disabled.

In a privileged source SRCPDB session:

```sql
SHOW CON_NAME;
SELECT current_scn FROM v$database;
```

Record the returned numeric value as `LOAD_SCN`. The export represents committed data as of that SCN; it does not include uncommitted work.

On `srchost`, substitute that exact number:

```bash
expdp system@//srchost:1521/srcpdb \
  schemas=APP flashback_scn=<LOAD_SCN> directory=DATA_PUMP_DIR \
  dumpfile=app_%U.dmp logfile=app_exp.log
```

Resolve the directory object's OS path separately in each PDB:

```sql
SELECT directory_name, directory_path
FROM dba_directories WHERE directory_name='DATA_PUMP_DIR';
```

Transfer **every** generated dump piece from source to the resolved target path using approved SSH/SCP access. Verify file sizes and checksums at both ends. These paths are server-side, not the workstation's current directory. Do not overwrite an unrelated dump set.

On `tgthost`, after confirming the target schema is clean:

```bash
impdp system@//tgthost:1521/tgtpdb \
  schemas=APP directory=DATA_PUMP_DIR \
  dumpfile=app_%U.dmp logfile=app_imp.log
```

Supply SYSTEM passwords interactively. Resolve target tablespace differences explicitly before import. Check complete export/import logs and all errors; do not accept a completion line as proof that all objects loaded correctly.

With APP writes still paused at both ends, compare object inventories, per-table row counts, and key/value content for every in-scope table. For small lab tables, compare complete ordered rows. Row counts alone cannot detect changed values. Record exceptions and stop if baseline reconciliation fails.

## Step 7: Start apply, verify the boundary, then enable DDL

Admin Client:

```text
DBLOGIN USERIDALIAS gg_target DOMAIN OracleGoldenGate
ADD REPLICAT REP1, INTEGRATED, EXTTRAIL ea, CHECKPOINTTABLE ggadmin.ggs_checkpoint
EDIT PARAMS REP1
```

Initial Replicat parameters:

```text
REPLICAT REP1
USERIDALIAS gg_target DOMAIN OracleGoldenGate
DDL EXCLUDE ALL
MAP APP.*, TARGET APP.*;
```

For the **first start only**, use the source export SCN, not a target SCN:

```text
START REPLICAT REP1, AFTERCSN <LOAD_SCN>
INFO REPLICAT REP1, DETAIL
VIEW REPORT REP1
```

**Verify** the report records the requested source CSN. AFTERCSN skips transactions committed at or below LOAD_SCN. With source writes paused, the process may wait for a later transaction; RUNNING or zero reported lag alone does not prove end-to-end apply.

After baseline reconciliation, keep writers paused and stop both processes cleanly:

```text
STOP EXTRACT EXT1
STOP REPLICAT REP1
INFO ALL
```

Edit EXT1, replacing only `DDL EXCLUDE ALL` with:

```text
DDL INCLUDE MAPPED
```

Edit REP1, replacing only `DDL EXCLUDE ALL` with:

```text
DDL INCLUDE MAPPED
```

Start from existing checkpoints:

```text
START EXTRACT EXT1
START REPLICAT REP1
INFO ALL
```

Run Step 8's controlled APP test before restoring normal application writes. Never use HANDLECOLLISIONS or skip errors to conceal a bad initial-load boundary. If initialization fails, preserve diagnostics and correct/rebuild the baseline deliberately.

## Step 8: Validate each operation separately

Confirm `APP.GG_TEST` does not already exist at either end. Use it only as a disposable lab object. Keep other APP writers paused during this test. Execute **one source operation**, wait for apply, and verify its target outcome before proceeding.

### 8.1 CREATE — source SRCPDB as APP

```sql
CREATE TABLE gg_test (id NUMBER PRIMARY KEY, note VARCHAR2(30));
```

Target TGTPDB, privileged read session:

```sql
SELECT owner, table_name FROM dba_tables
WHERE owner='APP' AND table_name='GG_TEST';
```

Expected: one row. **Verify** the target APP tablespace quota and replicated key/index definition.

### 8.2 INSERT — source APP

```sql
INSERT INTO gg_test VALUES (1, 'INSERT_OK');
COMMIT;
```

Target:

```sql
SELECT id, note FROM app.gg_test ORDER BY id;
```

Expected: exactly `(1, INSERT_OK)`.

### 8.3 UPDATE — source APP

```sql
UPDATE gg_test SET note='UPDATE_OK' WHERE id=1;
COMMIT;
```

Repeat the target SELECT. Expected: exactly `(1, UPDATE_OK)`.

### 8.4 DELETE — source APP

```sql
DELETE FROM gg_test WHERE id=1;
COMMIT;
```

Repeat the target SELECT. Expected: no rows.

### 8.5 DROP — source APP

```sql
DROP TABLE gg_test PURGE;
```

Repeat the target DBA_TABLES lookup from 8.1. Expected: no rows. Do not run SELECT against the dropped table as the only validation.

### 8.6 Processes and evidence

```text
INFO ALL
INFO EXTRACT EXT1, DETAIL
INFO REPLICAT REP1, DETAIL
LAG EXTRACT EXT1
LAG REPLICAT REP1
STATS EXTRACT EXT1, TOTAL
STATS REPLICAT REP1, TOTAL
VIEW REPORT EXT1
VIEW REPORT REP1
```

Process statistics support diagnosis; they are not a substitute for target-side content checks. Counters may cover different intervals or operation types. Use bounded waits and inspect reports when an expected result does not arrive.

Save sanitized target results, report excerpts, checkpoint observations, process/release identities and timing. Then resume source application writes, keeping target APP read-only to application users operationally. Perform a controlled process restart and subsequent DML test before claiming restart recovery is validated.

Keep status Draft until the full procedure, required Verify checks and evidence have been completed. A successful controlled lab test does not establish production acceptance or application cutover readiness.

## Operate

| Task | Admin Client command or host action |
|---|---|
| Status | `INFO ALL` |
| Checkpoints | `INFO EXTRACT EXT1, SHOWCH` / `INFO REPLICAT REP1, SHOWCH` |
| Reports | `VIEW REPORT EXT1` / `VIEW REPORT REP1` |
| Pause apply/capture | `STOP REPLICAT REP1`, then `STOP EXTRACT EXT1`; account for retained trails and source redo |
| Restart normally | `START EXTRACT EXT1`, then `START REPLICAT REP1`; use existing checkpoints |
| Service | `systemctl status <actual_service_unit> --no-pager`; use the verified unit for authorized start/stop |

Do not repeat AFTERCSN on routine restarts. Monitor source FRA/archive retention, Extract lag, trail disk usage and Replicat errors. Define a checkpoint-aware trail purge policy only after successful recovery testing; do not delete trails merely because they look old.

## Optional teardown — this disposable lab only

This removes replication configuration. It is not a normal shutdown. Confirm no other process depends on APP supplemental logging or the checkpoint table. Stop application writers and preserve required reports/evidence first.

```text
STOP REPLICAT REP1
STOP EXTRACT EXT1
DBLOGIN USERIDALIAS gg_target DOMAIN OracleGoldenGate
DELETE REPLICAT REP1
DELETE CHECKPOINTTABLE ggadmin.ggs_checkpoint
DBLOGIN USERIDALIAS gg_source DOMAIN OracleGoldenGate
DELETE EXTRACT EXT1
```

**Verify** whether DELETE EXTRACT successfully removed its database registration on this build. If registration remains, with the source login active:

```text
UNREGISTER EXTRACT EXT1 DATABASE
```

In SRCPDB, compare with the capture identity recorded for EXT1; other captures may legitimately remain:

```sql
SELECT capture_name, status FROM dba_capture;
```

Only if no other consumer requires APP schema supplemental logging:

```text
DELETE SCHEMATRANDATA APP
```

Deleting process groups is not a full uninstall: parameter files, trails, reports, aliases, users and deployment services can remain. Do not delete them or revoke shared grants without a separate dependency review. Do not disable database-wide ARCHIVELOG, FORCE LOGGING or supplemental logging as routine teardown.

## References

- [Oracle 26ai database users and privileges](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/prepare-database-user-and-privileges-oracle.html)
- [Before adding Extract and Replicat](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/configure-ogg-adding-extract-and-replicat.html)
- [Initial synchronization and DDL](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/extract-oracle-initial-synchronization.html)
- [DDL defaults](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/extract-oracle-enabling-ddl-support.html)
- [REGISTER EXTRACT](https://docs.oracle.com/en/database/goldengate/core/26/gclir/register-extract.html)
- [ADD EXTTRAIL](https://docs.oracle.com/en/database/goldengate/core/26/gclir/add-exttrail.html)
- [START REPLICAT and AFTERCSN](https://docs.oracle.com/en/database/goldengate/core/26/gclir/start-replicat.html)
- [Deleting Extract and Replicat](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/deleting-extract-and-replicat-1.html)

Documentation review does not replace testing against the exact installed software and database release updates.
