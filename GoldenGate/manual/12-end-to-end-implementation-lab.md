# 12 — End-to-End Implementation Lab

**Scope:** End-to-end GoldenGate 26ai Oracle-to-Oracle implementation plan. Configuration examples are illustrative; deployment, recovery and DML results will be recorded when the lab is executed.

## Scope and acceptance criteria

This implementation plan covers secure Microservices deployment, Oracle database preparation, Integrated Extract and Replicat, trail delivery, consistent initial load, committed DML validation, controlled failure recovery and reproducible evidence.

**Pass only with evidence:** correct version/platform support, repeatable deployment, successful initial baseline, successful target DML checks at *each* stage, stable restart/recovery checkpoints, and no unexplained differences. `RUNNING` status is necessary but insufficient.

## 1. Lab architecture and scope

```text
Oracle source database / PDBSRC (example)
           | Oracle redo / integrated capture
        [EXTLAB]  Integrated Extract
           | local source trail ea
  [Distribution Service: src_to_tgt]
           | authenticated WSS transport
  [Receiver Service on target]
           | local target trail eb
       [REPLAB]  Integrated Replicat
           | Oracle inbound server
Oracle target database / PDBTGT (example)
```

This represents two **separate GoldenGate deployments** in a disposable lab. The source and target database releases must each be certified with the selected GoldenGate build. The example database names, users, addresses, process names, trail prefixes, paths and credentials are fictional.

**Related work:** My completed Oracle 19c → 26ai migration used remote integrated capture (EXT19C) and Integrated Replicat (REP26AI). My OCI Oracle → Azure SQL Server project is documented separately in the enterprise-multicloud-database-platform-lab repository.

## 2. Preflight worksheet (before changes)

| Item | Required record |
|---|---|
| Source and target | Oracle release, patch, database role, DB_UNIQUE_NAME, CDB/PDB, service name |
| GoldenGate | Software release/build, architecture, compatibility/licensing evidence |
| Hosts | Linux release/kernel, user/group, software/deployment homes, disk/memory |
| Network | DNS, route, TLS CA/SANs, permitted ports, target Receiver endpoint |
| Capture | Approved schema/table, PK/UK, supplemental logging and archive retention |
| Apply | Target schema and privileges, object parity, checkpoint table, inbound server support |
| Instantiation | Data Pump / supported alternative, source snapshot metadata, CDC boundary |
| Operations | Recovery objectives, trail retention, rollback, monitoring and evidence directory |

### Read-only Linux inspection

```bash
hostnamectl
cat /etc/os-release
uname -r
id
df -hT
free -h
ip -br addr
ss -lnt
```

### Read-only Oracle SQL inspection

```sql
SHOW CON_NAME;
SHOW USER;
SELECT name, db_unique_name, database_role, open_mode, log_mode,
       force_logging, supplemental_log_data_min, current_scn
FROM v$database;
SHOW PARAMETER enable_goldengate_replication;
```

Run in an approved container with sufficient rights. Preserve *real* output as redacted evidence, not invented rows.

## 3. Lab build sequence and hold points

### Gate A — Install and deploy GoldenGate

Using [02](02-installation-and-microservices-deployment.md), install the certified software and configure Service Manager, a source deployment and a target deployment with OGGCA. Use independently secured administrative access, valid TLS, isolated runtime paths and approved startup modes.

**Examples only** (the software package/response files must be present and verified):

```bash
cd "$OGG_HOME/bin"
./oggca.sh
# Silent mode after a tested, sanitized response file is generated:
# ./oggca.sh -silent -responseFile /secure/path/deployment.rsp
```

**Gate A pass:** installed build identified, services healthy, intended deployment names/ports verified, security confirmed, OS logs archived, and a controlled restart procedure documented. No assumption that GoldenGate replication is already configured.

### Gate B — Prepare the databases

Use [03](03-oracle-database-preparation.md). Verify source redo/archive strategy, least-privilege capture account, table keys and supplemental logging. Configure a separate target apply account and compatible schema/table definitions. GoldenGate 26ai software may connect to **Oracle 19c or 26ai databases** subject to certification; their database privilege procedures differ. Do not assume blanket DBA grants or reuse one release's privilege script.

Illustrative source-admin command choices after approved database login:

```text
DBLOGIN USERIDALIAS gg_source
ADD TRANDATA PDBSRC.APP_SRC.GG_LAB
INFO TRANDATA PDBSRC.APP_SRC.GG_LAB
```

Names are placeholders, syntax must match the actual multitenant configuration. A source table with a stable primary key is required for this lab's validation.

**Gate B pass:** database/PDB connection and role checked, archive/redo retention approved, table metadata correct, necessary source supplemental logging and privileges validated. Save SQL results and no secret passwords.

