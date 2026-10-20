# 11 — Performance, High Availability and Automation

> **Reference scope:** Oracle-documented operations and illustrative tuning examples; measured results require separate evidence.

## Scope and operating requirements

Identify the slowest pipeline stage, distinguish workload bottlenecks from replication configuration errors, interpret Integrated Replicat parallelism, design GoldenGate service availability, set safe managed-process restarts and purge policies, and prove improvements with reproducible before/after metrics.

## 1. Establish a measured performance baseline

```text
Source application commit
 -> redo generation and Extract
 -> source trail and Distribution Service
 -> network / Receiver Service and target trail
 -> Replicat / database inbound server
 -> target committed transaction
```

Measure each stage before tuning. Useful metrics: committed source DML per second, trail creation/transport rate, per-stage lag, heartbeat end-to-end latency, current trail sequence and checkpoint, target sessions/locks/CPU/I/O, transaction size and source-to-target row correctness.

**Never tune solely because INFO ALL reports a large lag.** An idle process, long-running source transaction, target data inconsistency or delayed transport needs a different remedy from CPU saturation.

### Read-only administrative inspections

```text
INFO ALL
INFO EXTRACT EXTLAB, DETAIL
LAG EXTRACT EXTLAB
STATS EXTRACT EXTLAB
INFO DISTPATH ALL
INFO REPLICAT REPLAB, DETAIL
LAG REPLICAT REPLAB
STATS REPLICAT REPLAB
```

Replace names with real, authorized deployment process names; some commands require connecting to a particular deployment. Use the Administration Service and Performance Metrics Service to inspect throughput, resource trends and checkpoints. Automatic heartbeat tables, when configured, provide end-to-end lag measurements.

Oracle 26ai integrated diagnostics supplies sampled CPU, waits and other Extract/Replicat metrics and can export a diagnostic collection. Avoid interpreting one snapshot as a representative benchmark.

Oracle: https://docs.oracle.com/en/database/goldengate/core/26/coredoc/monitor-integrated-diagnostics.html

## 2. Find the bottleneck instead of guessing

| Observed pattern | Investigate first |
|---|---|
| Extract lag grows; source trail stays behind | Source redo/log access, LogMiner integrated capture, long transactions, source CPU/I/O, registration and process report |
| Extract healthy; transport lag grows | Source/target trail sequence, Distribution/Receiver service, network RTT/bandwidth, TLS and connection errors |
| Target trail advances; Replicat lag grows | Target CPU/I/O, locks, keys/indexes, apply mode, transaction dependencies, inbound server waits, MAP/filtering |
| All processes run but target incorrect | Snapshot/instantiation position, missing keys, excluded tables, filtering, collision/error suppression |
| Lag spikes on DDL or key updates | Barrier transactions and synchronization of parallel apply workers |

**Controlled tuning cycle:** measure a stable time window → select one evidence-based hypothesis → change one documented setting in an isolated lab → compare throughput/lag **and data consistency** → retain or roll back. Record workloads and hardware so the result can be reproduced.

## 3. Integrated Replicat and parallel apply

Integrated Replicat hands logical change records to the target Oracle inbound server. The inbound server determines dependencies and applies independent transactions in parallel while preserving required ordering. Oracle 26ai exposes inbound-server tuning options under DBOPTIONS INTEGRATEDPARAMS (or supported dynamic SEND REPLICAT commands).

Oracle 26ai lists PARALLELISM, MAX_PARALLELISM, MAX_PGA_SIZE, MAX_SGA_SIZE, COMMIT_SERIALIZATION and other controls. Oracle documentation states a default PARALLELISM of 4 and MAX_PARALLELISM of 50 for its Integrated Replicat configuration; **these defaults are vendor reference values, not the measured values of your lab**. Standard Edition has additional limits. Parallelism higher than the workload, memory or target can use may not help.

```text
-- CONFIGURATION EXAMPLE ONLY; do not add without release/support check and change approval
DBOPTIONS INTEGRATEDPARAMS (PARALLELISM 4, MAX_PARALLELISM 8)
```

This is a **hypothetical tuning experiment**, not a blanket recommendation. Record current inbound-server settings and measured transactions/sec before applying. Check target memory, concurrency, source transaction dependencies, and Oracle edition.

