# Oracle GoldenGate 26ai Engineering Field Guide

Reference procedures for GoldenGate Microservices architecture, installation, capture, transport, apply, operations and migration.

## Engineering topics

01. [Architecture and Deployment Prerequisites](01-architecture-and-prerequisites.md) — architecture, read-only SQL reconnaissance, validation exercises and evidence standards.
02. [Installation and Microservices Deployment](02-installation-and-microservices-deployment.md) — prerequisites, installation options, OGGCA, Service Manager lifecycle, security and lab validation.
03. [Oracle Database Preparation](03-oracle-database-preparation.md) — CDB/PDB scope, ARCHIVELOG, privileges, supplemental logging, credentials and SQL verification.
04. [Integrated Extract and Source Trails](04-integrated-extract-and-source-trails.md) — capture registration, parameters, trails and checkpoint diagnostics.
05. [Distribution and Receiver Services](05-distribution-and-receiver-services.md) — secure network path setup, trail transport, filtering and monitoring.
06. [Integrated Replicat and Validation](06-integrated-replicat-and-validation.md) — checkpoint table, Integrated Replicat, SQL DML tests, reconciliation and troubleshooting.
07. [Initial Load, SCN/CSN and Cutover](07-initial-load-scn-csn-and-cutover.md) — Data Pump instantiation, file-based load, positioning, validation, and cutover/rollback.
08. [Monitoring, Checkpoints and Recovery](08-monitoring-lag-checkpoints-and-recovery.md) — diagnostics, heartbeat, retention, troubleshooting and recovery exercises.
09. [Parameters, Filtering, Mapping and Collisions](09-parameters-filtering-mapping-and-collisions.md) — safe changes, table onboarding and validation exercises.
10. [Security and Interoperability](10-security-credentials-and-interoperability.md) — accounts, TLS, credentials, and mixed-mode integration.
11. [Performance, High Availability and Automation](11-performance-high-availability-and-automation.md) — bottleneck diagnostics, parallelism, managed processes, XAG, retention and exercises.
12. [End-to-End Implementation Lab](12-end-to-end-implementation-lab.md) — end-to-end lab plan, safety gates, DML validation, recovery exercises and acceptance criteria.

## Verification standard

Use current Oracle documentation for release-specific syntax. Link observed deployments, parameters, and logs only when evidence is available.

## 1. Choose the topology

GoldenGate replication is a logical data-movement pipeline. Determine whether Extract and Replicat reside on source, target or separate hub infrastructure. See [six deployment methodologies](../six-deployment-methodologies.md).

```text
Source Oracle database
  -> Extract (capture)
  -> local trail
  -> Distribution Path / Receiver (when configured across deployments)
  -> target trail
  -> Replicat (apply)
  -> target database
```

Physical Data Guard redo apply and GoldenGate logical replication serve different purposes. A physical standby is not normally a writable Replicat target.

## 2. Installation and Microservices planning

Before software installation, record Oracle and GoldenGate versions, certification, Oracle Linux/kernel baseline, storage, service accounts, directory layout, port assignment, network/firewall rules, TLS setup, TNS connectivity and restart procedures.

Example invocation patterns (verify against the installed release):

```bash
# Oracle Universal Installer: response file must exist and match installed release.
./runInstaller -silent -responseFile /path/to/install.rsp

# OGGCA: example only; confirm option case and response file structure.
./oggca.sh -silent -responsefile /path/to/deployment.rsp
```

A complete OGGCA runbook additionally needs the actual sanitized response-file keys, location of executable, Service Manager registration method, deployment service configuration, encrypted administration access and health checks. These inputs must be collected from the actual deployment before the procedure is considered executable.

## 3. Database prerequisites and logging

Check database role, CDB/PDB layout, open mode, ARCHIVELOG status, supplemental logging, privileges and network access **before** enabling capture.

```sql
-- Read-only diagnostics: run with appropriate database privileges.
SELECT name, open_mode, database_role, log_mode
FROM v$database;

SELECT supplemental_log_data_min
FROM v$database;

SELECT capture_name
FROM dba_capture;
```

Illustrative configuration statement:

```sql
-- CHANGE CONTROL REQUIRED: Oracle database setting, not a read-only check.
ALTER SYSTEM SET enable_goldengate_replication = TRUE;
```

GoldenGate privileges should be granted using Oracle-supported role-specific methods, including `DBMS_GOLDENGATE_AUTH` where applicable; do not treat unrestricted `GRANT DBA` as the default. Database-level and table-level supplemental logging require source-specific selection and verification.

