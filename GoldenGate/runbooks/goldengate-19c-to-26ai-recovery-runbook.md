# GoldenGate 19c to 26ai recovery runbook

Evidence updated: November 8, 2026, through 19:59 CST. Live INSERT/UPDATE/DELETE verified on HOLA.TEST1 and HOLA.FOX; four mapped DDL operations applied with zero DDL errors. HOLA schema key logging and FOX target key selection confirmed. Both listener settings persisted. Section 14 is the current validation record; sections 1–13 preserve the recovery chronology.

This record preserves correct commands and explanations from the supplied terminal output and logs. Mistyped commands, pasted prompts, repeated failures, and passwords are excluded. Historical errors are summarized where they explain a corrective action. Commands are grouped by execution context, not intended as one script to rerun blindly.

## 1. Scope and environment

Active route: PRODB/PRODBHR (Oracle 19c source) → integrated Extract EXT19C on target-host → local lt trail → integrated Replicat REP26AI → CDB23AI/PDB23AI (26ai target).

| Component | Confirmed configuration |
|---|---|
| Source host | source-host; shell hostname source-host; <SOURCE_IP> |
| Source database | PRODB, DBID 2635453154; PRIMARY, READ WRITE |
| Source PDB | PRODBHR, READ WRITE |
| Source Oracle home | /u01/app/oracle/product/19.3/db_home |
| Target / GoldenGate host | target-host; <TARGET_IP> |
| Target database / PDB | CDB23AI / PDB23AI |
| Target Oracle home | /u01/app/oracle/product/26ai/dbhome_1 |
| GoldenGate version | 23.26.1.0.0; 26ai product naming |
| GoldenGate home | /u02/ogg26ai_home |
| Deployment | DEP1; /u02/ogg26ai_deploy |
| Service Manager / Admin | HTTP management ports (lab only) |
| Credential domain | OracleGoldenGate |

> Public edition: network endpoints and hostnames are placeholders. Evidence transcripts/screenshots are retained outside this repository; the summaries below do not claim a published raw transcript. This is a lab recovery record; review commands individually in the stated host/container.

User reports RAC and Data Guard working. OCI and Azure environments were retired following trial expiration. Their historical routes must not be assumed active or blamed for local lag without configuration evidence.

Network change: user reports moving from Xfinity to Eazy Fiber and manually updating IP addresses. Stale addresses were confirmed during this recovery; this supports a contributing connectivity issue, not a complete proof of incident causation.

## 2. Know the execution context

- Linux shell: launch SSH, SQL*Plus, RMAN, listener tools, or Admin Client here.
- SQL> prompt: database SQL and SQL*Plus commands; confirm database and container first.
- RMAN> prompt: RMAN validation commands.
- OGG> prompt: Admin Client commands. Connect to DEP1 before database login or credential changes. Enter one command at a time, without copied prompt text or SQL semicolons.
- A terminal title may still show the target IP after nested SSH to the source. Verify hostname and database identity.
- Management user <OGG_ADMIN_USER> differs from database users GGADMIN and C##GGADMIN.

Observed tabs: 11 Admin Client; 12 target SQL*Plus/PDB23AI; 14 nested source SSH/SQL*Plus. Tabs can change; identity checks take precedence.

## 3. Host, listener, and database checks

Run in Linux shell on the host being inspected:

```bash
hostname
echo "$ORACLE_SID"
echo "$ORACLE_HOME"
ps -ef | grep '[o]ra_pmon_'
lsnrctl status
```

These establish host, local Oracle environment, instance process, listener endpoints, and registered services. A running PMON alone does not prove database OPEN status. A static listener UNKNOWN entry alone does not establish a database fault.

Access source from target when needed:

```bash
ssh oracle@<SOURCE_IP>
```

SSH supplies an operating system session; it does not authenticate a database session. Connection success depends on network access, SSH service, and account authentication. In this session password authentication succeeded. Exit the nested SSH session to return to target-host before launching its GoldenGate binaries.

Start SQL*Plus in the correct host environment:

```bash
sqlplus / as sysdba
```

At SQL>:

```sql
SHOW USER
SHOW CON_NAME
SELECT instance_name, status, startup_time FROM v$instance;
SELECT name, dbid, open_mode, database_role FROM v$database;
SHOW PDBS
```

Source verified OPEN/PRIMARY; PRODBHR READ WRITE. Target PDB23AI READ WRITE. Leave unrelated mounted PDBs unchanged.

### Target listener correction performed

Target listener was unavailable earlier; it was started from the target Linux shell:

```bash
lsnrctl start
```

Target LOCAL_LISTENER referenced <OLD_TARGET_IP> while the active listener used <TARGET_IP>. In target CDB$ROOT as SYS, the observed correction was:

```sql
ALTER SYSTEM SET LOCAL_LISTENER='(ADDRESS=(PROTOCOL=TCP)(HOST=<TARGET_IP>)(PORT=1521))' SCOPE=MEMORY;
ALTER SYSTEM REGISTER;
```

Result: CDB23AI and pdb23ai services registered READY. SCOPE=MEMORY was temporary; persistence was subsequently demonstrated with SCOPE=BOTH (section 13).

## 4. Admin Client connection and credential recovery

On target target-host, Linux shell:

```bash
/u02/ogg26ai_home/bin/adminclient
```

At OGG>:

```text
CONNECT http://localhost:<SM_PORT> DEPLOYMENT DEP1 USER <OGG_ADMIN_USER>
```