Oracle also documents direct-apply fallback for certain operations (including DDL, SQLEXEC and EVENTACTIONS). Use STATS REPLICAT to examine direct versus integrated apply counts before selecting a strategy. Large proportions of direct apply or barrier transactions can limit improvements from parallelism.

References:
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/replicat-integrated-replicat.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/replicat-additional-parameter-options-integrated-replicat.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/monitoring-and-controlling-processing-instantiation-1.html

## 4. Database design can dominate Replicat throughput

Oracle explains that absent a usable primary/unique key or index, Replicat may form a row-search predicate using all columns, leading to expensive target scans. Verify target keys and required foreign-key indexes, dictionary stats, hot blocks, constraints, triggers and high-volume transactional patterns.

An explicit KEYCOLS designation can change row identification when warranted, but it must identify a truly unique, stable key supported by data and logging. Never assign arbitrary columns solely to improve a benchmark.

Parallel Replicat groups and multi-process splits can improve throughput but may violate original transaction atomicity if cross-table dependencies are split improperly. Design splits with measured dependency analysis.

References:
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/tuning-replicat-transactions.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/using-multiple-process-groups.html

## 5. GoldenGate availability: understand the failure domains

```text
Source DB / redo | GoldenGate Capture Host | source trails | network
Target GoldenGate Host | receiver/target trails | Replicat | Target DB
```

GoldenGate service recovery is different from **database high availability** and different again from **end-to-end application availability**. Identify each failure domain and decide whether an interruption may create capture/apply backlog, a missed trail, an inaccessible credential wallet or a source-side redo-retention gap.

Oracle Microservices Service Manager supports these modes: manual, daemon/systemd, and Oracle Grid Infrastructure Agent (XAG). Choose exactly one service lifecycle owner; do not run independent competing start/stop mechanisms.

### Read-only Linux service checks

```bash
systemctl status OracleGoldenGate --no-pager
systemctl is-enabled OracleGoldenGate
journalctl -u OracleGoldenGate -n 80 --no-pager
```

These diagnose a **daemon-managed** instance with that unit name; a manually managed or XAG-managed deployment requires its appropriate mechanism.

### XAG / Grid Infrastructure

An XAG-managed deployment must follow the configured Clusterware resource lifecycle, dependencies, shared-storage and service/endpoint plans. Oracle's 26ai upgrade notes impose Service Manager/deployment version compatibility restrictions when XAG is enabled. Avoid importing a manual restart technique from an unrelated host into an XAG-managed deployment.

References:
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/deploy-start-stop-sm.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/overview-upgrade-procedure.html

## 6. Managed-process auto start and restart

GoldenGate Administration Service supports Managed Process Profiles for Extract and Replicat, with Auto Start, Auto Restart, restart attempts, delay and retry window. Use profiles in accordance with incident escalation—not simply indefinite restart loops.

**A restart policy must address:**

1. What process failure is transient versus a repeatable configuration/credential/redo failure?
2. What is the maximum retry count and operator notification threshold?
3. Can dependent services, paths and target DB actually resume?
4. Has the previous trail/recovery checkpoint been preserved?
5. Is the deployment under XAG management?

Oracle warns against setting 'Critical to deployment health' on managed-process profiles under XAG: an unavailable Extract or Replicat can prevent related XAG-managed resources from starting.

**Restart policy values require testing.** A fixed attempt count and delay should be chosen for the environment, failure type and alerting policy rather than copied into every deployment.

Reference: https://docs.oracle.com/en/database/goldengate/core/26/coredoc/extract-managed-processes.html

## 7. Safe maintenance automation

Oracle supports scheduled Administration Service tasks: archive trails, purge trails, purge certain processes, and lag reports. Archive/purge behavior must honor the oldest downstream consumer checkpoint, operational retention requirements and disaster-recovery backups.

**Purge-trail risk:** If 'Use Checkpoints' is disabled, Oracle states a trail may be purged once its age/file rule is reached **even if not consumed**. Production automation should explicitly assess checkpoint-aware purging and plan for stopped Replicat or network outages.

