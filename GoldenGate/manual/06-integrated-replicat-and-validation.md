# 06 — Integrated Replicat and Validation

> **Reference scope:** Vendor documentation and illustrative configurations. Executed changes require separately retained logs and validation evidence.
>

## Scope and operational checks

Understand where apply happens; select a compatible Replicat type; verify the target database and checkpoint table; add an Integrated Replicat with a correctly aligned trail; explain its parameters and checkpoint behavior; test committed INSERT/UPDATE/DELETE and reconciliation; diagnose apply errors without losing transactions.

## 1. Position in the replication pipeline

~~~text
Source Oracle redo -> Integrated Extract -> source trail
       -> Distribution Service -> Receiver Service -> target trail
       -> INTEGRATED REPLICAT -> Oracle database inbound server
       -> target Oracle tables
~~~

Integrated Replicat reads the GoldenGate trail, filters/maps/transforms records as configured, constructs logical change records (LCRs) and sends them to the Oracle target database inbound server for apply. This differs from non-integrated (classic) Replicat, which performs target SQL execution through its own apply model. Integrated and parallel integrated apply modes have different behavior and support requirements.

Oracle 26ai documents that integrated Replicat should be used for online Oracle change synchronization that reads a local EXTTRAIL. **Do not use integrated Replicat for GoldenGate initial-load BULKLOAD:** initial loading and ongoing change synchronization are separate workflows.

