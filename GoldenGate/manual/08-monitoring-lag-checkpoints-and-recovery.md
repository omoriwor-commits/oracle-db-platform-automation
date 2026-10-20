# 08 — Monitoring, Checkpoints and Recovery

**Scope:** GoldenGate 26ai process monitoring, checkpoint interpretation, trail retention and incident recovery. Process names are illustrative; recorded results belong in project evidence.
>
> **Reference scope:** Oracle-documented procedures and illustrative examples. Lab results are recorded separately.
>
**Operational approach:** Diagnose first, preserve checkpoints and logs, remediate under change control, then validate target data.

## Scope and operational diagnostics

This page covers:
1. Distinguish process status, lag at checkpoint, true process lag and end-to-end heartbeat lag.
2. Trace failures through Extract, source trail, Distribution, Receiver, target trail, Replicat and target rows.
3. Explain checkpoints and why missing redo or trails can defeat a restart.
4. Plan checkpoint-aware trail purging without deleting data needed by downstream consumers.
5. Capture a reproducible incident record and test recovery with source-target reconciliation.

## 1. Establish the whole topology before diagnosis

~~~text
Source DB redo
   -> Extract [source redo / capture checkpoint]
   -> source trail ea [sequence + RBA]
   -> Distribution Path [input/output position]
   -> Receiver [target trail delivered]
   -> target trail eb [sequence + RBA]
   -> Replicat [read + applied checkpoint]
   -> Target Oracle database [verified committed rows]
~~~

**Rules:** A RUNNING state proves only that a process is running (it may also be suspended). A zero lag value does not prove transactions have been delivered. A restarted process may display reset statistics. A successful path does not prove target data correctness. A source or target with no changes may legitimately show little throughput.

## 2. Initial investigation: safe read-only commands

**Execution context:** Connect Admin Client to the *correct* Microservices deployment; avoid plaintext passwords in examples. Use your actual process names in place of EXTLAB and REPLAB.

~~~text
INFO ALL
INFO EXTRACT EXTLAB, DETAIL
INFO EXTRACT EXTLAB, SHOWCH
LAG EXTRACT EXTLAB
STATS EXTRACT EXTLAB
INFO DISTPATH ALL
INFO REPLICAT REPLAB, DETAIL
INFO REPLICAT REPLAB, SHOWCH
LAG REPLICAT REPLAB
STATS REPLICAT REPLAB
~~~

Run each command only in an administration context where supported. A path may exist in a different deployment; check source and target separately. For a target-initiated path, inspect the corresponding Receiver Service Path rather than assuming INFO DISTPATH displays it.

| Command | Operational interpretation | Caveat |
|---|---|---|
| INFO ALL | Broad process inventory and lag-at-checkpoint indicators | Does not prove that apply is correct |
| INFO EXTRACT ... SHOWCH | Input/recovery/next/output capture checkpoint detail | Capture continuity depends on redo retention |
| LAG EXTRACT | More direct lag measurement than INFO's checkpoint-based value | Idle stream and clock differences complicate interpretation |
| STATS EXTRACT | Capture operation counters | Counters and scopes require interpretation |
| INFO DISTPATH ... DETAIL | Transport path identity and checkpoint evidence | Transport is not target apply |
| INFO REPLICAT ... SHOWCH | Current and historical trail/checkpoint positions | Checkpoint not sufficient to prove row consistency |
| LAG REPLICAT | More direct process-to-trail lag than INFO REPLICAT | Not the same as source-to-target end-to-end latency |
| STATS REPLICAT | Apply operation statistics | Counters can include filtered/restarted windows |

**Vendor:** Oracle 26ai INFO ALL, LAG EXTRACT, LAG REPLICAT and INFO REPLICAT in references below.

## 3. Lag: four different questions

**Capture lag:** how far behind is Extract in reading committed source changes?

**Transport lag:** how long do records wait between local trail creation and receiver delivery?

**Apply lag:** how far behind is Replicat relative to target trail records?

**End-to-end latency:** time from a source change through a successfully delivered/applied target change.

Oracle documents LAG EXTRACT and LAG REPLICAT as more direct estimates than the checkpoint lag reported by INFO. **Do not add independent lag fields mechanically** and call their sum an exact source-to-target service-level result: clocks, idle periods and differing measurement semantics matter.

For a supported database setup, GoldenGate **heartbeat tables** provide monitoring of replication path latency and historical trends, with the required database objects and privileges. Establish them under a separate approved configuration procedure; do not assume heartbeat functionality is already configured.

### Checkpoint-age alert thresholds

