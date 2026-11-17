# Incident Postmortem — Oracle GoldenGate 26ai Microservices Replication Startup Failure

**Project:** Oracle Database Platform Automation
**Incident period:** November 14–17, 2026 (CST; timestamps approximate where derived from operator observations)
**Status:** Forward replication functionally restored using replacement groups; original defect and historical continuity not fully resolved
**Environment:** VirtualBox Oracle Linux lab. Recovery practices described below are intended to inform production runbooks, not evidence of production-grade lossless recovery.
**Software:** Oracle GoldenGate 26ai Microservices (release 23.26.1). "26ai" is the product name; `23.26.1` is the version reported by the binaries.
**Prepared:** November 17, 2026
**Related:** [November 7–8 recovery and validation incident report](2026-11-07-08-goldengate-recovery-and-validation.md) · [19c to 26ai recovery runbook](../../GoldenGate/runbooks/goldengate-19c-to-26ai-recovery-runbook.md)

Public edition: host names and addresses are replaced with placeholders (`source-host`, `target-host`, `<SOURCE_IP>`, `<TARGET_IP>`); raw evidence is retained separately.

---

## 1. Executive summary

Following a host interruption / recovery period, two previously working Oracle GoldenGate Microservices groups, Integrated Extract `EXT19C` and Integrated Replicat `REP26AI`, would not start in deployment `DEP1` on `target-host`. Administration Server accepted START requests but immediately logged `WARN | invalid checkpoint for group ()`, and no Extract/Replicat worker process was launched. The warning also appeared during successful starts of replacement groups, so it cannot alone establish checkpoint corruption.

The original groups and trail were preserved. New Integrated Extract `EXTTEST` and Replicat `REPTEST` established that new processes could start and that test-table DDL/DML replicated. A separate Integrated Replicat `REPCUT` was then introduced for four application tables with a new forward-only cutover checkpoint. All four mapped application tables passed INSERT, UPDATE and DELETE verification; `REPCUT` also passed a graceful stop/restart preserving checkpoint position. Final health output showed `EXTTEST`, `REPCUT` and `REPTEST` running, while the originals remained stopped.

**Primary limitation:** Old Extract and replacement Extract capture windows have an unreconciled SCN gap. Initial source/target row checks were not a transactionally consistent reconciliation. Therefore zero data loss, historical completeness and production-grade RPO are not established.

## 2. Topology and scope

| Role | Host / component | Notes |
|---|---|---|
| Oracle source | `source-host` (`<SOURCE_IP>`) | Oracle 19c, CDB `PRODB`, PDB `PRODBHR`, source schemas `FOX`, `HOLA` |
| GoldenGate hub and Oracle target | `target-host` (`<TARGET_IP>`) | Oracle Linux 9.8 VM; GoldenGate 26ai (23.26.1) Microservices binaries `/u02/ogg26ai_home`; deployment `/u02/ogg26ai_deploy` |
| GoldenGate Admin Client | `/u02/ogg26ai_home/bin/adminclient` | Administration Server `http://127.0.0.1:7821`, `DEP1`; Service Manager 7820 |
| Oracle target | CDB `CDB23AI`, PDB `PDB23AI` | Alias `TGT26AI`; Integrated Replicat apply |
| Original path | `EXT19C` → `./dirdat/lt` → `REP26AI` | Both preserved, stopped |
| Replacement path | `EXTTEST` → `./dirdat/xt` → `REPCUT` | Functional application CDC, validated for four tables |
| Parallel test consumer | `REPTEST` | Maps only `HOLA.GG_DDL_PROBE` for DDL/DML testing; not required for application CDC |

## 3. Incident symptoms and discovery

1. Originally working groups `EXT19C` and `REP26AI` stopped normally around November 14, 2026, 17:28 CST (per observed group history) and repeatedly failed to start subsequently.
2. On START, Admin Server logged `Starting extract 'EXT19C'` or `Starting replicat 'REP26AI'`, followed by `WARN | invalid checkpoint for group ()`. No child Extract/Replicat executable started.
3. The original `EXT19C` last observed source position was SCN `16833423`, trail `lt000000007` RBA `2467`. `REP26AI` had read the same trail sequence/RBA. This is an observed position, not proof that all upstream commits were consistently applied.
4. Original Replicat inbound server `OGG$REP26AI` appeared `DISABLED` when stopped, with no reported `DBA_APPLY.ERROR_NUMBER`. A controlled later stop/restart of `REPCUT` showed `DISABLED` while stopped and `ATTACHED` when running; thus `DISABLED` by itself is expected behavior, not an established root cause.
5. `EXT19C.cpe` (51,200 bytes) and `REP26AI.cpr` (24,576 bytes) existed and were readable. File checksums are not included in this document (see action register, Section 9).
6. REST PATCH start received HTTP 202, indicating acceptance of an asynchronous request rather than confirmed process launch. A later request-status lookup reported `OGG-12029` / non-existent request.
7. Controlled `strace` attached to `adminsrvr` during a failed start showed successful access to `.cpe` but no `fork`/`clone`/`execve` of the Extract worker. A lookup of a missing runtime `.pce` returned `ENOENT`; absence of runtime process files when a group is stopped is normal and is not proof of corruption.
8. One isolated VirtualBox guest Linux kernel soft-lockup/time jump was observed on the source. Its causal relationship to the startup problem was not established.