### Gate C — Initial data and precise instantiation strategy

**This is the primary correctness gate.** Use [07](07-initial-load-scn-csn-and-cutover.md). Decide *before starting apply* whether the lab baseline is an intentionally empty, quiesced target or a nonempty source table needing a consistent copy.

For a nonempty Oracle source, use an Oracle-supported instantiation procedure such as Data Pump automatic per-table CSN instantiation: establish capture first, set PREPARECSN as documented, export/import the consistent source baseline, verify target instantiation metadata and only then choose Replicat filtering/starting position. Do not use a random `CURRENT_SCN` as the baseline boundary or start Replicat at NOW to bypass backlog.

Oracle references: [Precise instantiation](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/instantiate-precise-instantiation-oracle.html) and [Data Pump automatic per-table instantiation](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/using-data-pump-automatic-table-instantiation-oracle-ma.html).

**Gate C pass:** either both empty baseline tables are provably equal before CDC or a certified instantiation procedure yields consistent target rows with documented source/table CSN metadata. Never proceed with known divergence.

### Gate D — Integrated Extract and source trail

Use [04](04-integrated-extract-and-source-trails.md) and Oracle's exact instructions to register integrated capture before creating its Extract. Confirm the approved start boundary.

**Illustrative Admin Client structure, not ready-to-run production commands:**

```text
DBLOGIN USERIDALIAS gg_source
REGISTER EXTRACT EXTLAB DATABASE
ADD EXTRACT EXTLAB, INTEGRATED TRANLOG, BEGIN NOW
ADD EXTTRAIL ea, EXTRACT EXTLAB, MEGABYTES 200
```

`BEGIN NOW` is appropriate only for an expressly approved starting design, for example a controlled empty-table exercise with a pre-established capture boundary. It is not a safe default for nonempty migration. Preserve actual Extract parameter file, source trail binding, report and registration details.

**Gate D pass:** registered capture, healthy Extract, required TABLE mapping, trail sequence generated from a committed test DML, correct checkpoint and recoverable redo.

### Gate E — Transport to target

Use [05](05-distribution-and-receiver-services.md) to add a source Distribution Service Path to the secured target Receiver Service. Confirm source trail `ea`, destination trail `eb`, TLS/certificate trust, path checkpoint and physical target trail creation. A target-initiated Receiver Path is an alternative when topology requires it.

**Gate E pass:** test record leaves source trail, path reports movement, target trail sequence advances and the Receiver reports no unresolved errors. Transport alone does *not* prove apply.

### Gate F — Integrated Replicat and checkpoint table

Use [06](06-integrated-replicat-and-validation.md). Confirm target DB alias, target table, valid instantiation boundary, Replicat type and checkpoint table. Oracle's Microservices Replicat procedure identifies DB Connections, supplemental logging, checkpoint table and heartbeat as setup prerequisites.

**Illustrative Admin Client structure:**

```text
DBLOGIN USERIDALIAS gg_target
ADD CHECKPOINTTABLE APP_TGT.GG_CHECKPOINT
ADD REPLICAT REPLAB, INTEGRATED, EXTTRAIL eb,
  CHECKPOINTTABLE APP_TGT.GG_CHECKPOINT
```

Use source/target mappings in the Replicat parameter file, a securely stored target USERIDALIAS, and the *actual* target trail prefix. Align Replicat initial position with Gate C; do not uncritically apply BEGIN NOW or AFTERCSN.

**Gate F pass:** Replicat started without unresolved apply errors, its trail checkpoint advances, inbound apply is healthy, and changes can be validated at the target.

## 4. Controlled DML validation lab

The following SQL is **change-producing**. Use only isolated lab tables, not production data. Create compatible source/target tables and ensure Extract/Replicat mapping, table keys and initial baseline are configured first.

```sql
-- In SOURCE application schema only (after approval):
CREATE TABLE gg_lab (
  test_id NUMBER PRIMARY KEY,
  payload VARCHAR2(80),
  version_no NUMBER
);
```

Record the target table-creation/instantiation method and verify schema parity. Then carry out each phase separately:

```sql
-- Test A: INSERT; COMMIT, then verify TARGET contains 1 row.
INSERT INTO gg_lab VALUES (101, 'INSERT_OK', 1);
COMMIT;

-- Test B: UPDATE; COMMIT, then verify TARGET reflects version 2.
UPDATE gg_lab SET payload='UPDATE_OK', version_no=2
WHERE test_id=101;
COMMIT;

-- Test C: DELETE; COMMIT, then verify TARGET row is absent.
DELETE FROM gg_lab WHERE test_id=101;
COMMIT;
```

