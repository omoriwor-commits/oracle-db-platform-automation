# Oracle 19c to 26ai GoldenGate Replication Recovery — November 7–8, 2026

**Project:** Oracle Database Platform Automation — local Oracle 19c → 26ai GoldenGate replication
**Status:** Local lab replication operational for tested TEST1 and FOX DML; four mapped DDL operations applied with zero DDL errors. Updated through November 8, 19:59 CST. Current follow-ups and evidence limits are in Appendix D.

## 1. Summary

My Oracle 19c to 26ai GoldenGate replication path had stopped advancing. Its read checkpoint dated from August, with later failed restart attempts. After a lab network change, I found stale target listener configuration and an incorrect target credential-store address. Source and target authentication failures were also recorded. The timing makes the network change a probable contributor; it does not prove the cause of the original August stop.

I corrected the listener and credentials, validated with RMAN that the archived redo required by the capture was intact, and resumed the existing Extract and Replicat. I did not reset checkpoints, use HANDLECOLLISIONS, skip transactions or recreate processes. During catch-up, a steady one-hour lag remained. I traced it to a fixed `-04:00` source time zone offset that became wrong when daylight saving time ended on November 1, and replaced it with a region-based setting. Lag fell to about four seconds, and a live INSERT, UPDATE and DELETE test on the source was reflected on the target.

## 2. Environment

| Component | Configuration |
|---|---|
| Source | Oracle Database 19c, CDB `PRODB`, PDB `PRODBHR`, Oracle Linux 7.9, `source-host` |
| Source role | PRIMARY of a Data Guard configuration |
| Target | Oracle AI Database 26ai, CDB `CDB23AI`, PDB `PDB23AI`, Oracle Linux 9.8, `target-host` |
| GoldenGate | 26ai Microservices (23.26.1.0.0), deployment `DEP1`, running on the target host |
| Capture | Integrated Extract `EXT19C`, remote capture from the 19c source |
| Trail | Local trail `lt` |
| Apply | Integrated Replicat `REP26AI` into `PDB23AI` |
| Replicated schemas | `FOX`, `HOLA` |

```text
Oracle 19c / PRODBHR (source-host)
        | Oracle Net: remote Integrated Extract EXT19C
        v
GoldenGate 26ai deployment DEP1 (target-host) -> local trail lt
        | Integrated Replicat REP26AI
        v
Oracle AI Database 26ai / PDB23AI (target-host)
```

My OCI and Azure trial environments were retired. No dependency on those retired cloud routes was established for this local recovery.

## 3. Timeline (November 7, 2026)

| Time (CST) | Event |
|---|---|
| Before Nov 7 | Replicat report shows an August abend after ORA-41900 (missing INSERT privilege on `HOLA.TEST1`) and ORA-26804 (apply disabled). September logs show source credential failures, target hostname resolution failures and Extract restart attempts. |
| Before 13:37 | Target listener down; started it. Found target `LOCAL_LISTENER` pointing to an old address. Corrected it and re-registered services. |
| Before 13:37 | Updated existing source and target credential-store entries and synchronized passwords. Confirmed database logins; private rotation of the exposed source password remains unconfirmed. |
| Before 13:37 | Confirmed source capture DISABLED with its required checkpoint SCN. Located the covering archive log and validated the required archives with RMAN. |
| 13:37 | Started Extract `EXT19C`. It recovered its existing state and attached to the capture. No checkpoint reset. |
| 13:42 | Started Replicat `REP26AI`. It attached and rolled over to the next trail file. |
| Afternoon | Monitored catch-up through the backlog. Lag fell from approximately 83 days through the backlog to about one hour, then stayed near one hour. |
| 15:54 | Compared host clocks and time zones. Source on America/New_York (EST, DST ended Nov 1), NTP synchronized. |
| 16:10 | Stopped Extract gracefully and replaced the fixed `-04:00` offset with `America/New_York`. |
| 16:17 | Restarted Extract. |
| 16:22 | Extract lag about 4 seconds. |
| 16:30–16:38 | Target screenshots show the test INSERT, UPDATE and DELETE transitions; INSERT counters captured at 16:31–16:32. |
| After the DML test | Correct source and target listener endpoints persisted with `SCOPE=BOTH`; target SPFILE value explicitly verified. |
| 17:08 | Extract RUNNING with 4-second lag; Replicat RUNNING/ATTACHED with zero lag. Both displayed trail sequence 4/RBA 3073. |