Enter the deployment management password privately when prompted.

Target credential update, performed after correcting the database password and stored address:

```text
ALTER CREDENTIALSTORE REPLACE USER <APPLY_USER>@<TARGET_IP>:1521/pdb23ai ALIAS TGT26AI DOMAIN OracleGoldenGate
DBLOGIN USERIDALIAS TGT26AI
```

Run separately. Omitted PASSWORD requests hidden input. Confirmed successful login to PDB23AI. A malformed target address containing an extra address component was corrected.

Source credential update:

```text
ALTER CREDENTIALSTORE REPLACE USER <CAPTURE_USER>@<SOURCE_IP>:1521/PRODB ALIAS SRC19CROOT DOMAIN OracleGoldenGate
DBLOGIN USERIDALIAS SRC19CROOT
```

Confirmed successful login to source CDB$ROOT. EXT19C uses this root alias. Existing SRC19C alias points to <APPLY_USER>@<SOURCE_IP>:1521/prodbhr; it was not tested in this recovery and is not the configured EXT19C alias.

Database account diagnostic, source root SQL>:

```sql
SELECT username, account_status, authentication_type
FROM dba_users
WHERE username = 'C##GGADMIN';
```

Observed OPEN/PASSWORD. Source account password was changed successfully, and the alias synchronized. Do not preserve inline password values. Private source password rotation after exposure was recommended but not confirmed.

Target SQL*Plus password change was confirmed using:

```text
PASSWORD GGADMIN
```

This prompts privately. The analogous source SQL*Plus command is PASSWORD C##GGADMIN; its later execution is pending confirmation. Password changes require updating each actual credential consumer.

## 5. Preserved parameters

At OGG>, inspect one command at a time:

```text
VIEW PARAMS EXT19C
VIEW PARAMS REP26AI
```

EXT19C:

```text
EXTRACT EXT19C
USERIDALIAS SRC19CROOT
EXTTRAIL ./dirdat/lt
TRANLOGOPTIONS SOURCE_OS_TIMEZONE America/New_York
LOGALLSUPCOLS
UPDATERECORDFORMAT COMPACT
DDL INCLUDE MAPPED
SOURCECATALOG PRODBHR
TABLE FOX.*;
TABLE HOLA.*;
```

SOURCECATALOG supplies PRODBHR for the two source schema patterns. LOGALLSUPCOLS causes the reported NOCOMPRESSDELETES/GETUPDATEBEFORES behavior. The current region-based timezone parameter replaces the original fixed -04:00 setting; see section 12 for evidence and restart verification.

REP26AI:

```text
REPLICAT REP26AI
USERIDALIAS TGT26AI
DBOPTIONS ENABLE_INSTANTIATION_FILTERING
MAP PRODBHR.FOX.*, TARGET FOX.*;
MAP PRODBHR.HOLA.*, TARGET HOLA.*;
```

Target login restricts apply to PDB23AI. Instantiation filtering remains enabled. No HANDLECOLLISIONS, transaction skipping, repositioning, or recreation was performed.

GLOBALS report identifies GGSCHEMA c##sourcegg1; preserved unchanged. Replicat checkpoint table is GGADMIN.GGCHKPT.

## 6. Target apply diagnostics and privilege evidence

Run in target PDB23AI SQL>:

```sql
SET LINESIZE 220
COLUMN apply_name FORMAT A20
COLUMN error_message FORMAT A110 WORD_WRAPPED
SELECT apply_name, status, error_number, error_message
FROM dba_apply
WHERE apply_name = 'OGG$REP26AI';

SELECT apply_name, error_number, error_message
FROM dba_apply_error
WHERE apply_name = 'OGG$REP26AI';

SELECT owner, table_name
FROM dba_tables
WHERE owner = 'HOLA' AND table_name = 'TEST1';

SELECT grantee, privilege, grantor
FROM dba_tab_privs
WHERE owner = 'HOLA' AND table_name = 'TEST1'
ORDER BY grantee, privilege;

SELECT privilege
FROM dba_sys_privs
WHERE grantee = 'GGADMIN'
ORDER BY privilege;
```

Before restart: apply DISABLED, no reported error fields; DBA_APPLY_ERROR no rows. This does not erase historical errors from the Replicat report.

Historical August report: ORA-41900 missing INSERT privilege on HOLA.TEST1, ORA-26804 apply disabled, followed by abend. Current check confirmed HOLA.TEST1 exists and direct GGADMIN INSERT granted by HOLA. System privileges observed: CREATE ANY INDEX, CREATE ANY TABLE, CREATE SESSION, CREATE TABLE, DELETE ANY TABLE, INSERT ANY TABLE, UNLIMITED TABLESPACE, UPDATE ANY TABLE. No additional broad grants were made based on the historical report.

## 7. Source capture and retained redo validation

Run in source PRODB CDB$ROOT SQL>:

```sql
SET LINESIZE 220
COLUMN capture_name FORMAT A25
COLUMN error_message FORMAT A80 WORD_WRAPPED
COLUMN required_checkpoint_scn FORMAT 99999999999999999999
SELECT capture_name, status, required_checkpoint_scn,
       error_number, error_message
FROM dba_capture
WHERE purpose = 'GoldenGate Capture';
```

Before restart: OGG$CAP_EXT19C DISABLED, required checkpoint SCN 10782180, no displayed error.

Locate redo covering that SCN:

```sql
COLUMN name FORMAT A100
COLUMN first_change# FORMAT 9999999999999999
COLUMN next_change# FORMAT 9999999999999999
SELECT thread#, sequence#, first_change#, next_change#,
       deleted, status, name
FROM v$archived_log
WHERE first_change# <= 10782180
  AND next_change# > 10782180
  AND resetlogs_change# = (
      SELECT resetlogs_change# FROM v$database
  )
ORDER BY thread#, sequence#, dest_id;
```

Thread 1 sequence 105 covers SCNs 10761764–10875205. Local FRA copy status A, deleted NO. The prdst destination entry is not a local archive filename.

In source Linux shell, start RMAN using the correct Oracle environment:

```bash
rman target /
```

At RMAN> (observed successful validation):

```text
BACKUP VALIDATE ARCHIVELOG FROM SEQUENCE 105 THREAD 1;
```

Evidence: sequences 105–177, 73 sequences, OK with zero failing blocks and no RMAN error. This validates the selected archived logs; it is not a new backup or proof that every future archive remains available.

Source root SQL> continuity check:

```sql
SELECT MIN(sequence#) AS first_seq,
       MAX(sequence#) AS last_seq,
       COUNT(DISTINCT sequence#) AS sequence_count
FROM v$archived_log
WHERE thread# = 1
  AND sequence# BETWEEN 105 AND 177
  AND deleted = 'NO'
  AND status = 'A'
  AND name LIKE '/%'
  AND resetlogs_change# = (
      SELECT resetlogs_change# FROM v$database
  );
```

Result: first 105, last 177, count 73. Combined with physical validation this supported resuming existing capture. Retain required archives during catch-up.

After restart, source root SQL>:

```sql
SELECT capture_name, state FROM v$goldengate_capture;
```

Confirmed OGG$CAP_EXT19C CAPTURING CHANGES.

## 8. Resume existing processes and monitor

At OGG>, source login verified before Extract start:

```text
DBLOGIN USERIDALIAS SRC19CROOT
START EXTRACT EXT19C
INFO EXTRACT EXT19C DETAIL
```

Extract started November 7 at 19:37:21 UTC / 13:37:21 CST, PID 65553. Recovery validated existing bounded recovery state and attached to OGG$CAP_EXT19C. Initial redo sequence 105; last completed historical trail transaction CSN 10664917, sequence 2 begin RBA 5097/end 5343. Initial read checkpoint SCN 10782542. No checkpoint reset was needed.

Then target login and Replicat start:

```text
DBLOGIN USERIDALIAS TGT26AI
START REPLICAT REP26AI
INFO REPLICAT REP26AI DETAIL
```

Replicat started 19:42:16 UTC / 13:42:16 CST, PID 67362. Initially DETACHED; later ATTACHED/RUNNING. Report confirmed successful attach and rollover from trail 2 RBA 5447 to trail 3, including a graceful restart record at RBA 1669. Observed read position trail 3 RBA 1730.

Monitoring commands, one at a time:

```text
INFO EXTRACT EXT19C DETAIL
INFO REPLICAT REP26AI DETAIL
STATS EXTRACT EXT19C TOTAL
STATS REPLICAT REP26AI TOTAL
VIEW REPORT EXT19C
VIEW REPORT REP26AI
```

Compare read SCN/timestamp across samples spaced about 20–30 minutes. RUNNING and recent checkpoint-update age prove responsiveness, not advancement by themselves. A 30-second unchanged read SCN did not establish a stall; later advancement disproved a persistent stall.

### Recorded progress

| Read checkpoint | SCN | Observed significance |
|---|---:|---|
| August 14 | 10782542 | Pre-restart position |
| August 20 | 12214320 | Backlog processing; UI redo sequence 125 |
| September 11 00:00:37 | 13628750 | Lag about 57d 15h |
| September 11 03:33:16 | 13664806 | Further advancement |
| October 18 09:45:18 | 13820373 | Lag about 20d 6h |
| October 18 10:14:47 | 13831060 | Further advancement |
| October 18 14:00:54 | 13864176 | Intermediate checkpoint; lag 20d 01:53:38 |

Intermediate status before time zone correction and live DML testing (superseded by section 12): Extract RUNNING, PID unchanged. Displayed Extract output trail remains sequence 2 RBA 5447. No newly captured mapped table transaction has been demonstrated. Replicat zero lag and fresh checkpoint do not establish source-to-target currency. Watermarks observed remained low 9375138/high 10664917. Statistics reported no active maps and zero transactions after restart.

No reliable completion ETA: calendar time covered by redo varies significantly in this lab.

## 9. Interpret warnings and management messages correctly

- Error log path in INFO DETAIL merely identifies a file; it is not a new error.
- Extract Source Not Available is absent source metadata in that view, not proof of missing required redo.
- Outbound server SCNs Unavailable were observed while Admin Client database login was to the target; this output alone does not establish a source capture failure.
- OGG-02045: streams_pool_size not explicitly configured. Capture successfully attached. Inspect source memory allocation and waits before deciding whether tuning is needed; memory starvation has not been proven.
- OGG-04033: LOGALLSUPCOLS sets related before-image/delete handling; no action taken.
- OGG-12062 at 14:49:13 CST: authenticated management request for the Extract report was not authorized. Separate from database login and capture; inspect management session/role if repeated. Do not change the capture database account to fix a management authorization error.
- Poorly formed browser cookies/user session retrieval failures are management-session evidence, not demonstrated capture failures.
- FQDN lookup warning warrants hostname-resolution review; not established as current capture lag cause.
- Service Manager security disabled is consistent with observed HTTP endpoints; record for subsequent hardening, not an asserted cause of redo backlog.
- OCI call [ORA] means Oracle Call Interface. It does not identify Oracle Cloud Infrastructure traffic.