A statement such as *time since checkpoint must be below ten seconds* is **not a universal GoldenGate rule**. Define workload-specific latency objective, acceptable idle behavior, alert thresholds and on-call response policy. A quiet source should not automatically produce the same metrics as an active one.

## 4. Checkpoints, trail sequences and the restart model

A GoldenGate trail is persisted in numbered sequence files. The **RBA** is an offset within a trail file. Process checkpoints and recovery positions determine where capture, transport and apply can continue without intentionally skipping data.

For integrated Extract, redo retention must account for the **recovery checkpoint**, which can be older than the current read checkpoint because a long-running transaction began earlier. Oracle documents distinct Input, Recovery, Next and Output checkpoints under INFO EXTRACT ... SHOWCH.

For Replicat, recovery depends on the target trail history, its checkpoint and target apply semantics. A missing file between required trail sequence numbers may block downstream processing; the right response is to investigate retention and recover required data, not force the process past the gap.

### Read-only host observations

~~~bash
df -hT
ls -lh "$OGG_DATA_HOME"
# Use the real deployment trail directory and service account.
# Preserve relevant file metadata and logs before altering anything.
~~~

Do not run filesystem cleanup against a guessed path.

## 5. Trail purging and redo retention

**Source archived redo:** Oracle's guidance says a log may be removed safely from GoldenGate's perspective only when Extract's read/recovery constraints have moved beyond it. Database backup/recovery requirements and other consumers (including standby/recovery) may require retaining it longer. Use the approved RMAN/archive-log policy, **not shell rm** based on one number.

**GoldenGate trails:** configure GoldenGate's supported **Purge Trails** maintenance task. Oracle recommends checkpoint-based purging. If **Use Checkpoints** is disabled, a time/file-count retention rule can purge a trail whether or not it has been consumed. That can permanently break downstream catch-up.

Pre-purge approval checklist:
- Are Extract, all Distribution/Receiver Paths and Replicats correctly identified, including offline or paused consumers?
- Which exact source/target sequence and RBA is the **oldest still needed**?
- Are long transactions, planned maintenance windows, replay/reconciliation and restore procedures accounted for?
- Is disk utilization projected to remain safe even when downstream apply stops?
- Has the retention and restore policy been documented and tested?

**Never:** delete a trail manually because disk usage is high, purge archived redo solely from current INFO lag, or reposition a process to NOW to silence an incident.

## 6. Incident triage decision path

~~~text
Reported delayed/incorrect target rows
          |
          v
Confirm source COMMIT and expected mapped table
          |
          +-- Extract not advancing?
          |      -> scope/logging/registration/source redo/report
          |
          +-- Source trail not advancing?
          |      -> Extract trail binding, error, path, disk
          |
          +-- Distribution/Receiver stalled?
          |      -> prefix/sequence, TLS/authentication, ports, path filtering
          |
          +-- Target trail advancing, Replicat stalled?
          |      -> MAP, target connection, SQL errors, constraint/lock, checkpoint
          |
          +-- All processes advancing, rows still wrong?
                 -> initial-load boundary, filters, data transformation,
                    missing keys, unsupported operations, reconciliation
~~~

### Common symptoms

| Symptom | Evidence to gather | Safer first response |
|---|---|---|
| EXTRACT ABENDED | Exact OGG error, Extract report, Oracle capture state, redo availability | Restore cause after diagnosing; avoid unregister/recreate |
| Replicat ABENDED on constraint | Target row/key, MAP, source key logging, instantiation position | Investigate baseline or divergence; don't hide error |
| Source trail advances but path is stopped | Distribution status, source prefix, TLS and network, path report | Preserve delivered/undelivered positions |
| Receiver reports missing trail | Target directory, permission, free space, endpoint URI | Restore correct delivery route, not checkpoint skipping |
| Lag spikes then recovers | Throughput/long transactions/resource pressure | Trend against SLA before escalating |
| Lag stuck with idle traffic | Heartbeat activity, last committed source test, checkpoint age | Controlled DML proof, not just restarting |
| Disk almost full | Trail and archive retention, oldest consumer checkpoint | Capacity/retention plan; no manual deletion |
| Process RUNNING but rows incorrect | Source/target query, object filters, mapping, instantiation SCN | Reconcile and document exact divergence |

## 7. Parameter changes and restart discipline

For parameter changes, obtain approval; capture current reports/checkpoints; back up parameters; edit and validate; restart only affected processes when required; and observe downstream recovery. Apply this with awareness of shared paths and live transactions.