## 4. Contributing causes

1. **Connection configuration problems.** The target `LOCAL_LISTENER` referenced an old address, and a target credential-store entry contained a malformed address. Historical logs also recorded hostname resolution and connection failures. These are confirmed findings; attribution of every failure to the provider change is not established.
2. **Credential failures.** Source logins failed during earlier restart attempts. Passwords were reset and the aliases resynchronized.
3. **Fixed time zone offset.** `TRANLOGOPTIONS SOURCE_OS_TIMEZONE -04:00` was correct during daylight saving time but one hour off after November 1. This produced the steady one-hour reported lag after catch-up.
4. **Historical apply error.** The August Replicat abend (ORA-41900) is recorded in the report. On November 7 the privilege was already in place, so no grant was needed. I did not grant additional broad privileges.

The network change is a probable contributing event. Stale connection settings are confirmed, but the exact cause and chronology of the original August stop are not fully established.

## 5. Resolution

### 5.1 Target listener

```bash
lsnrctl start
```

In target `CDB$ROOT`:

```sql
ALTER SYSTEM SET LOCAL_LISTENER='(ADDRESS=(PROTOCOL=TCP)(HOST=<TARGET_IP>)(PORT=1521))' SCOPE=MEMORY;
ALTER SYSTEM REGISTER;
```

Both `CDB23AI` and `pdb23ai` services registered READY. The initial emergency change used `SCOPE=MEMORY`. After explicitly verifying target identity as `CDB23AI` on the target host, I persisted it:

```sql
ALTER SESSION SET CONTAINER = CDB$ROOT;
SELECT name FROM v$database;
SELECT host_name FROM v$instance;
SHOW PARAMETER spfile

ALTER SYSTEM SET LOCAL_LISTENER='(ADDRESS=(PROTOCOL=TCP)(HOST=<TARGET_IP>)(PORT=1521))' SCOPE=BOTH;
ALTER SYSTEM REGISTER;

SELECT sid, value, isspecified
FROM v$spparameter
WHERE name = 'local_listener';
```

The target SPFILE entry returned SID `*`, the correct target listener endpoint and `ISSPECIFIED=TRUE`. The source listener endpoint was also saved with `SCOPE=BOTH` and registered, using `<SOURCE_IP>:1521`. A wrong-host entry during this step was corrected immediately; only the correct endpoint commands are retained here. Verify database and host identity before each `ALTER SYSTEM` operation. No database restart was required; restart survival was not separately tested.

### 5.2 Credential store

```text
/u02/ogg26ai_home/bin/adminclient
CONNECT http://localhost:<SM_PORT> DEPLOYMENT DEP1 USER <OGG_ADMIN_USER>

ALTER CREDENTIALSTORE REPLACE USER <TARGET_APPLY_USER>@<TARGET_IP>:1521/pdb23ai ALIAS TGT26AI DOMAIN OracleGoldenGate
DBLOGIN USERIDALIAS TGT26AI

ALTER CREDENTIALSTORE REPLACE USER <SOURCE_CAPTURE_USER>@<SOURCE_IP>:1521/PRODB ALIAS SRC19CROOT DOMAIN OracleGoldenGate
DBLOGIN USERIDALIAS SRC19CROOT
```

The credential-store replacement commands omitted the PASSWORD option and prompted for hidden input. Earlier database password reset activity included an exposed inline value, which is excluded from this report; subsequent private source rotation remains a follow-up. Both alias logins succeeded. `EXT19C` uses the root alias `SRC19CROOT`.