September 10 logs show source credential failures, target hostname resolution failures, and Extract restart attempts. Therefore describe an old August checkpoint with later restart attempts, not uninterrupted process inactivity since August.

## 10. Table baseline and closure checks

Source SQL> in PRODBHR:

```sql
ALTER SESSION SET CONTAINER = PRODBHR;
SHOW CON_NAME
DESC HOLA.TEST1
SELECT COUNT(*) FROM HOLA.TEST1;
SELECT id, name FROM HOLA.TEST1 ORDER BY id;
SELECT name FROM v$database;
```

Target SQL> verify CDB23AI/PDB23AI before reading the corresponding table:

```sql
SELECT name FROM v$database;
SHOW CON_NAME
SELECT id, name FROM HOLA.TEST1 ORDER BY id;
```

Both observed baselines: ID 1 NAME ROTE; ID 2 NAME GG TEST. Source columns ID NUMBER NOT NULL and NAME VARCHAR2(50). Matching old rows alone do not prove current CDC.

### Earlier closure checklist — superseded by sections 13–14

1. Catch-up reached four-second reported lag after the time zone correction; obtain final process snapshots to confirm sustained low lag.
2. Inspect current source supplemental logging for FOX/HOLA. Historical setup failures exist; no current deficiency is established. Confirm version-supported INFO commands before use; do not blindly re-register capture or add logging based on an old error.
3. Verify current Replicat ATTACHED/RUNNING and absence of current apply errors.
4. Completed: test ID 20261107 was absent on both databases, then appeared, changed, and disappeared on the target following the source test sequence. INSERT statistics independently confirmed capture and apply. See section 12. Final UPDATE/DELETE counters are still to be collected.
5. Investigate instantiation filtering only if evidence shows test transactions filtered; do not disable it preemptively.
6. Persist corrected target LOCAL_LISTENER after checking SPFILE/PFILE usage.
7. Confirm private rotation of exposed source credentials and synchronization of actual consumers.
8. If progress stops across a meaningful interval, inspect source capture state, waits, required redo availability, and current reports before restarting or tuning.
9. Preserve retired OCI/Azure route configurations separately if available. No cloud endpoint or route dependency has been established in supplied management logs.

## 11. File locations and evidence register

| Item | Location |
|---|---|
| Extract parameters | /u02/ogg26ai_deploy/etc/conf/ogg/EXT19C.prm |
| Replicat parameters | /u02/ogg26ai_deploy/etc/conf/ogg/REP26AI.prm |
| Extract report | /u02/ogg26ai_deploy/var/lib/report/EXT19C.rpt |
| Replicat report | /u02/ogg26ai_deploy/var/lib/report/REP26AI.rpt |
| GoldenGate error log | /u02/ogg26ai_deploy/var/log/ggserr.log |
| Extract checkpoint | /u02/ogg26ai_deploy/var/lib/checkpt/EXT19C.cpe |
| Replicat checkpoint | /u02/ogg26ai_deploy/var/lib/checkpt/REP26AI.cpr |
| Actual trail directory | /u02/ogg26ai_deploy/var/lib/data/dirdat |
| Bounded recovery temporary area | /u02/ogg26ai_deploy/var/temp/BR/EXT19C |

Supplied evidence includes RMAN validation Pasted text(20261107-193620).txt; Admin Server history Pasted text(20261107-202529).txt; Service Manager history Pasted text(20261107-204747).txt; Extract report with management authorization response Pasted text(20261107-205010).txt; pasted commands and screenshots in this conversation.

This runbook records confirmed actions separately from pending work. Section 12 records subsequent catch-up and live DML verification; listener persistence and unresolved credential/security checks remain open.


## 12. Time zone correction and live DML validation — November 7 update

### Clock evidence and one-hour lag

Source source-host returned EST -0500 and UTC 21:54:46. Target target-host returned CST -0600 and UTC 21:54:25 in separately executed commands; these samples do not prove a 21-second clock drift. Source timedatectl confirmed America/New_York, NTP enabled/synchronized, DST inactive, with DST ending November 1, 2026. No OS time zone or clock change was performed.

Linux diagnostics on each host:

```bash
hostname
date '+%Y-%m-%d %H:%M:%S %Z %z'
date -u '+%Y-%m-%d %H:%M:%S UTC'
hostnamectl
timedatectl status
```

Extract had processed into current-day redo but retained approximately 01:00:04 lag with the fixed -04:00 source offset. Corrective sequence:

1. At OGG>, STOP EXTRACT EXT19C. Confirmed graceful shutdown at 22:10:30 UTC / 16:10:30 CST.
2. In web console Extracts → EXT19C → Parameters, replace the fixed offset line with TRANLOGOPTIONS SOURCE_OS_TIMEZONE America/New_York and save.
3. At OGG>, VIEW PARAMS EXT19C confirmed the saved region setting and other parameters unchanged.
4. START EXTRACT EXT19C, then inspect its report and INFO detail. Replicat was left running.