1. Capture INFO/lag/checkpoint/stats and process report **before** modification.
2. Save a sanitized configuration diff and accurate rollback file.
3. Confirm operator, service mode, target deployment, maintenance window and restart dependencies.
4. Make only one controlled change at a time when possible.
5. Restart through **supported** Administration Service/Admin Client workflow, not ad hoc kill.
6. Compare process state, checkpoint progression, backlog behavior, report and target DML before declaring recovery.

**High-risk commands/actions requiring separate review:** STOP/START process when affecting production, ALTER/DELETE EXTRACT or REPLICAT, SKIPTRANSACTION, CSN repositioning, FORCESTOP, deleting trails, disabling supplemental logging, changing checkpoint tables, changing autostart/restart or purge policies.

## 8. Case study: orphaned Microservices during OGGCA deployment

A previously documented lab incident found that a DEP1 deployment's Admin, Distribution, Receiver and Metrics processes remained alive even after Service Manager had stopped. OGGCA could report deployment conflict despite an apparently stopped manager.

**Read-only initial commands:**

~~~bash
systemctl status OracleGoldenGate --no-pager
ss -lntp
ps -ef | grep -E 'adminsrvr|distsrvr|recvsrvr|pmsrvr|ServiceManager' | grep -v grep
~~~

Correlate process IDs, port ownership, service mode, deployment home and logs. Do not blindly kill all matching processes or overwrite credential wallets. This is an existing historical lab lesson, not a newly reproduced troubleshooting test.

Related project: https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/docs/goldengate/troubleshooting/goldengate-26ai-oggca-daemon-registration-troubleshooting.md

## 9. Troubleshooting scenarios

**RUNNING but missing rows:** source transaction/query, current Extract trail/position, transport path and Receiver positions, Replicat report/checkpoint, mapping/filters and actual target query. RUNNING is not the conclusion.

**Recovery checkpoint:** Extract may need the earlier redo to recover/assemble the long-running transaction. Retain it until all Oracle/GoldenGate consumers and recovery policies permit purge.

**Trail retention:** source/target trail data needed by the downstream checkpoint may be deleted before apply resumes. Use a checkpoint-aware maintenance design plus tested retention/recovery policy.

**End-to-end latency:** distribution/receiver delay, heartbeat design, application commit and observation timestamps, mapping/filtering, source/target clock quality, and whether the transaction actually reached the target.

## 10. Incident evidence template

~~~text
Incident / change ID:
Date, start and end times, timezone:
Source/target database versions and GoldenGate build:
Service Manager deployment and process names:
Observed business impact, objects and test transaction:
INFO ALL / Extract and Replicat INFO, SHOWCH and LAG timestamps:
Source trail prefix, sequence, RBA and retention:
Distribution/Receiver path, status, checkpoint, error:
Target trail prefix, sequence, RBA:
Replicat MAP, checkpoint, report and target apply state:
Relevant Oracle DB errors, locks, redo/archive availability:
Heartbeat or independent end-to-end latency:
Root cause: CONFIRMED / SUSPECTED / UNKNOWN
Change approval and exact remediation steps:
Post-recovery transaction and source-target row reconciliation:
Remaining risks, monitoring and follow-up:
Evidence files and sanitized links:
~~~

## Evidence and validation status

- **Operational scope:** Process status, parameter review, trail checkpoints, reports and recovery controls.
- **Oracle-documented:** INFO/LAG/STATS distinctions; heartbeat; Extract recovery checkpoint; checkpoint-aware purging.
- **Examples:** Process names and the decision tree are illustrative; the linked DEP1 event is documented separately.

## Official Oracle GoldenGate 26ai references

- [INFO ALL](https://docs.oracle.com/en/database/goldengate/core/26/gclir/info-all.html)
- [INFO REPLICAT](https://docs.oracle.com/en/database/goldengate/core/26/gclir/info-replicat.html)
- [LAG EXTRACT](https://docs.oracle.com/en/database/goldengate/core/26/gclir/lag-extract.html)
- [LAG REPLICAT](https://docs.oracle.com/en/database/goldengate/core/26/gclir/lag-replicat.html)
- [STATS EXTRACT](https://docs.oracle.com/en/database/goldengate/core/26/gclir/stats-extract.html)
- [STATS REPLICAT](https://docs.oracle.com/en/database/goldengate/core/26/gclir/stats-replicat.html)
- [Monitor Lag and Heartbeats](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/monitor-monitor-lag.html)
- [Purging Archive Logs](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/purging-archive-logs.html)
- [Automate Maintenance Tasks — Purge Trails](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/automate-maintenance-tasks-1.html)

**Next:** [09 — Parameters, Filtering, Mapping and Collisions](09-parameters-filtering-mapping-and-collisions.md)