### 5.3 Required redo validation before resuming

In source `CDB$ROOT`:

```sql
SELECT capture_name, status, required_checkpoint_scn
FROM dba_capture
WHERE purpose = 'GoldenGate Capture';
```

Capture `OGG$CAP_EXT19C` was DISABLED with required checkpoint SCN 10782180.

```sql
SELECT thread#, sequence#, first_change#, next_change#, deleted, status, name
FROM v$archived_log
WHERE first_change# <= 10782180
  AND next_change# > 10782180
  AND resetlogs_change# = (SELECT resetlogs_change# FROM v$database)
ORDER BY thread#, sequence#, dest_id;
```

Thread 1, sequence 105 covered the required SCN, with a local FRA copy available.

```text
RMAN> BACKUP VALIDATE ARCHIVELOG FROM SEQUENCE 105 THREAD 1;
```

Sequences 105–177 (73 logs) validated with zero failing blocks. A continuity query against `v$archived_log` confirmed all 73 sequences present. This established readability and recorded sequence continuity for the selected archive range, supporting resumption of the existing capture. It did not by itself guarantee end-to-end consistency.

### 5.4 Resume existing processes

```text
DBLOGIN USERIDALIAS SRC19CROOT
START EXTRACT EXT19C
INFO EXTRACT EXT19C DETAIL

DBLOGIN USERIDALIAS TGT26AI
START REPLICAT REP26AI
INFO REPLICAT REP26AI DETAIL
```

Extract validated its existing bounded recovery state and attached to `OGG$CAP_EXT19C`. Replicat attached and rolled over from trail sequence 2 to sequence 3. After restart, `v$goldengate_capture` showed the capture in state CAPTURING CHANGES.

Catch-up progress, sampled on November 7:

| Redo timestamp at read checkpoint | Read SCN | Reported lag |
|---|---|---|
| Aug 14 | 10782542 | Starting position |
| Aug 20 | 12214320 | — |
| Sep 11 | 13628750 | ~57 days |
| Oct 18 | 13831060 | ~20 days |
| Oct 18 | 13864176 | ~20 days |

The dates are the timestamps of the redo being read, not the times I checked. All samples were taken on November 7 while Extract worked through the backlog. A short interval with an unchanged read SCN did not indicate a stall; later samples showed continued progress.

### 5.5 Time zone correction

After catch-up, Extract held a steady lag of about 01:00:04. Host checks:

```bash
date '+%Y-%m-%d %H:%M:%S %Z %z'
date -u '+%Y-%m-%d %H:%M:%S UTC'
timedatectl status
```

The source host was on America/New_York (EST, UTC-5), NTP synchronized, with daylight saving time ended on November 1. The Extract parameter still used the fixed daylight-time offset `-04:00`.

```text
STOP EXTRACT EXT19C
-- edit parameters: TRANLOGOPTIONS SOURCE_OS_TIMEZONE America/New_York
VIEW PARAMS EXT19C
START EXTRACT EXT19C
VIEW REPORT EXT19C
INFO EXTRACT EXT19C DETAIL
```

Extract restarted cleanly. OGG-01438 reported that the saved output checkpoint expected trail sequence 2 while sequence 3 existed. Extract's output recovery scan completed and it continued normally; no trail deletion or checkpoint reset was performed. Lag then read 00:00:04.

## 6. Validation

**Baseline:** test ID `20261107` absent on both source `PRODBHR` and target `PDB23AI`.

The test procedure directed all writes and commits to source `PRODBHR`, with SELECT-only checks on target `PDB23AI`. Supplied target screenshots show the expected transitions. Source DML/COMMIT acknowledgements were not separately pasted; INSERT capture and apply are independently corroborated by both process statistics.