Read after *each* step at both ends, waiting for catch-up:

```sql
SELECT test_id, payload, version_no
FROM gg_lab
WHERE test_id=101;
```

| Stage | Expected SOURCE | Expected TARGET after catch-up | Evidence |
|---|---|---|---|
| INSERT | `101, INSERT_OK, 1` | Same single row | Source commit + target query + checkpoints |
| UPDATE | `101, UPDATE_OK, 2` | Same updated row | Source commit + target query + checkpoints |
| DELETE | No row for 101 | No row for 101 | Source commit + target query + checkpoints |

**Do not claim a pass from the final deleted row alone.** The target might never have received the INSERT. Inspect the intermediate states and process reports. This table is an *expected result*, not observed lab output.

## 5. Troubleshooting and recovery assessment

Run these scenarios only in a disposable lab under an explicit recovery plan. Do not intentionally damage a production trail or change production checkpoint positions.

| Simulated problem | Safe diagnostic path | Pass evidence |
|---|---|---|
| Extract stopped | `INFO EXTRACT`, report, DB capture state, redo and trail | Resume from preserved capture position, no missed DML |
| Distribution Path paused | `INFO DISTPATH`, path checkpoints, network/TLS, source/target sequences | Restart catches up and target trail is continuous |
| Replicat stopped | `INFO REPLICAT`, `SHOWCH`, report, target locks/constraints | Controlled restart, target DML reaches expected state |
| Source/target mapping error | Compare TABLE/MAP/COLMAP, target schema and Replicat error | Correct mapping after backup/approval and reconciliation |
| Unexpected collision | Verify target baseline and instantiation CSN | Root cause explained; do not permanently enable HANDLECOLLISIONS |
| Disk/retention warning | Capacity, oldest needed trail/redo and consumer checkpoint | Safe retention plan; no deletion of needed files |

Read-only diagnostic examples:

```text
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
```

Consult [08](08-monitoring-lag-checkpoints-and-recovery.md) before any restart, trail purge, checkpoint reposition or recovery. Record all errors before attempting corrections.

## 6. Operational acceptance checklist

### Design and operational checks

1. Draw the end-to-end MSA pipeline and explain each component (8).
2. Explain why ARCHIVELOG and supplemental logging are different and what key columns achieve (6).
3. Explain source registration, local and remote trail, Replicat and checkpoint table roles (6).
4. Compare ATCSN vs AFTERCSN and explain why a random CURRENT_SCN is unsafe for instantiation (8).
5. Contrast process running, checkpoint advancing and verified target rows (6).
6. Explain one secure authentication model and why credential wallets cannot be transplanted (6).

### Implementation validation gates

| Competency | Points |
|---|---:|
| Preflight inventory, topology and security | 10 |
| Installation/deployment and database readiness | 10 |
| Correct capture, trail and transport setup | 10 |
| Valid initial-load/instantiation and Replicat checkpoint | 10 |
| Three separately proven DML tests and reconciliation | 15 |
| One safely recovered failure with documented checkpoints | 5 |

**Operational acceptance:** all mandatory safety controls must pass: no credential disclosure, no unexplained replication gap, a verified initial baseline and successful INSERT/UPDATE/DELETE validation with retained evidence.


## 8. Final project deliverables

Store sanitized topology diagrams, release and compatibility records, parameter files, SQL, process reports, checkpoints, logged operations, DML reconciliation and recovery evidence. Keep third-party proprietary materials in access-controlled storage and retain Oracle references for authoritative syntax.

**Do not publish:** passwords, wallets, TLS private keys, unaudited installation response files, client database data, internal production addresses, copyrighted third-party course materials or sensitive logs.

## 9. Evidence requirements and references

- **Reference procedures:** Architecture, configuration and recovery instructions are supported by the linked Oracle documentation.
- **Vendor-reference:** official Oracle 26ai Extract/Replicat/path/instantiation workflows.

### Oracle documentation

- [Oracle 26ai — Add an Extract](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/extract-add-primary-extract.html)
- [Oracle 26ai — Add a Distribution Path](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/distribute-add-distribution-path.html)
- [Oracle 26ai — Add a Replicat](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/replicat-add-replicat_procedure.html)
- [Oracle 26ai — Precise Instantiation](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/instantiate-precise-instantiation-oracle.html)
- [Oracle 26ai — Data Pump per-table instantiation](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/using-data-pump-automatic-table-instantiation-oracle-ma.html)
- [Oracle 26ai — Replication components and checkpoints](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/overview-components-data-replication-oracle-goldengate.html)

**Follow-up work:** Consolidate a command reference, review release-specific syntax across topics, and attach execution evidence from the end-to-end lab.