```text
STOP EXTRACT EXT19C
VIEW PARAMS EXT19C
START EXTRACT EXT19C
VIEW REPORT EXT19C
INFO EXTRACT EXT19C DETAIL
```

These are separate commands with the parameter edit between STOP and VIEW. Do not run as an unconditional stop/start script.

New report: start 16:17:34 CST, PID 122855, attach to OGG$CAP_EXT19C at 16:18:03, position SCN 15755670, first record sequence 178 SCN 15755681. No ERROR/ABEND in supplied startup report.

OGG-01438 warned that the saved graceful-shutdown output checkpoint expected sequence 2/RBA 5447, while trail sequence 3/RBA 1730 existed. Output recovery scan completed and Extract continued rollover. No trail deletion or checkpoint reset was performed. This warning alone is not proof of target consistency.

Subsequent INFO detail: RUNNING, last started 16:18, PID 122855, read checkpoint November 7 16:22:52, SCN 15757660, lag 00:00:04 updated two seconds ago. Thus the historical backlog cleared and the one-hour reported discrepancy disappeared after the parameter correction.

Management authorization failure for <OGG_ADMIN_USER> occurred once immediately before a successful retry. Treat separately from capture database login. Its root cause remains unconfirmed; do not label it resolved permanently.

### Committed transaction test and target evidence

First execute in both source PRODBHR and target PDB23AI SQL*Plus sessions:

```sql
SHOW CON_NAME
SELECT id, name FROM HOLA.TEST1 WHERE id = 20261107;
```

Both returned no rows. The following writes were instructed on SOURCE PRODBHR only; target evidence consists of SELECT results, not direct target writes. Source DML/COMMIT terminal acknowledgements were not separately pasted, so retain that evidence limit. Extract/Replicat INSERT counters independently corroborate the insert path.

SOURCE INSERT:

```sql
INSERT INTO HOLA.TEST1 (id, name)
VALUES (20261107, 'GG_RECOVERY_20261107');
COMMIT;
```

TARGET SELECT after a short wait:

```sql
SELECT id, name FROM HOLA.TEST1 WHERE id = 20261107;
```

Observed target row: 20261107 / GG_RECOVERY_20261107. At 16:31:56 Extract statistics showed one INSERT from PRODBHR.HOLA.TEST1, one operation, one metadata record, zero discards. At 16:32:10 Replicat statistics showed one transaction, one INSERT to PDB23AI.HOLA.TEST1, zero discards. This establishes live INSERT capture and apply.

SOURCE UPDATE:

```sql
UPDATE HOLA.TEST1
SET name = 'GG_RECOVERY_UPDATE_20261107'
WHERE id = 20261107;
COMMIT;
```

Same TARGET SELECT then showed 20261107 / GG_RECOVERY_UPDATE_20261107 (screenshot around 16:36 CST). This demonstrates the expected update reaching the target following the source test instruction.

SOURCE DELETE / test cleanup:

```sql
DELETE FROM HOLA.TEST1
WHERE id = 20261107
  AND name = 'GG_RECOVERY_UPDATE_20261107';
COMMIT;
```

TARGET session explicitly confirmed PDB23AI, then the same SELECT returned no rows (screenshot around 16:38 CST). The test row was removed on the target following source cleanup instruction. Original IDs 1 and 2 were not targeted by these DML predicates.

### Status and remaining work

Live INSERT, UPDATE, and DELETE behavior on HOLA.TEST1 is verified by the observed target transitions; INSERT has independent Extract/Replicat statistics. This validates this table's tested DML path, not every FOX/HOLA table, DDL replication, or full historical consistency.

Collect final process INFO and STATS to record current lag, ATTACHED state, and UPDATE/DELETE counters. Persist target LOCAL_LISTENER after checking startup parameter file usage. Confirm source private credential rotation if still pending. Retain the intermittent management authorization issue and streams pool warning as follow-up items, not established ongoing capture failures. No broad schema grants, process recreation, skip operations, or instantiation-filter removal was needed.


## 13. Final operational verification — November 7, 2026, 17:08 CST

### Persisted listener settings

After database identity verification, the correct source and target listener endpoints were saved with SCOPE=BOTH and registration requested. During this step the target address was briefly entered on the source by mistake; it was corrected immediately to the source endpoint. Do not reproduce that mistaken command. This record retains the correction and the need for identity checks rather than the erroneous syntax.

SOURCE PRODB CDB$ROOT:

```sql
SELECT name FROM v$database;
SELECT host_name FROM v$instance;
ALTER SYSTEM SET LOCAL_LISTENER='(ADDRESS=(PROTOCOL=TCP)(HOST=<SOURCE_IP>)(PORT=1521))' SCOPE=BOTH;
ALTER SYSTEM REGISTER;
SHOW PARAMETER local_listener
SHOW PARAMETER spfile
```

Observed source acknowledgements: System altered for both statements; memory value <SOURCE_IP>:1521; SPFILE /u01/app/oracle/product/19.3/db_home/dbs/spfilePRODB.ora. These observed successful SCOPE=BOTH results supersede earlier persistence-pending notes for source.

TARGET identity explicitly verified CDB23AI / target-host before applying:

```sql
ALTER SESSION SET CONTAINER = CDB$ROOT;
SELECT name FROM v$database;
SELECT host_name FROM v$instance;
ALTER SYSTEM SET LOCAL_LISTENER='(ADDRESS=(PROTOCOL=TCP)(HOST=<TARGET_IP>)(PORT=1521))' SCOPE=BOTH;
ALTER SYSTEM REGISTER;
SELECT sid, value, isspecified
FROM v$spparameter
WHERE name = 'local_listener';
```