## 4. Root-cause assessment — evidence vs. inference

**Confirmed failure domain:** The original groups failed in Administration Server's prelaunch handling / group metadata or checkpoint processing path, before a worker process was started. The precise failing validation, data structure or defect remains unknown.

**Not demonstrated:**

- Physical checkpoint-file corruption. Files were present and accessible; the invalid checkpoint warning also occurred on successful replacement-group starts.
- Integrated capture/apply server corruption, or inbound `DISABLED`, as the primary reason for failed START.
- SQL Server, Oracle database schema or application DML as causal factors.
- VirtualBox interruption or OS clock anomalies as a proven direct cause.

**Root cause classification:** Undetermined / isolated to original-group prelaunch control path. Do not label this a proven checkpoint corruption incident without additional diagnostic evidence or vendor confirmation.

## 5. Resolution and recovery sequence

### 5.1 Preserve evidence; avoid destructive reset

- Preserved original `EXT19C`, `REP26AI`, original `lt` trail, checkpoint files and original parameter files.
- Incident artifacts were collected under `/home/oracle/ogg-incident-20261116`, and an offline VirtualBox snapshot was available.
- Did not reset original checkpoints or delete original groups.

### 5.2 Prove replacement capture/apply capability

- Created and started `EXTTEST` as an Integrated Extract on the 19c source, independent trail `./dirdat/xt`, maps `FOX.*` and `HOLA.*`, `DDL INCLUDE MAPPED`.
- Recorded new Extract first registered SCN `17014549`, filtering start SCN `17014924`; these values establish a potential historical gap relative to original `EXT19C` SCN `16833423`.
- Created `REPTEST`, an Integrated Replicat mapping only `PRODBHR.HOLA.GG_DDL_PROBE` to `HOLA.GG_DDL_PROBE`.
- Verified replication of test-table CREATE, INSERT and UPDATE.
- **Open:** DELETE was issued on the source, but target-side verification was not retained. Tracked in the action register (Section 9).

### 5.3 Validate current application baseline before forward cutover

Observed matching source and target application row counts/content for four tables, after a requested source-write freeze:

| Table | Observed rows on each side |
|---|---|
| `FOX.ILOAD` | 14 |
| `HOLA.CHILDREN_NAMES` | 5 |
| `HOLA.FOX` | 14 |
| `HOLA.TEST1` | 3 |
| **Total** | **36** |

This was an operator-level visual comparison, not a flashback-consistent, SCN-bound, checksum-based or transaction-complete reconciliation. It does not close the historical gap.

### 5.4 Establish application delivery with independent cutover checkpoint

Created `REPCUT` as an Integrated Replicat on the independent `xt` trail with `BEGIN NOW`, target alias `TGT26AI`, checkpoint table `GGADMIN.GGCHKPT`, mapping:

```
REPLICAT REPCUT
USERIDALIAS TGT26AI
DDL INCLUDE MAPPED
MAP PRODBHR.FOX.ILOAD, TARGET FOX.ILOAD;
MAP PRODBHR.HOLA.CHILDREN_NAMES, TARGET HOLA.CHILDREN_NAMES;
MAP PRODBHR.HOLA.FOX, TARGET HOLA.FOX;
MAP PRODBHR.HOLA.TEST1, TARGET HOLA.TEST1;
```

`BEGIN NOW` was a deliberate forward cutover, not a replay/reconciliation of the historical `lt` backlog. The existing duplicate-suppression behavior was not overridden with `NOFILTERDUPTRANSACTIONS`.

### 5.5 DML validation, checkpoint restart and last health observations

Source-driven DML tests confirmed on target PDB `PDB23AI`:

| Application mapping | INSERT | UPDATE | DELETE |
|---|---|---|---|
| `PRODBHR.HOLA.TEST1` → `HOLA.TEST1` | PASS (ID 930001) | PASS | PASS (count 0) |
| `PRODBHR.FOX.ILOAD` → `FOX.ILOAD` | PASS (ID 930002) | PASS (`STATUS=UPDATED`) | PASS (count 0) |
| `PRODBHR.HOLA.FOX` → `HOLA.FOX` | PASS (ID 930003) | PASS (`STATUS=UPDATED`) | PASS (count 0) |
| `PRODBHR.HOLA.CHILDREN_NAMES` → `HOLA.CHILDREN_NAMES` | PASS (CHILD_ID 930004) | PASS (`MIDDLE_NAME=CDC_UPDATED`) | PASS (count 0) |

`REPCUT` graceful shutdown returned `OGG-02965`, with status STOPPED / inbound DISABLED. Restart returned `OGG-15445` and status RUNNING / inbound ATTACHED with checkpoint `xt000000001` RBA `10102` preserved. This validates one orderly restart, not crash/failover recovery.

Final observation, November 17, 2026, approximately 13:06 CST:

| Group | Status | Last key checkpoint |
|---|---|---|
| `EXTTEST` | RUNNING | source SCN `17258723`, trail `xt` sequence 1 RBA `12981` |
| `REPCUT` | RUNNING; inbound ATTACHED | `xt000000001` RBA `12981`; checkpoint lag 0 |
| `REPTEST` | RUNNING; inbound ATTACHED | `xt000000001` RBA `12981`; checkpoint lag 0 |
| `EXT19C` | STOPPED, preserved | old `lt` path |
| `REP26AI` | STOPPED, preserved | old `lt` path |

The observed common trail RBA supports near-term reader progress; it does not prove end-to-end completeness or a persistent zero-lag SLA.

## 6. Why REPCUT instead of changing REPTEST?

It was possible to modify `REPTEST`'s MAP statements and restart it; a new process was not required by GoldenGate. `REPCUT` was chosen to separate experimental DDL testing from application recovery and to establish an independent application cutover/checkpoint. That adds operational clarity, but also an extra group to maintain. After completion, `REPTEST` can be gracefully stopped and retained for future lab tests; `EXTTEST` and `REPCUT` comprise the validated application path. Avoid making another migration solely to rename/consolidate groups.

## 7. Production-grade response that should replace the lab shortcut

### Containment and evidence

1. Declare an incident and identify last known good Extract and Replicat positions; record timestamps, SCNs, CSNs, trail sequence/RBA, lag, database apply state, process health, Admin Server and OS logs.
2. Quiesce/coordinate source writers if required by the recovery plan; document the exact outage window and affected tables.
3. Preserve original checkpoint files, parameter files, trails, report/error logs, Service Manager/Admin Server logs, database redo/archive retention and a system snapshot. Take supported backups. Avoid blanket checkpoint rewinds or deletes.
4. Determine whether the failure is in Microservices orchestration/prelaunch vs. database registration, runtime process, credential store, or integrated inbound/outbound server. A generic warning alone is insufficient.

### Data correctness and recovery decision

5. Define recovery objectives (RPO/RTO) and choose a supported recovery path with Oracle Support/vendor guidance where applicable.
6. Establish a transaction-consistent baseline (SCN/flashback or coordinated snapshot, depending on feature/support matrix), then reconcile every intervening source commit against preserved trails and target apply history. Check primary keys, schema changes, row counts and cryptographic checksums where appropriate; investigate differences.
7. If historical continuity cannot be reconstructed, formally declare and approve a new baseline/reinitialization using a supported initial load, with stakeholder sign-off on any accepted data loss. Do not treat `BEGIN NOW` plus matching counts as lossless recovery.
8. Validate before reopening application writes: deterministic INSERT/UPDATE/DELETE, DDL tests if in scope, replication-lag checks, collision/duplicate behavior, and controlled stop/restart plus failure-mode tests.

### Hardening and change control

9. Monitor Extract/Replicat status, checkpoint age, end-to-end latency, inbound server, apply errors, trail growth, archive log retention, disk and OS events; alert on stalled RBA even when the process is RUNNING.
10. Separate test and application mappings/roles; enforce least privilege, secure credential aliases, encrypted trails, backups, retention, documented service startup order and maintenance windows.
11. Record recovery change IDs, exact parameter diffs, rollback conditions, source/target baseline, cutover SCN, post-change evidence and explicit remaining risks.

## 8. Lessons learned