## 4. Admin Client and process review

For Microservices Architecture, the client commonly launches from GoldenGate home:

```bash
cd "$GG_HOME/bin"
./adminclient
```

Illustrative Admin Client inspection commands:

```text
INFO ALL
INFO EXTRACT EXT1
INFO REPLICAT REP1
INFO DISTPATH ALL
```

Validate commands in the actual administrative context; never place plain-text passwords in command examples or shell history.

## 5. Extract, trail transport and Replicat

Each replication path needs captured scope, source logging, trail prefixes, checkpoint state, credentials, target mappings and process monitoring. Confirm the trail produced by Extract is the trail consumed by Distribution/Replicat. A process reporting RUNNING is insufficient proof of target data correctness.

Source scope and target mapping examples (illustrative, not an executed lab configuration):

```text
-- Extract parameter idea
TABLE source_pdb.source_schema.table_name;

-- Replicat parameter idea
MAP source_pdb.source_schema.table_name,
    TARGET target_pdb.target_schema.table_name;
```

Create and validate the required Extract and Replicat process types using release-appropriate GUI/Admin Client workflows. A complete runbook must record actual parameters, database privileges, checkpoint behavior, target instantiation and process-specific status output.

## 6. Initial load and migration cutover

A consistent source snapshot and transactional capture must be aligned to an **explicit, verified instantiation position**. Capture start, snapshot consistency, target baseline, and Replicat start must not introduce gaps or double-apply.

```sql
-- Diagnostic example; this query alone does not establish safe instantiation.
SELECT current_scn FROM v$database;
```

Do not generalize `AFTERCSN` examples into a zero-downtime cutover recipe. Validate supported start syntax and semantics, source/target consistency, reconciliation, cutover gates, rollback capability and downtime commitments.

## 7. Filtering, column mapping, and new tables

`WHERE` and `FILTER` support selective transactions, subject to database and GoldenGate syntax. `COLMAP` and `USEDEFAULTS` support target-column mapping. Verify the effect on inserts, updates and deletes by running explicit before/after tests.

```text
MAP source_schema.source_table,
    TARGET target_schema.target_table,
    COLMAP (USEDEFAULTS, target_column = source_column);
```

For adding a new table, coordinate supplemental logging, capture inclusion, consistent initial load, Replicat mapping and exact start/instantiation point. Avoid unplanned stoppages of shared pipelines.

## 8. Troubleshooting and operations

1. Confirm Service Manager and the intended deployments, including component processes and listeners.
2. Check Extract, Distribution Path, Receiver and Replicat status and reports.
3. Compare input/output trail names, sequence numbers, and checkpoints.
4. Evaluate lag relative to the system's required SLA and activity, not an arbitrary ten-second threshold.
5. Check database connectivity, privileges, supplemental logging, missing row keys, conflicts and abends.
6. Validate source versus target counts/checksums and INSERT/UPDATE/DELETE transaction results.
7. Document the time window, confirmed root cause, tested remediation and rollback.

**Do not** replace wallet files using wallets copied from a dummy deployment to reset access. Use a documented vendor-supported administrative recovery method.

## 9. Validation checklist before a 'completed' claim

| Check | Result to record |
|---|---|
| Oracle / GoldenGate compatibility | Tested versions and platform certification |
| Database and supplemental logging | SQL output with source role and required log groups |
| Service Manager / deployment | REST or Admin Client service status |
| Extract | Integrated capture registration, status, read position |
| Trail transport | Consistent prefixes, receiver delivery and checkpoint |
| Replicat | Start position, apply status, report, no unhandled errors |
| Transaction tests | INSERT, UPDATE, DELETE, plus DDL only when configured |
| Data reconciliation | Row-level correctness, consistency, and timing |
| Failure testing | Restart and recovery outcome, with saved logs |
| Publication hygiene | Redacted credentials, client data, IPs where sensitive |

## 10. Next engineering deliverables

- Record complete sanitized OUI and OGGCA response files from an actual supported lab deployment.
- Publish tested Extract and Replicat parameter files and command transcripts.
- Document initial-load strategy with instantiation verification and restart recovery.
- Cross-link the [Oracle 19c → 26ai migration](https://github.com/omoriwor-commits/enterprise-data-platform-labs/tree/main/migrations/oracle-19c-to-26ai-goldengate) without suggesting that illustrative commands reproduce the project's original executed configuration.

