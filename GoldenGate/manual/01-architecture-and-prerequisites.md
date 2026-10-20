# 01 — Architecture and Deployment Prerequisites

**Scope:** Oracle GoldenGate 26ai Microservices Architecture (MA), Oracle-to-Oracle replication design, and deployment readiness. Diagrams are reference topologies; deployment evidence is maintained in the linked project records.

## 1. Replication architecture

Oracle GoldenGate captures selected logical changes from a source and applies them to a target. It supports migration and change data capture where the exact database/software combination is certified. It does **not** replace RMAN backups or Oracle Data Guard physical standby recovery.

```text
Oracle source database redo
          |
    Integrated Extract
          |
      Source trail
          |
  Distribution Service
          | authenticated transport
    Receiver Service
          |
      Target trail
          |
        Replicat
          |
    Target database
```

This is a two-deployment MA topology. Actual Extract/Replicat placement can vary. A RUNNING process does not guarantee correctness; each stage needs checkpoint, trail, and target-row evidence.

### Transaction flow

1. Oracle records a committed source change in redo.
2. Integrated Extract captures the configured logical operation and writes it to a local trail.
3. Distribution sends the trail stream to the target Receiver, where a target trail is written.
4. Replicat reads the target trail and applies the mapped change.
5. The DBA confirms target consistency **after catch-up**, accounting for intentional filtering or transformations.

Initial data instantiation and capture-start positioning are separate requirements; CDC alone will not populate preexisting source rows.

## 2. Microservices responsibilities

| Component | Responsibility | Operational check |
|---|---|---|
| Service Manager | Manages deployment services | Service state, deployment inventory and listener ports |
| Administration Service | Configures/controls Extract and Replicat | Parameters, reports, checkpoints and database connections |
| Distribution Service | Streams source trail records via Paths | Source trail, path progress and endpoint |
| Receiver Service | Receives trail records on target | Receiver status, target trail and sequence |
| Performance Metrics Service | Exposes performance metrics | Trends in lag, throughput, and failures |
| Admin Client | CLI administration for deployments | Correct authenticated deployment context |
| Extract | Captures source changes | Capture registration, input/recovery checkpoints |
| Replicat | Applies target changes | Mapping, target privileges, apply errors and checkpoint |

Oracle documentation: [Microservices Architecture components](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/overview-components-oracle-goldengate-microservices-architecture.html).

## 3. Classic versus Microservices

| Area | Legacy Classic | Microservices |
|---|---|---|
| Administration | GGSCI, Manager, OS processes | Administration Service, REST/WebUI, Admin Client |
| Data capture and apply | Extract, trails, Replicat | Extract, trails, Replicat under deployments |
| Inter-host transport | Data pump and Collector | Distribution and Receiver services |
| Operations | Manager and process lifecycle | Service health plus process/path checkpoints |

For 26ai deployments, use the certified architecture and Oracle release guidance. Mixed connectivity to **existing older Classic deployments** requires explicit interoperability and transport-security review; see [Topic 10](10-security-credentials-and-interoperability.md).

## 4. Six process-placement patterns

| Pattern | Extract placement | Replicat placement | Design trade-off |
|---|---|---|---|
| Local / local | Source host | Target host | Software installed at each database host |
| Local / remote | Source host | Remotely connects to target | Source-host concentration, network dependence |
| Remote / local | Target-side host, remote source capture | Target host | Less source-host software; verify remote capture support |
| Hub / hub | Intermediate hub | Intermediate hub | Central administration and shared failure domain |
| Hub / local | Hub | Target host | Central capture, local target apply |
| Local / hub | Source host | Intermediate hub | Local capture and remote target apply |

These are **placement patterns**, not standalone claims of certification or network readiness. For detailed placement implications see [Deployment Methodologies](../six-deployment-methodologies.md).

### Project context

The separately recorded [Oracle 19c→26ai migration](https://github.com/omoriwor-commits/enterprise-data-platform-labs/tree/main/migrations/oracle-19c-to-26ai-goldengate) describes remote Integrated Extract `EXT19C` and target Integrated Replicat `REP26AI`. Available evidence does not contain every original parameter and command transcript, so that project should not be presented as a fully reproduced runbook.

The separate [OCI→Azure project](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab) documents source capture and trail-delivery milestones; complete SQL Server apply has not been verified in the published record.

## 5. Prerequisite design review

| Area | Required decision or evidence |
|---|---|
| Product support | Exact source/target Oracle versions, GoldenGate builds, platforms and support matrix |
| Database | CDB/PDB, roles, open modes, connection services and privileges |
| Scope | Tables, keys, supported DML/DDL, LOB requirements and exclusions |
| Redo and logging | ARCHIVELOG, required supplemental logging and retention |
| Storage | Binary homes, deployment homes, trail volume and checkpoint-aware purging |
| Security | OS/service/database identities, TLS/WSS, key/credential recovery |
| Network | Reachability, firewall ports, DNS, service endpoints, certificates |
| Migration baseline | Consistent initial load, capture registration and SCN/CSN coordination |
| Operations | Monitoring, planned outage, service lifecycle, failover and fallback |
| Acceptance | Target DML reconciliation, measured lag and signed-off recovery criteria |

### Read-only Oracle inventory

Use a suitably privileged SQL*Plus/SQLcl session; record the exact source database and container.

```sql
SHOW CON_NAME;
SHOW USER;

SELECT name, db_unique_name, database_role, open_mode, log_mode,
       supplemental_log_data_min
FROM v$database;

SHOW PARAMETER enable_goldengate_replication;

-- Run from an appropriate CDB administrative session.
SELECT con_id, name, open_mode
FROM v$pdbs
ORDER BY con_id;
```

These commands provide inventory only. Do not alter ARCHIVELOG, initialization parameters, logging or credentials without a planned database change. Privilege and syntax decisions differ between Oracle Database 19c and AI Database 26ai.

## 6. Fault-isolation order

If the Extract is RUNNING but a target row is missing, verify:

1. The source change was committed on a selected table.
2. Extract registration, required logging and capture checkpoints are correct.
3. The expected local trail advanced.
4. Distribution reads that trail and Receiver delivers the matching target trail.
5. Replicat consumes the trail without unresolved errors.
6. Table mappings, key columns, filters and initial-load positions are correct.
7. Source and target data agree after the agreed catch-up boundary.

Avoid diagnosing the entire pipeline from a single INFO status field.

## 7. Implementation acceptance

- [ ] Source/target certification and topology recorded.
- [ ] Source and target CDB/PDB identities verified.
- [ ] Key columns, logging and credentials approved.
- [ ] Initial-load and change-capture boundary specified.
- [ ] Storage and retention plan checked against expected outages.
- [ ] End-to-end verification procedure defines exact expected rows and checkpoints.
- [ ] Changes and recovery actions have an owner and rollback plan.

**Validation evidence:** Attach actual environment inventory and transaction-test output to the project record when available; this architecture reference does not itself establish execution.

## Oracle references

- [Microservices components](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/overview-components-oracle-goldengate-microservices-architecture.html)
- [Microservices overview](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/overview-oracle-goldengate-microservices-architecture.html)
- [Oracle GoldenGate 26ai documentation](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/index.html)

**Next:** [02 — Installation and Microservices Deployment](02-installation-and-microservices-deployment.md)