| Step | Source statement | Target result |
|---|---|---|
| INSERT | `INSERT INTO HOLA.TEST1 (id, name) VALUES (20261107, 'GG_RECOVERY_20261107'); COMMIT;` | Row present |
| UPDATE | `UPDATE HOLA.TEST1 SET name = 'GG_RECOVERY_UPDATE_20261107' WHERE id = 20261107; COMMIT;` | Updated value present |
| DELETE | `DELETE FROM HOLA.TEST1 WHERE id = 20261107 AND name = 'GG_RECOVERY_UPDATE_20261107'; COMMIT;` | Row removed |

For the INSERT, Extract statistics showed one INSERT from `PRODBHR.HOLA.TEST1` and Replicat statistics showed one INSERT applied to `PDB23AI.HOLA.TEST1`, with zero discards. Existing rows (IDs 1 and 2) were not touched.

**Original November 7 scope:** one-table DML validation. Appendix D extends this to FOX DML, four DDL operations and HOLA logging inspection. Full historical consistency and every-table validation remain unproven.

## 7. Final operational evidence and remaining checks

Final process output was collected November 7, 2026, around **17:08 CST**:

| Measure | Extract EXT19C | Replicat REP26AI |
|---|---|---|
| State | RUNNING | RUNNING; inbound server ATTACHED |
| PID | 122855 | 67362 |
| Reported lag | 00:00:04 | 00:00:00 |
| Trail position | Output sequence 4/RBA 3073 | Read sequence 4/RBA 3073 |
| Redo read SCN | 15764894 | — |

Replicat low/high watermarks advanced to **15759775 / 15760096**, respectively. Its older trail-record timestamp alone does not demonstrate backlog: the displayed reader position matches the writer position, and the test DML reached the target.

Completed:

- [x] Resumed capture and apply from existing checkpoints.
- [x] Cleared the historical capture backlog; observed low lag after correction of the source time zone setting.
- [x] Verified INSERT, UPDATE and DELETE target transitions on `HOLA.TEST1`; removed the test row through the source test procedure.
- [x] Captured matching INSERT statistics with zero discards.
- [x] Persisted correct source and target listener endpoints; explicitly verified target SPFILE entry.
- [x] Captured final RUNNING/ATTACHED states, low lag and matching displayed trail positions.

Remaining:

- [x] Collected matching final TEST1 and FOX DML counters, including UPDATE/DELETE (Appendix D).
- [ ] Finish logging inventory for the separate FOX schema and resolve Admin Client logging-inspection privileges. HOLA schema-level key logging is confirmed (Appendix D).
- [ ] Investigate intermittent management authorization failures; several occurred and retries succeeded. Root cause remains unconfirmed.
- [ ] Confirm private source credential rotation and synchronization of actual consumers after exposure.
- [ ] Review `streams_pool_size` warning OGG-02045 if performance symptoms warrant; no memory starvation was demonstrated.
- [ ] Inventory GLOBALS `GGSCHEMA` objects and dependencies before considering any change. Leave the setting unchanged meanwhile.
- [ ] Plan management-service TLS/access hardening separately from this recovery.
- [x] Verified test-table CREATE/ALTER/DROP and FOX primary-key DDL apply (Appendix D).
- [ ] Complete full historical/schema reconciliation and restart/failover testing if required; neither is established by the completed lab tests.

## 8. Lessons learned

- **Use the source's configured time zone region.** A fixed offset does not follow DST. Here, the saved `-04:00` differed from the source's current EST `-05:00`; using `America/New_York` removed the persistent one-hour reported discrepancy after restart.
- **Manage endpoint changes consistently.** Inventory listener settings, Oracle Net aliases and credential-store connect strings after network changes. Stable DNS names or managed host mappings may reduce future edits when resolution is reliable; they were not introduced in this recovery.
- **Verify identity before configuration changes.** Confirm database, host and container in the actual session before issuing `ALTER SYSTEM`.
- **Persist emergency fixes.** Check SPFILE/PFILE usage and save intended dynamic changes appropriately. Verify saved values instead of assuming a successful memory change survives restart.
- **Validate required redo.** Archive availability, sequence continuity and RMAN readability checks supported checkpoint-based recovery without skipping transactions.
- **Monitor process state, checkpoint movement and end-to-end behavior.** Zero Replicat lag alone did not establish pipeline currency while Extract was behind. Lag and checkpoint monitoring are recommended follow-ups; this report does not establish when the original issue was first noticed.

