# 07 — Initial Load, SCN/CSN and Cutover

> **Reference scope:** Oracle-documented procedures and illustrative examples. Lab results are recorded separately.

## Scope and migration criteria

This page covers existing-data instantiation, continuous CDC, SCN/CSN boundaries, Data Pump and file-based initial load, Replicat positioning, consistency checks, migration cutover and rollback.

## 1. Initial load and CDC solve different problems

Extract can capture new source transactions, but it does not automatically copy all rows that existed before capture. An initial-load procedure populates a **consistent target baseline**. The CDC stream then applies changes not already represented in that baseline. If baseline and streaming positions are misaligned, missing rows and duplicate-key collisions can result.

```text
Time ------------------------------------------------------>
Source rows:   existing baseline   | new committed changes --->
Capture:    registration -- CDC trail retains needed changes --->
Snapshot:                  [consistent point B] ---> initial copy
Target:                                 baseline + required CDC --->
Cutover:                                                 quiesce/switch
```

**Core invariant:** the target baseline and the Replicat instantiation/starting position must refer to a defensible consistency boundary. Capture registration and snapshot time need not be identical. Oracle's precise instantiation guide states that the instantiation SCN must be after the registration SCN.

## 2. SCN, CSN and checkpoints

- **Oracle SCN:** database sequencing/consistency identifier used with redo and snapshots.
- **GoldenGate CSN:** source commit-position identifier used in change streams; for Oracle, tied to Oracle commit ordering.
- **Instantiation CSN:** boundary through which the target object contents are considered loaded; it can be **per table**.
- **Capture registration SCN:** database position relevant to integrated capture registration.
- **Replicat checkpoint:** durable apply progress; not proof of correct snapshot alignment.

Read-only inspection of the source database:

```sql
SHOW CON_NAME;
SELECT name, db_unique_name, database_role, open_mode, current_scn
FROM v$database;
```

**Correction:** an arbitrary CURRENT_SCN query does not establish the SCN at which Data Pump or another method made a consistent copy. Nor does it prove a safe Replicat start position. Long-running transactions and per-object snapshot points matter.

## 3. Pick the instantiation method

| Method | Typical use | What must be proven |
|---|---|---|
| Oracle Data Pump with automatic per-table instantiation | Oracle-to-Oracle logical object baseline | PREPARECSN, dump/import metadata, per-table instantiation filtering |
| GoldenGate file-based initial load | Smaller table sets, selected schemas, some heterogeneous tasks | Snapshot point, initial-load Extract/Replicat and CDC continuity |
| RMAN physical instantiation | Large Oracle databases when physical compatibility allows | Restore/recovery compatibility and exact target consistency |
| Application copy/ETL | Customized transformations | Stable snapshot and CDC mapping by object |

Oracle 26ai documents logical and physical methods separately. Validate certification and environment-specific limitations; none is universally best.

## 4. Method A — Data Pump with automatic per-table CSN instantiation

### Phase A: prepare the Oracle source

1. Verify certified DB/GoldenGate combination, redo/logging and source privileges (03–04).
2. Establish continuous Extract capture early enough to retain transaction changes during the export.
3. Prepare source table/schema instantiation information before exporting, as documented by Oracle:

```text
DBLOGIN USERIDALIAS gg_source
ADD SCHEMATRANDATA PDBSRC.APP_SRC PREPARECSN
INFO SCHEMATRANDATA PDBSRC.APP_SRC
```

These names are placeholders. Verify the actual multitenant command form, Admin Client release and privileges.

### Phase B: consistent export/import

Use supported Oracle Data Pump export/import settings to generate an appropriately consistent baseline and carry instantiation metadata. Save source PDB, snapshot method, dump metadata, export/import logs, object scope, target remaps and target schema checks. Use actual export/import logs and parameter records to support completed-lab claims.

### Phase C: Replicat filtering

Oracle's automatic per-table method uses the following Replicat parameter after the source PREPARECSN and target import have established per-table metadata:

```text
DBOPTIONS ENABLE_INSTANTIATION_FILTERING
```

This filters changes already included in the imported baseline on a per-table basis. It is **not** a magic safety switch; missing or incorrect metadata can create gaps or duplicate apply. Verify the exact target SCNs and Replicat start before activation.

Official reference: https://docs.oracle.com/en/database/goldengate/core/26/coredoc/using-data-pump-automatic-table-instantiation-oracle-ma.html

### Manual setting alternative — high risk if misused

Oracle provides SET INSTANTIATION CSN for a table when automatic metadata was not supplied:

```text
DBLOGIN USERIDALIAS gg_target
SET INSTANTIATION CSN 12345678 FOR app_tgt.orders FROM source.example
```

**Illustrative only.** The number and source global database name are invented placeholders. An incorrect value can silently omit required transactions. Do not set it by guessing from a convenient CURRENT_SCN sample.

Official reference: https://docs.oracle.com/en/database/goldengate/core/26/gclir/set-instantiation-csn.html

## 5. Method B — file-based GoldenGate initial load

A file-based Initial Load Extract can use RMTHOST/RMTFILE and TABLE statements with corresponding Replicat MAP clauses. Validate these examples against the target release and confirm completion using actual load evidence.

```text
EXTRACT LOAD1
USERIDALIAS ggadmin_cdb DOMAIN OracleGoldenGate
RMTHOST target.example.invalid, PORT 7833
RMTFILE /approved/target/path/loadfile
TABLE PDB1.APP_SRC.DEPARTMENTS;
TABLE PDB1.APP_SRC.EMPLOYEES;
```