Observed target result: SID *, endpoint <TARGET_IP>:1521, ISSPECIFIED TRUE. SPFILE /u01/app/oracle/product/26ai/dbhome_1/dbs/spfileCDB23AI.ora. Target persistence is confirmed, superseding earlier pending notes. No database restart was required or performed for this verification; restart survival was not separately exercised.

### Final GoldenGate evidence

| Measure | EXT19C | REP26AI |
|---|---|---|
| State | RUNNING | RUNNING; OGG$REP26AI ATTACHED |
| PID | 122855 | 67362 |
| Last started (displayed) | November 7 16:18 | November 7 13:42 |
| Reported checkpoint lag | 00:00:04 | 00:00:00 |
| Checkpoint updated age | 3 seconds | 9 seconds |
| Trail position | Output sequence 4/RBA 3073 | Read sequence 4/RBA 3073 |
| Source redo read SCN | 15764894 | Not applicable |

Extract redo checkpoint timestamp November 7 17:08:07. Replicat INFO timestamp 23:08:25 UTC / 17:08:25 CST; trail record timestamp 16:38:04, consistent with the earlier test cleanup record time. Replicat LOGBSN 15755670; low watermark 15759775; high watermark 15760096. Watermarks and trail position advanced from the historical values. An older trail record timestamp alone does not prove renewed backlog when read position matches the displayed writer position and no later mapped transaction has been demonstrated.

### Outcome and limits

Local 19c PRODBHR → 26ai PDB23AI replication is operational for the tested HOLA.TEST1 INSERT/UPDATE/DELETE path. Historical redo catch-up completed without a position reset, trail deletion, process recreation, or collision suppression. Fixed-offset reporting discrepancy cleared following the America/New_York correction. Correct LOCAL_LISTENER endpoints are persisted on both databases.

At this November 7 checkpoint, DDL and final UPDATE/DELETE counters had not yet been collected. Section 14 supplies that later evidence. Full historical/schema reconciliation, all-table certification, restart/failover and backup/recovery testing remain outside the completed scope.

Residual follow-ups: intermittent <OGG_ADMIN_USER> management authorization failures; source credential private-rotation confirmation; inspect streams pool allocation if performance symptoms recur; review hostname resolution and HTTP deployment hardening. Read-only supplemental logging inventory remains useful for the full FOX/HOLA scope; the tested table successfully replicated the exercised DML. Avoid treating these follow-ups as proof of an ongoing replication outage.


## 14. DDL, logging and FOX validation — November 8, 2026 update

This section supersedes earlier pending DDL, final TEST1 counter and HOLA logging notes. Times below are displayed deployment times (CST); the source host uses America/New_York. Evidence is from a self-directed lab, not paid production work. Writes were instructed on source PRODBHR only, with multi-execution disabled and target PDB23AI used for SELECT verification. Not every source DML acknowledgement was pasted; matched capture/apply counters independently corroborate the exercised operations.

### 14.1 DDL through the existing wildcard

Source PRODBHR SQL*Plus:

```sql
ALTER SESSION SET CONTAINER = PRODBHR;
SHOW CON_NAME
CREATE TABLE HOLA.GG_DDL_TEST_20261108 (
  id NUMBER PRIMARY KEY,
  name VARCHAR2(50)
);
```

Target PDB23AI SQL*Plus, after source creation:

```sql
ALTER SESSION SET CONTAINER = PDB23AI;
SHOW CON_NAME
DESC HOLA.GG_DDL_TEST_20261108
```

Source only:

```sql
ALTER TABLE HOLA.GG_DDL_TEST_20261108
ADD (ddl_note VARCHAR2(100));
```

Target DESC showed DDL_NOTE. Source-only cleanup:

```sql
DROP TABLE HOLA.GG_DDL_TEST_20261108;
```

Target verification:

```sql
SELECT owner, table_name FROM dba_tables
WHERE owner = 'HOLA' AND table_name = 'GG_DDL_TEST_20261108';
```

No rows after replicated DROP; DESC then returned expected ORA-04043. This is an expected object-absence result, not a GoldenGate apply error. Extract and Replicat initially reported 3 mapped DDL operations, with all Replicat DDL error counters zero. Screenshots showed multi-execution enabled during parts of the earlier session, so the screenshots alone were not treated as sufficient replication evidence; process counters corroborated the three operations.

SOURCECATALOG PRODBHR plus TABLE HOLA.* includes matching HOLA tables. TABLE FOX.* is a different schema rule: HOLA.FOX is covered by HOLA.*, not by FOX.*. DDL INCLUDE MAPPED captures supported DDL for selected objects; matching Replicat mapping directs apply. A wildcard selects scope; it does not copy historical rows. A new table created and populated during active, correctly configured capture can have its DDL and subsequent DML replicated without a separate historical load. This DDL test independently established CREATE/ALTER/DROP only, not DML on that temporary table.

### 14.2 Three-table comparison and its limits

In source PRODBHR and target PDB23AI, separately:

```sql
SHOW CON_NAME
SELECT 'CHILDREN_NAMES' AS table_name, COUNT(*) AS row_count
FROM HOLA.CHILDREN_NAMES
UNION ALL
SELECT 'FOX', COUNT(*) FROM HOLA.FOX
UNION ALL
SELECT 'TEST1', COUNT(*) FROM HOLA.TEST1;
SELECT * FROM HOLA.CHILDREN_NAMES ORDER BY child_id;
SELECT * FROM HOLA.FOX ORDER BY id;
SELECT * FROM HOLA.TEST1 ORDER BY id;
```

Counts matched: CHILDREN_NAMES 5, FOX 14, TEST1 2 (21 total). Displayed row values matched when compared by ID; differing unsorted order was not a discrepancy. Personal row contents are intentionally omitted here. Historical FOX DATE values were displayed without time-of-day, so exact DATE equality to the second has not been established. These observations do not establish how original rows arrived or a transactionally consistent full-schema reconciliation.

### 14.3 Idle checkpoint investigation and fresh TEST1 delivery

EXT19C remained RUNNING with an unchanged checkpoint at SCN 15956414/time 16:49:44 while reported lag grew from 15:50 to 23:33. Trail output remained sequence 4/RBA 7555; Replicat had read through the same position. A fresh status request was used rather than restarting or resetting anything:

```text
SEND EXTRACT EXT19C, STATUS
```

Response: Recovery complete: Processing data; read SCN 15956420. In source CDB$ROOT:

```sql
ALTER SESSION SET CONTAINER = CDB$ROOT;
SELECT name, current_scn, database_role, open_mode FROM v$database;
SELECT capture_name, state FROM v$goldengate_capture;
```

Source PRODB was PRIMARY/READ WRITE, current SCN 15957091; OGG$CAP_EXT19C was WAITING FOR TRANSACTION. SCN difference alone is not elapsed-time lag. This supported idle capture, but live delivery was checked independently.

After confirming ID 20261108 absent on both sides, source PRODBHR only:

```sql
INSERT INTO HOLA.TEST1 (id, name)
VALUES (20261108, 'GG_LIVE_CHECK_20261108');
COMMIT;
```

Target PDB23AI SELECT showed the row. Source-only cleanup:

```sql
DELETE FROM HOLA.TEST1
WHERE id = 20261108 AND name = 'GG_LIVE_CHECK_20261108';
COMMIT;
```

Target query returned no rows. At approximately 17:35, Extract checkpoint advanced to SCN 15959892/time 17:34:40, reported lag 4 seconds, output sequence 4/RBA 8091. TEST1 counters matched on capture/apply: 2 inserts, 1 update, 2 deletes, zero discards. No restart was needed. These observations support idle checkpoint ageing rather than a sustained delivery failure during this episode. Four-second checkpoint lag is not a measured end-to-end transaction latency.

### 14.4 Supplemental logging and inspection privilege gap

At Admin Client, successful source root login was followed by two read-only checks, each returning OGG-00664 / ORA-01031:

```text
DBLOGIN USERIDALIAS SRC19CROOT
INFO SCHEMATRANDATA PRODBHR.HOLA
INFO TRANDATA PRODBHR.HOLA.*
```

The inspection privilege failure remains unresolved. It is not evidence that logging is absent. No broad grant or logging change was made in response.

Source CDB$ROOT, existing SYSDBA SQL*Plus session:

```sql
ALTER SESSION SET CONTAINER = CDB$ROOT;
SELECT name, supplemental_log_data_min,
       supplemental_log_data_pk, supplemental_log_data_ui, force_logging
FROM v$database;
SELECT username, privilege_type, grant_select_privileges
FROM dba_goldengate_privileges
WHERE username = 'C##GGADMIN';
```

PRODB returned MIN YES, database-wide PK NO, UI NO, FORCE_LOGGING YES. C##GGADMIN returned CAPTURE / GRANT_SELECT_PRIVILEGES YES. The correct column is USERNAME; the earlier erroneous GRANTEE query is not a reusable command and is excluded.

Source PRODBHR:

```sql
ALTER SESSION SET CONTAINER = PRODBHR;
SELECT owner, table_name, log_group_name, log_group_type, always, generated
FROM dba_log_groups
WHERE owner = 'HOLA'
ORDER BY table_name, log_group_name;
SELECT schema_name, supplemental_log_data_pk, supplemental_log_data_ui,
       supplemental_log_data_fk, supplemental_log_data_all
FROM dba_capture_prepared_schemas
WHERE schema_name = 'HOLA';
```

No HOLA table-level log groups were returned. Schema HOLA returned PK IMPLICIT, UI IMPLICIT, FK IMPLICIT, ALL NO. Thus schema-level key logging is present despite the empty table-level view. ALL NO alone does not establish a fault. This is HOLA evidence, not a certification of the separate FOX schema, every datatype, or every future workload. LOGALLSUPCOLS controls Extract handling of available supplemental columns; it is not a substitute for enabling source logging.

### 14.5 Key inventory and FOX primary-key improvement

Source PRODBHR:

```sql
SELECT c.table_name, c.constraint_name, c.constraint_type, c.status,
       cc.column_name, cc.position
FROM dba_constraints c
JOIN dba_cons_columns cc
  ON cc.owner = c.owner AND cc.constraint_name = c.constraint_name
 AND cc.table_name = c.table_name
WHERE c.owner = 'HOLA'
  AND c.table_name IN ('CHILDREN_NAMES', 'FOX', 'TEST1')
  AND c.constraint_type IN ('P', 'U')
ORDER BY c.table_name, c.constraint_name, cc.position;
SELECT i.index_name, i.uniqueness, i.status,
       ic.column_name, ic.column_position
FROM dba_indexes i
JOIN dba_ind_columns ic
  ON ic.index_owner = i.owner AND ic.index_name = i.index_name
WHERE i.table_owner = 'HOLA' AND i.table_name = 'FOX'
ORDER BY i.index_name, ic.column_position;
```