## Appendix A. Parameter files

`EXT19C`:

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

`REP26AI`:

```text
REPLICAT REP26AI
USERIDALIAS TGT26AI
DBOPTIONS ENABLE_INSTANTIATION_FILTERING
MAP PRODBHR.FOX.*, TARGET FOX.*;
MAP PRODBHR.HOLA.*, TARGET HOLA.*;
```

## Appendix B. Reading GoldenGate messages correctly

| Message | Meaning in this incident |
|---|---|
| Error log path in `INFO DETAIL` | Identifies the log file; not a new error |
| "Source Not Available" in INFO | Missing metadata in that view; not proof of missing redo |
| Outbound server SCNs "Unavailable" | Observed with Admin Client logged into the target; these fields alone do not prove source capture failure |
| OGG-02045 | `streams_pool_size` not set explicitly; capture attached normally |
| OGG-04033 | Expected effect of `LOGALLSUPCOLS` |
| OGG-12062 | Management request not authorized; separate from database login and capture |
| "OCI call [ORA]" | Oracle Call Interface, not Oracle Cloud Infrastructure |

## Appendix C. File locations

| Item | Path |
|---|---|
| Parameter files | `/u02/ogg26ai_deploy/etc/conf/ogg/` |
| Reports | `/u02/ogg26ai_deploy/var/lib/report/` |
| Error log | `/u02/ogg26ai_deploy/var/log/ggserr.log` |
| Checkpoints | `/u02/ogg26ai_deploy/var/lib/checkpt/` |
| Trails | `/u02/ogg26ai_deploy/var/lib/data/dirdat/` |

## Security

Network addresses, host names and credential identities in connection examples use placeholders. Lab database, schema, process, deployment and alias names, version details and local file paths remain for technical context; this is not complete anonymization. No password values, wallet files or credential-store secret material are included. This public edition omits raw transcripts/screenshots and personal data; evidence summaries are derived from retained lab records.

## Appendix D. November 8 validation update — current evidence

This update supersedes the earlier one-table-only validation scope. It records a self-directed local lab. Source writes were instructed only in PRODBHR; target PDB23AI was queried separately. Selected source acknowledgements were not pasted, but matching Extract/Replicat counters independently corroborate the exercised DML/DDL. No passwords or network addresses are added here.

### DDL and wildcard scope

The temporary HOLA.GG_DDL_TEST_20261108 table was created on source, altered to add DDL_NOTE, then dropped. Target checks showed the table, the added column and subsequent absence. The expected post-DROP ORA-04043 was not an apply error. Three mapped DDL operations were recorded on capture/apply, with zero Replicat DDL errors. Existing TABLE HOLA.* under SOURCECATALOG PRODBHR and MAP PRODBHR.HOLA.*, TARGET HOLA.* covered the object; DDL INCLUDE MAPPED enabled supported DDL capture. Wildcard scope does not perform a historical initial load. The separate TABLE FOX.* rule refers to schema FOX; HOLA.FOX belongs to schema HOLA.

### Data comparison and idle capture

Source and target counts matched: CHILDREN_NAMES 5, FOX 14, TEST1 2. Displayed values matched by ID. Personal row contents are omitted. Historical FOX dates were formatted without times; an exact full-DATE comparison and consistent-snapshot reconciliation were not performed.