**Oracle:** [ADD REPLICAT command reference](https://docs.oracle.com/en/database/goldengate/core/26/gclir/add-replicat.html).

## 2. Verify the target BEFORE creating Replicat (read-only)

~~~sql
SHOW CON_NAME;
SHOW USER;

SELECT name, db_unique_name, database_role, open_mode, log_mode
FROM v$database;

SELECT con_id, name, open_mode
FROM v$pdbs
ORDER BY con_id;

-- Run in the intended target PDB with suitable dictionary privileges.
SELECT owner, table_name
FROM dba_tables
WHERE owner = 'APP_TGT'
ORDER BY table_name;

SELECT owner, table_name, constraint_name, constraint_type, status
FROM dba_constraints
WHERE owner = 'APP_TGT'
  AND constraint_type IN ('P','U')
ORDER BY table_name, constraint_type;
~~~

**Why:** The Replicat credential must reach the correct target service/PDB; the destination schema and tables must exist with compatible structure and usable keys. The target role/open mode must allow the intended apply. A valid network login is not sufficient evidence that all MAP rules can apply successfully.

Write down: target service, PDB, Replicat account, intended object map, target character set, relevant constraints/triggers, target trail prefix, disk capacity, required checkpoint table and initial-load instantiation point.

## 3. Checkpoint table: what it protects

A Replicat checkpoint records durable progress so it can restart at the correct position after failures. Oracle 26ai strongly recommends checkpoint tables and its Microservices configuration instructions require creating one before adding relevant Replicat types; certain parallel and coordinated configurations require it.

**Create only after confirming the connected TARGET database**, its privileges and approved owner. In Administration Service, select the target DB Connection, open the Checkpoint Table section, and add a qualified table such as APP_TGT.GG_CHECKPOINT (name here is illustrative). For a command-line workflow, Oracle documents an ADD CHECKPOINTTABLE command.

~~~text
-- Change-controlled Admin Client illustration after target DBLOGIN:
DBLOGIN USERIDALIAS gg_target
ADD CHECKPOINTTABLE APP_TGT.GG_CHECKPOINT
~~~

Do not treat the checkpoint table as an application table or replicate its rows without a supported reason. Never drop, truncate or edit checkpoint contents as an ad hoc recovery method.

**Oracle:** [Before Adding Extract and Replicat Processes](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/configure-ogg-adding-extract-and-replicat.html).

## 4. Target trail identification and initial position

05 configured delivery into a target trail. Record the **actual destination trail** and its checkpoint/sequence. The prefix in the Replicat ADD command must match the delivered target trail, not automatically the source Extract's prefix. Example: source ea -> target eb; Replicat reads eb.

A preexisting target data set requires a consistent instantiation boundary. The default BEGIN NOW is **not** a substitute for a documented initial-load method and may skip required transactions. Establish source snapshot, capture start, instantiated target state and Replicat initial checkpoint together; record specific CSN/SCN or sequence/RBA decisions with DBA review.

## 5. Create an Integrated Replicat

### Microservices graphical method

1. Authenticate to the **target** deployment's Administration Service.
2. Confirm the target database connection/alias and checkpoint table exist.
3. In Replicats, select **Add Replicat** and **Integrated Replicat** (verify supported types for exact database and 26ai build).
4. Choose a process name, e.g. REPLAB; enter the target trail prefix, e.g. eb, and a previously created checkpoint table.
5. Explicitly choose the approved begin position and credential alias.
6. Supply/validate a parameter file and decide whether to create without starting, allowing review first.
7. Once approved, start the process and inspect status, reports, checkpoints and target data.

### Admin Client configuration example (change-controlled)

~~~text
DBLOGIN USERIDALIAS gg_target
ADD CHECKPOINTTABLE APP_TGT.GG_CHECKPOINT
ADD REPLICAT REPLAB, INTEGRATED, EXTTRAIL eb, CHECKPOINTTABLE APP_TGT.GG_CHECKPOINT
~~~

**Assumptions:** APP_TGT is an authorized target owner, the checkpoint table does not already exist, the Admin Client is connected to the correct deployment, eb is an existing locally delivered trail prefix, the target PDB service is correct, source/target data are already instantiated consistently, and the chosen initial position is appropriate. This block is intentionally **not presented as a fully unattended production script**.

Oracle's 26ai command reference documents the ADD REPLICAT structure with INTEGRATED, EXTTRAIL and CHECKPOINTTABLE. It documents that Replicat registration in the target database occurs automatically under normal startup conditions; unlike Integrated Extract, **do not assume a separate REGISTER REPLICAT step is universally required**.

**Oracle:** [ADD REPLICAT](https://docs.oracle.com/en/database/goldengate/core/26/gclir/add-replicat.html); [Add a Replicat](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/replicat-add-replicat_procedure.html).

## 6. Explain each parameter line

Example: these names and schemas are placeholders and must be adapted to actual PDB scope and container-qualified source naming.

~~~text
REPLICAT REPLAB
USERIDALIAS gg_target DOMAIN OracleGoldenGate
MAP PDBSRC.APP_SRC.ORDERS, TARGET PDBTGT.APP_TGT.ORDERS;
~~~

| Line | Function | Pitfall |
|---|---|---|
| REPLICAT REPLAB | Associates the configuration with this process | Name must match created group |
| USERIDALIAS gg_target | Uses protected target DB connection | Wrong PDB, expired credential, incorrect domain |
| MAP source, TARGET target | Specifies object-to-object apply | Incorrect catalog/schema/column names or unsupported mapping |
| Semicolon | Terminates mapping directive | Missing delimiter can invalidate file |

For cross-database mappings, **SOURCECATALOG** is another supported approach; whether catalog-qualified three-part names are applicable depends on the exact Oracle multitenant/deployment configuration. Do not mix conflicting conventions without testing.

Do not add global DDL INCLUDE MAPPED, DDLERROR, REPERROR DISCARD, HANDLECOLLISIONS or filters by default. They materially affect what is replicated or silently ignored and must be deliberate, tested options.

## 7. Start, monitor and distinguish types of evidence

Administration Service provides process controls and statistics. Example Admin Client inspection:

~~~text
INFO ALL
INFO REPLICAT REPLAB
STATS REPLICAT REPLAB
~~~

Start only after the parameter file, checkpoint, initial position and trail alignment are approved:

~~~text
START REPLICAT REPLAB
~~~

Use the report, trail checkpoint progression, errors and database apply evidence to understand activity. A running state is **not equal to target correctness**; stats can reflect attempted/filtered operations or be affected by restarts.

A useful target-side read-only check for integrated apply, with dictionary privileges, is:

~~~sql
SELECT apply_name, status
FROM dba_apply
ORDER BY apply_name;
~~~

The displayed inbound-server names need not exactly equal the Replicat name. An apply entry alone does not prove correct data.

## 8. End-to-end test: INSERT, UPDATE and DELETE

### Test design

Use a **new, dedicated lab table** with a primary key, deterministic values and a recorded start state. Avoid touching production application tables or using a DELETE example on business data.

Example intended source table:

~~~sql
-- LAB SCHEMA ONLY; review ownership and privileges before creation.
CREATE TABLE app_src.gg_lab_validation (
    test_id NUMBER PRIMARY KEY,
    payload VARCHAR2(100),
    version_no NUMBER
);
~~~

Create a compatible target table and establish the chosen baseline/instantiation *before* starting synchronized apply. Ensure the source table is included in Extract logging and TABLE rules, and the Replicat MAP points to its target counterpart.

Then execute controlled source transactions in the lab:

~~~sql
INSERT INTO app_src.gg_lab_validation
    (test_id, payload, version_no)
VALUES (10001, 'INSERT_TEST', 1);
COMMIT;

UPDATE app_src.gg_lab_validation
SET payload = 'UPDATE_TEST', version_no = 2
WHERE test_id = 10001;
COMMIT;

DELETE FROM app_src.gg_lab_validation
WHERE test_id = 10001;
COMMIT;
~~~

### Validate each stage, not only the final deleted row

After the INSERT, query the target and expect **one row with INSERT_TEST and version 1**. After the UPDATE, expect **one row with UPDATE_TEST and version 2**. After the DELETE, expect **zero rows** on both sides. Save query output and process checkpoints after *each* step. If all three tests run before checking target state, zero final rows alone cannot distinguish successful replication from never having replicated anything.

Validation query template (execute at each stage on source and target):

~~~sql
SELECT test_id, payload, version_no
FROM app_src.gg_lab_validation
WHERE test_id = 10001;
~~~

When schemas differ, substitute the target owner/table. Use a unique test identifier per session and identify test timestamp, source commit confirmation, Replicat checkpoint and target query time. For high-assurance checks, supplement a single-row test with row counts and checksums across a defined, stable data set.

**Acceptance criteria:** Source committed; Extract trail recorded; path transported; Receiver wrote target trail; Replicat applied; target query reflects each committed state after reasonable catch-up; no hidden unresolved errors.

## 9. Troubleshooting target apply

| Symptom | Check in order | Unsafe shortcut to avoid |
|---|---|---|
| Replicat cannot start | Target credential, wrong service/PDB, checkpoint table, trail prefix, parameter syntax, report | Recreating Replicat at NOW |
| Replicat running but rows absent | MAP scope, source/target object names, inbound apply status, checkpoint, filtered transactions | Claiming success from INFO only |
| Unique constraint collision | Was target baseline already loaded? Duplicate key? Wrong instantiation? | Permanently enabling HANDLECOLLISIONS |
| Missing target row on UPDATE/DELETE | Target baseline, PK/UK logging, mapping/key columns, prior apply errors | Suppressing error to advance checkpoint |
| DDL/schema drift | Object structure, source DDL strategy and support | Disabling referential constraints without plan |
| Apply lag grows | Target database load, contention, inbound apply workers, constraints, large transaction, trail backlog | Restarting repeatedly without identifying reason |
| Gap/missing target trail sequence | Receiver output, purging, disk retention and checkpoint | Deleting trails or skipping sequences |

**Collision handling:** Oracle documents NOHANDLECOLLISIONS as the default. HANDLECOLLISIONS is limited to supported initial synchronization workflows and may mask actual divergence if left enabled. Verify its compatibility with the configured Replicat mode; do not use it as a routine recovery technique.

## 10. Implementation evidence

~~~text
Date / operator / reviewer:
Oracle DB source and target versions, CDB/PDB:
GoldenGate build:
Extract name and source trail:
Distribution/Receiver path and target trail:
Replicat type and name:
Source/target schemas and validated MAP:
Checkpoint table and creation evidence:
Initial load/snapshot and start checkpoint:
Credential aliases (no secrets):
INSERT source commit and target row output:
UPDATE source commit and target row output:
DELETE source commit and target row output:
Source-to-target row counts/checksums:
Replicat INFO, STATS, report and apply diagnostics:
Errors and corrections:
Replication result: VERIFIED / FAILED / PARTIAL / NOT TESTED
Evidence file references (sanitized):
~~~

## 11. Verification criteria

1. What does the Oracle integrated inbound server do?
2. Why is creating a checkpoint table useful for restart recovery?
3. Why does Integrated Extract registration differ from normal Integrated Replicat startup registration?
4. Why must Replicat read the **target** trail prefix?
5. Can target zero rows after a DELETE prove that INSERT and UPDATE replicated?
6. Which data-creation and checkpoint boundaries need alignment before starting Replicat?

**Answer summary:** Inbound server applies LCRs; checkpoints record durable apply position; Replicat normally auto-registers; target trail is the Receiver output; no, intermediate state must be checked; capture start/initial snapshot/target baseline and Replicat entry point must be consistent.

## Verification status

- **Vendor-confirmed:** Integrated Replicat mode, ADD REPLICAT syntax, checkpoint table guidance, GUI steps.
- **reference-derived:** Replicat process overview, log/lag/collision discussion, initial-load distinction.
- **Examples:** Schema/process identifiers and expected results are illustrative; actual execution evidence belongs in the lab record.

## Oracle references

- [ADD REPLICAT — Oracle GoldenGate 26ai](https://docs.oracle.com/en/database/goldengate/core/26/gclir/add-replicat.html)
- [Add a Replicat — Microservices procedure](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/replicat-add-replicat_procedure.html)
- [Before Adding Extract and Replicat Processes — checkpoint table](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/configure-ogg-adding-extract-and-replicat.html)
- [Configure Oracle GoldenGate Environment](https://docs.oracle.com/en/database/goldengate/core/26/ggmah/task-2-configure-oracle-goldengate-environment.html)

**Next:** [07 — Initial Load, SCN/CSN and Cutover](07-initial-load-scn-csn-and-cutover.md)