Enabled primary keys: CHILDREN_NAMES.CHILD_ID and TEST1.ID. FOX initially had no P/U constraint and no indexes. Before proposing a key, both source and target were checked:

```sql
SELECT COUNT(*) AS total_rows, COUNT(id) AS nonnull_ids,
       COUNT(DISTINCT id) AS distinct_ids FROM HOLA.FOX;
DESC HOLA.FOX
SELECT constraint_name, constraint_type, status
FROM dba_constraints
WHERE owner = 'HOLA' AND table_name = 'FOX'
  AND constraint_type IN ('P', 'U');
```

Both sides: 14/14/14, no P/U constraint; ID NUMBER(10) nullable, NAME VARCHAR2(100), CREATED_AT DATE, STATUS VARCHAR2(20). Existing ID values were unique/non-null, but were not enforced. In this lab the source-only change was directed as follows:

```sql
ALTER SESSION SET CONTAINER = PRODBHR;
SHOW CON_NAME
ALTER TABLE HOLA.FOX ADD CONSTRAINT FOX_PK PRIMARY KEY (ID);
```

Target PDB23AI verification:

```sql
SHOW CON_NAME
SELECT constraint_name, constraint_type, status, validated
FROM dba_constraints
WHERE owner = 'HOLA' AND table_name = 'FOX' AND constraint_type = 'P';
```

FOX_PK / P / ENABLED / VALIDATED was observed on target. The fourth mapped DDL and zero DDL errors corroborate apply. The source ALTER acknowledgement was not separately pasted; target constraint plus process counters are the retained evidence. No manual target constraint creation was instructed. A production key change additionally requires application/data-model and locking review; unique sample data alone does not establish the business key.

### 14.6 FOX live INSERT/UPDATE/DELETE and selected key

After checking test ID 20261108 absent on both sides, source PRODBHR only, with multi-execution off:

```sql
INSERT INTO HOLA.FOX (id, name, created_at, status)
VALUES (20261108, 'GG_FOX_CDC_TEST', SYSDATE, 'NEW');
COMMIT;
UPDATE HOLA.FOX SET status = 'UPDATED'
WHERE id = 20261108 AND name = 'GG_FOX_CDC_TEST' AND status = 'NEW';
COMMIT;
DELETE FROM HOLA.FOX
WHERE id = 20261108 AND name = 'GG_FOX_CDC_TEST' AND status = 'UPDATED';
COMMIT;
```

Run each mutation separately and verify its target transition before the next. Target read-only checks:

```sql
SELECT id, name,
       TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS created_at, status
FROM HOLA.FOX WHERE id = 20261108;
SELECT COUNT(*) AS row_count FROM HOLA.FOX;
```

Target showed NEW, then UPDATED, then no test row; count restored to 14. Replicat report at 19:55:44 resolved wildcard PRODBHR.HOLA.* to PDB23AI.HOLA.FOX. At 19:56:04 it obtained metadata from the trail, mapped ID/NAME/CREATED_AT/STATUS, and explicitly recorded: "Using the following key columns for target table PDB23AI.HOLA.FOX: ID."

### 14.7 Final counters, evidence and remaining limits

At Admin Client, enter each separately:

```text
STATS EXTRACT EXT19C TOTAL
STATS REPLICAT REP26AI TOTAL
VIEW REPORT REP26AI
```

November 8 19:59:11 Extract / 19:59:21 Replicat:

| Measure | Extract | Replicat |
|---|---:|---:|
| TEST1 inserts / updates / deletes | 2 / 1 / 2 | 2 / 1 / 2 |
| FOX inserts / updates / deletes | 1 / 1 / 1 | 1 / 1 / 1 |
| DML discards (both tested tables) | 0 | 0 |
| Mapped DDL operations | 4 | 4 |

Replicat total transactions 12; DDL errors/retried/discarded/ignored all zero. Direct transactions ratio 33.33% is an execution-path statistic, not a failure rate. The four DDL operations comprise test CREATE, ADD COLUMN, DROP, and FOX primary-key addition. No additional process restart was performed during these tests.

Evidence: Pasted text(20261109-020037).txt (final stats and selected-key report); Pasted text(20261109-014505).txt (fourth DDL); image(20261109-013104).png (schema logging); image(20261109-012953).png (capture privilege and table-log-group result); image(20261109-015732).png (FOX update target); image(20261109-015828).png (FOX cleanup/count); earlier DDL screenshots and pasted SQL in this conversation. Filename UTC dates may be November 9 while displayed CST evidence dates are November 8.

Open: CHILDREN_NAMES live DML not independently tested; exact full-time historical FOX DATE comparison pending; source logging-inspection ORA-01031 unresolved; separate FOX-schema logging not inventoried; source private credential rotation unconfirmed; management authorization, TLS/hostname and conditional memory follow-ups remain. No full consistent-snapshot reconciliation, restart/failover test or measured delivery SLA is claimed. Final FOX counters are current to 19:59; the last pasted four-second Extract checkpoint snapshot was 17:35, not a new 19:59 lag measurement.