1. **RUNNING is not an end-to-end data-integrity assertion.** Verify target DML and advancing checkpoints.
2. **DISABLED inbound on a stopped Integrated Replicat is normal.** Correlate with group status.
3. **`WARN invalid checkpoint for group ()` is non-diagnostic by itself.** It also occurred on successful starts in this incident.
4. **HTTP 202 on REST START is not process success.** Confirm subsequent group status and the actual worker process.
5. **Runtime `.pce`/`.pcr` absence when stopped is expected.** Do not infer corruption from `ENOENT` alone.
6. **New groups can bypass an original-group prelaunch fault, but cannot by themselves heal a historical SCN gap.**
7. **Independent trails/checkpoints provide safer isolation** for lab cutover and experimentation, but require a documented beginning position and reconciliation in production.
8. **Separate original failure root cause from restoration outcome.** Functional service recovery is established; forensic root cause and lossless historical continuity are not.
9. **Validate all mapped tables and all DML classes.** Four-table INSERT/UPDATE/DELETE and a controlled restart were recorded.
10. **Preserve evidence before change, and automate data/health assertions** rather than relying on status output or visual row comparisons.

## 9. Outstanding risks and action register

| Priority | Action | Acceptance criteria |
|---|---|---|
| Critical before production designation | Reconcile the original-to-new SCN interval (`16833423` → `17014924`) or perform an approved transaction-consistent reinitialization | Auditable continuity proof or formal accepted-loss exception |
| Critical (time-sensitive) | Confirm source archived logs covering SCN `16833423` → `17014924` still exist and protect them from RMAN deletion; then mine that range with LogMiner, filtered to schemas `FOX` and `HOLA` and the four mapped tables | Saved LogMiner output showing either no DML on mapped tables in the interval (gap closed with evidence) or the exact changes to reconcile |
| High | Check whether `EXT19C` is still registered with the source database (`DBA_CAPTURE`, `REQUIRED_CHECKPOINT_SCN`) and whether that registration is holding archived logs | Documented decision: keep registration until reconciliation is complete with FRA monitoring, or unregister `EXT19C` afterward |
| High | Archive original artifacts (`EXT19C`, `REP26AI`, `lt`, logs, checkpoints, parameters) | Immutable/verified evidence package and retention decision |
| High | Implement GoldenGate health, lag/stall and data-consistency monitoring | Automated alert on stopped/abended/stalled processes and apply errors |
| Medium | Add SHA-256 checksums of `EXT19C.cpe` and `REP26AI.cpr` from the incident artifact directory, if retained | Checksums recorded in this document, or a note that they were not retained |
| Medium | Re-run `REPTEST` DELETE on `HOLA.GG_DDL_PROBE` and record target-side result | Target row count 0 captured as evidence |
| Medium | Produce a supported cold/crash restart and failure-mode drill | Documented RTO/RPO measurement and recovery proof |
| Medium | Gracefully stop `REPTEST` if no further DDL lab testing is required | `EXTTEST`/`REPCUT` continue uninterrupted |
| Medium | Record exact versions and source-to-target capability matrix before SQL Server CDC phase | SQL Server 2022 target compatibility, network, credentials, mapping, datatype assessment |
| Low | Investigate isolated VirtualBox soft-lockup separately | OS/VM incident evidence and reproducibility, or closure as unproven |

## 10. Final disposition

- **Service restoration:** PASS for forward Oracle 19c → Oracle 26ai CDC on four named application tables; test DDL path separately validated.
- **Graceful restart:** PASS for replacement `REPCUT`.
- **Original failure root cause:** UNDETERMINED; prelaunch problem isolated but not conclusively explained.
- **Historical transaction reconciliation:** OPEN.
- **Production-ready lossless recovery certification:** NOT ESTABLISHED.
- **Next project workstream:** SQL Server 2022 target readiness and a supported GoldenGate-to-SQL Server delivery architecture, without changing the validated Oracle-to-Oracle pipeline.

**Evidence basis:** GoldenGate Admin Client `INFO ALL`, `INFO EXTRACT/REPLICAT DETAIL`, STOP/START messages, controlled `strace` findings, source and target SQL validation, and incident observations recorded during the November 2026 troubleshooting. This postmortem does not substitute for archived raw logs, time-synchronized trace files or vendor root-cause confirmation.

## Document history

| Date | Change |
|---|---|
| 2026-11-17 | Initial postmortem |
| 2026-11-17 | Review edits: clarified GoldenGate 26ai / 23.26.1 naming; moved checkpoint checksums and `REPTEST` DELETE verification to the action register; added archived-log/LogMiner gap check and `EXT19C` registration/archive-retention risk |
| 2026-11-17 | Moved to `incident-reports/` alongside the November 7–8 report; replaced host names and IP addresses with placeholders |