During a later idle interval, Extract's checkpoint stayed at SCN 15956414 while reported lag rose to 23:33. SEND EXTRACT EXT19C, STATUS responded with Processing data; source V$GOLDENGATE_CAPTURE reported WAITING FOR TRANSACTION. A controlled TEST1 insert (ID 20261108) reached target, followed by a source delete that removed it on target. Without restart, the read checkpoint advanced to SCN 15959892 and reported lag returned to four seconds around 17:35 CST. This supports idle checkpoint ageing rather than a sustained delivery failure for that episode; four-second checkpoint lag is not measured transaction latency.

### Logging and privilege evidence

Source root: minimal supplemental logging YES, database-wide PK/unique logging NO, FORCE_LOGGING YES. DBA_GOLDENGATE_PRIVILEGES returned C##GGADMIN / CAPTURE / GRANT_SELECT_PRIVILEGES YES. In PRODBHR, no HOLA table-level log groups were returned, but DBA_CAPTURE_PREPARED_SCHEMAS showed HOLA PK/unique/foreign-key logging IMPLICIT, all-column logging NO. The empty table-level view therefore did not establish missing logging. No blanket grants or logging changes were made.

Admin Client INFO SCHEMATRANDATA and INFO TRANDATA under the successful source root alias both returned ORA-01031. The exact missing inspection privilege or container scope remains unresolved; capture privilege registration alone does not resolve it.

### FOX primary key and live data changes

CHILDREN_NAMES had an enabled primary key on CHILD_ID; TEST1 on ID. FOX initially had no primary/unique constraint or index. On each side, all 14 FOX IDs were populated and distinct, although the column was nullable. After these checks, a source-only ALTER TABLE HOLA.FOX ADD CONSTRAINT FOX_PK PRIMARY KEY (ID) was directed. Target showed FOX_PK ENABLED/VALIDATED and DDL counters increased to four with zero errors. Production adoption would also require application-key and locking review; uniqueness in current lab data alone does not establish a business key.

A temporary FOX row (ID 20261108, GG_FOX_CDC_TEST) was inserted, updated from NEW to UPDATED, then deleted through separate source commits, with target checks between operations. Target returned to 14 rows. At 19:55:44 the wildcard resolved for FOX; at 19:56:04 Replicat explicitly selected ID as its target key and mapped ID, NAME, CREATED_AT and STATUS from trail metadata.

### Final counters — November 8, 19:59 CST

| Measure | Extract | Replicat |
|---|---:|---:|
| TEST1 inserts / updates / deletes | 2 / 1 / 2 | 2 / 1 / 2 |
| FOX inserts / updates / deletes | 1 / 1 / 1 | 1 / 1 / 1 |
| DML discards | 0 | 0 |
| Mapped DDL operations | 4 | 4 |

Replicat reported 12 total transactions; DDL errors, retried, discarded and ignored errors were all zero. The DDL count comprises temporary-table CREATE/ADD COLUMN/DROP and FOX_PK addition. Direct transactions ratio 33.33% is not an error rate. Latest counters do not supply a fresh 19:59 lag snapshot; the last pasted four-second Extract snapshot was around 17:35.

### Evidence and remaining limits

Evidence: final stats/report Pasted text(20261109-020037).txt; fourth DDL Pasted text(20261109-014505).txt; schema logging image(20261109-013104).png; privilege/log-group checks image(20261109-012953).png; FOX update and cleanup images image(20261109-015732).png and image(20261109-015828).png; preceding pasted SQL/DDL screenshots. Filename dates are UTC-oriented; displayed deployment evidence is November 8 CST.

Still open: independent CHILDREN_NAMES live DML test; exact historical FOX DATE comparison; Admin Client logging-inspection ORA-01031; separate FOX-schema logging inventory; private source credential rotation confirmation; intermittent management authorisation and HTTP/TLS/hostname follow-ups. Full schema reconciliation, restart/failover and a delivery SLA were not demonstrated. These limits do not negate the successful tested TEST1/FOX delivery or four completed DDL operations.