Recommended automated signals: process status transitions, heartbeat end-to-end lag versus SLA, checkpoint progression, filesystem capacity trend, redo/trail backlog, repeated abends, certificate expiry and failed maintenance tasks.

**Avoid:** automated DELETE/ALTER process commands, checkpoint advance to NOW, blanket filesystem cleanup, or error-suppression switches as a reflexive self-healing strategy.

Reference: https://docs.oracle.com/en/database/goldengate/core/26/coredoc/automate-maintenance-tasks-1.html

## 8. Automation design without secrets

A safe monitoring workflow reads secured APIs or approved command outputs, logs a timestamp and deployment identity, validates command response status, redacts connection details, and raises an alert if a metric exceeds the approved threshold.

```text
Every monitoring cycle:
  identify deployment and check access
  read status, lag, heartbeat and storage metrics
  compare against documented SLA and last good checkpoint
  emit metrics/alert with deployment ID and timestamp
  NEVER reposition, delete trails or restart processes automatically
        unless a separate tested remediation policy explicitly permits it
```

For scripts, use secure secrets management or restricted authentication profiles. Never embed an actual password, wallet blob or long-lived token in a public GitHub repository. Restrict read-only monitoring accounts appropriately.

## 9. Capacity and resilience planning

**Hypothetical case:** the source generates 40 GB of relevant trail data per hour. The downstream target can be unavailable for 6 hours. What baseline retention volume is needed?

40 GB/hour × 6 hours = 240 GB **before** headroom, bursts, archived redo, filesystem metadata, backup lag and recovery margins. This is not a GoldenGate product requirement or a capacity assessment of your installation. State your assumed peaks, trail compression and response time and use measured real data for engineering decisions.

**Capacity review:** If a 6-hour target outage becomes 12 hours, the minimum estimated backlog doubles. Why may the actual required space differ? Because workload bursts, multiple paths, filtering, trail representation and checkpoint/retention policies vary.

## 10. HA and tuning troubleshooting scenarios

| Scenario | Root-cause candidates | Evidence needed |
|---|---|---|
| Restart loop with recurring authentication failure | Expired alias, wallet access, service identity | Log, retry settings, credential state |
| Replicat lag increases after parallelism increase | Target CPU/lock contention, barriers, apply server waits | Throughput/lag before and after, inbound server diagnostics |
| Service Manager restarted but DEP1 services missing | Wrong lifecycle mode, child services, ports, XAG dependency | Service inventory, process ownership, deployment log |
| Replicat process healthy but target diverged | Bad baseline, filter/MAP, skipped errors | Consistent source-target row comparison |
| Filesystem nearing capacity | Unconsumed trails, too-short retention, source spikes | Oldest checkpoint, bytes/hour, downstream state |
| Replication resumes after failover but shows missing sequence | Inaccessible trails, unshared storage, restore omission | Trail inventory, checkpoints, recoverable backups |

## 11. Performance lab — reusable evidence worksheet


## 12. Operational acceptance criteria

1. Why does increasing parallelism not always improve apply performance?
2. What is the difference between end-to-end latency and INFO ALL lag?
3. What makes an XAG-controlled GoldenGate deployment distinct from a systemd service?
4. What happens if automated Purge Trails ignores checkpoints?
5. What proof is required to claim a tuning change improved replication safely?

**Answer key:** workload dependencies, database saturation and direct apply may cap throughput; checkpoint lag is not a measured end-to-end latency; Clusterware/XAG owns resource lifecycle and dependencies; unconsumed trails may be deleted; controlled before/after workload, lag/throughput, error-free recovery and data reconciliation are required.

## Verification status

- **Technical background:** general Microservices roles, lag monitoring, autostart/restart discussions.
- **Oracle-verified reference:** integrated apply options, diagnostics, managed process profiles, XAG restrictions, automated maintenance and heartbeat concepts.

## Official documentation

- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/replicat-integrated-replicat.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/replicat-additional-parameter-options-integrated-replicat.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/monitor-integrated-diagnostics.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/using-multiple-process-groups.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/extract-managed-processes.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/deploy-start-stop-sm.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/automate-maintenance-tasks-1.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/monitor-monitor-lag.html

**Next:** [12 — End-to-End Implementation Lab](12-end-to-end-implementation-lab.md)