**Caution:** sample paths, port, remote-file method and credentials require release-specific verification. Microservices initial-load topologies differ: Oracle also documents an initial-load trail transported through Distribution Paths. The supported topology determines the method.

**Procedure logic, not a ready-to-run script:**

1. Register and prepare the primary Extract and record capture registration/position.
2. Determine a precise instantiation SCN later than registration and account for long-running transactions.
3. Create a consistent initial-load Extract/source snapshot tied to that position.
4. Transfer the initial-load data through the configured supported file/trail mechanism.
5. Apply the initial load and verify target object state.
6. Position the ongoing CDC Replicat so it applies only changes that the baseline does not contain.
7. Reconcile counts and row values, then prove continuing DML through the pipeline.

Oracle documentation warns Microservices Architecture does not support direct-load initial load. Use its supported file-based workflow.

Official reference: https://docs.oracle.com/en/database/goldengate/core/26/coredoc/instantiate-add-initial-load-extract-using-admin-client.html

## 6. ATCSN versus AFTERCSN

Oracle documents these START REPLICAT choices:

```text
START REPLICAT repname ATCSN <approved_csn>
START REPLICAT repname AFTERCSN <approved_csn>
```

- **ATCSN:** process the transaction **at** the specified commit sequence and later; skip lower CSNs.
- **AFTERCSN:** skip the specified commit and all earlier CSNs; start with later transactions.

One wrong boundary can lose or double-apply transactions. A single CSN may be wrong when table snapshots were taken at different times. Check trail-format support and the exact load/positioning procedure before using either command.

Official reference: https://docs.oracle.com/en/database/goldengate/core/26/gclir/start-replicat.html

## 7. Migration cutover runbook — staged decision gates

**Preparation:** define approved scope, downtime objective, data-integrity criteria, capture/transport/apply monitoring, application service changes, fallback owner and evidence signoff. Test source/target object compatibility, sequences, triggers, constraints, permissions and job state.

**Before freeze:** ensure baseline has loaded; Extract and Replicat are healthy; records are being applied; measured lag and target row reconciliation satisfy the gate; verify enough redo/trail retention to ride out a delay.

**Write-freeze window:**

1. Quiesce application writes using an approved mechanism and record last accepted source transaction.
2. Verify Extract has read all required source commits, paths delivered trails, and Replicat has applied through the agreed endpoint.
3. Reconcile source/target data and critical business invariants at a consistent boundary.
4. Check application credentials, connection strings, sequences, jobs and integration endpoints for target readiness.
5. Record a formal go/no-go; only then switch client write traffic.
6. Test first target transaction and application workflow, monitor errors and throughput.

**Rollback caution:** after target accepts new writes, returning to old source is *not* safe by default. The rollback plan must preserve or reverse-synchronize target-only transactions or specify the latest point at which rollback without reverse capture is permitted. Avoid split-brain writes.

**Measure actual downtime** (write-freeze to successful production write on target). Do not claim zero downtime solely because GoldenGate was used.

## 8. Failure analysis

| Symptom | Investigate | Avoid |
|---|---|---|
| Duplicate keys after initial load | Baseline overlap, per-table instantiation CSNs, Replicat position | Permanent HANDLECOLLISIONS |
| Missing rows on UPDATE/DELETE | Initial-load completeness, source keys/logging, filtering and MAP | Skipping failed operations |
| Import succeeded but Replicat diverges | PREPARECSN, imported metadata, long transactions, checkpoint | Assuming Data Pump completion proves correctness |
| Catch-up exceeds outage window | Source write rate, apply throughput, trail backlog, target locks | Proceeding without go/no-go |
| Trails or redo missing | Retention policy, source checkpoint and backup recoverability | Blind reposition to NOW |
| Rollback after target writes | Target-only commits, reverse synchronization, split-brain risk | Flipping connection strings without data plan |

## 9. Operational review scenario

Three source tables have snapshot boundaries at hypothetical SCNs 900, 950 and 1000, while Extract started earlier.

**Question A:** Why might AFTERCSN 1000 for all tables lose records? **Answer:** older table snapshots require intervening commits between their baseline SCNs and 1000.

**Question B:** Why might ATCSN 900 for all tables replay changes? **Answer:** later table snapshots may already contain commits after 900.

**Question C:** What does automatic per-table instantiation solve? **Answer:** it records/filters by each table's correct source baseline, if correctly configured and imported.

**Question D:** What proves go-live readiness? **Answer:** approved source write freeze, complete capture/delivery/apply, target reconciliation, application smoke tests, and reversible cutover decision with recorded evidence.

## 10. Real-lab evidence worksheet


## Oracle references and validation requirements

**Implementation requirement:** File-based initial load and SCN-based cutover require a documented consistent snapshot, supported trail topology, position/instantiation metadata and source-target reconciliation.

**Oracle 26ai guidance:**

- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/instantiate-instantiating.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/instantiate-precise-instantiation-oracle.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/using-data-pump-automatic-table-instantiation-oracle-ma.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/instantiate-add-initial-load-extract-using-admin-client.html
- https://docs.oracle.com/en/database/goldengate/core/26/gclir/set-instantiation-csn.html
- https://docs.oracle.com/en/database/goldengate/core/26/gclir/start-replicat.html

**Next:** [08 — Monitoring, Checkpoints and Recovery](08-monitoring-lag-checkpoints-and-recovery.md)
