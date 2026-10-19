# Six Oracle GoldenGate Deployment Methodologies

> Architecture study reference | Independent Oracle database engineering lab
>
> **Scope:** These are six placement patterns evaluated during the Oracle Database 19c-to-Oracle AI Database 26ai modernization project. They describe **where capture and apply components run**, not six distinct GoldenGate products or universally interchangeable supported configurations. Validate the precise GoldenGate release, operating system, database versions, privileges, network paths, and topology against Oracle's certification and architecture documentation before implementation.

## Terminology

- **Local capture:** Extract runs on the same host as the source database (or source-side database infrastructure).
- **Remote capture:** Extract runs on a different host and connects to the source database over Oracle Net.
- **Local apply:** Replicat runs on the same host as the target database (or target-side database infrastructure).
- **Remote apply:** Replicat runs on a different host and connects to the target database.
- **Hub:** A dedicated host or tier for GoldenGate services, separate from database servers. A single dedicated hub can host capture and apply components, subject to certified platform support.

Here, *local* and *remote* describe **process placement relative to each database**, not whether a database is in a public or private cloud. GoldenGate trail transport, distribution/receiver components, and service placement are additional design decisions.

## The six placement patterns

### 1. Local capture and local apply

```text
SOURCE HOST                         TARGET HOST
Oracle Source                       Oracle Target
Extract (local)  -- trail flow -->  Replicat (local)
```

Both source and target hosts run their respective GoldenGate components. This can reduce remote database access for capture/apply, but adds GoldenGate installation and lifecycle management on both database hosts.

### 2. Local capture and remote apply

```text
SOURCE HOST                     GOLDENGATE/APPLY HOST            TARGET HOST
Oracle Source + Extract  ---->  Replicat (remote)  ----------->  Oracle Target
```

Extract runs with the source; Replicat connects remotely to the target. Consider when capture can run on the source host but target-side GoldenGate installation is undesirable or unavailable.

### 3. Remote capture and local apply

```text
SOURCE HOST                     TARGET HOST
Oracle Source  -- Oracle Net --> Extract (remote) + Replicat (local)
                                Oracle Target
```

Extract runs away from the source and connects to it over Oracle Net; Replicat runs on the target host. This was the **selected design** in the independent Oracle 19c → Oracle AI Database 26ai lab, with GoldenGate 26ai hosted on the Oracle Linux 9.8 target side. The design avoided placing that GoldenGate installation on the Oracle Linux 7.9 source host. The project reported successful Extract, trail, Replicat, and end-to-end transactional validation.

### 4. Dedicated hub with remote capture and remote apply

```text
SOURCE HOST                    DEDICATED GOLDENGATE HUB                TARGET HOST
Oracle Source  -- Oracle Net -> Extract + trail + Replicat -- Net --> Oracle Target
```

A separate hub hosts both capture and apply processes. This separates GoldenGate lifecycle management from database hosts, at the cost of additional compute, network dependencies, and operational design. Specific heterogeneous configurations may need **separate database-specific GoldenGate runtimes**.

### 5. Hub-based remote capture with local apply

```text
SOURCE HOST             DEDICATED HUB                       TARGET HOST
Oracle Source --------> Extract (remote) -- trail flow --> Replicat (local)
                                                              Oracle Target
```

Capture runs on a dedicated hub, while apply runs on the target database host. This keeps the capture workload off the source and retains target-local apply. Requires trail transport and coordinated monitoring between the hub and target.

### 6. Local capture with hub-based remote apply

```text
SOURCE HOST                   DEDICATED HUB                  TARGET HOST
Oracle Source + Extract ----> Replicat (remote) -----------> Oracle Target
```

Capture runs on the source, while apply is hosted on a separate hub that connects to the target. This may suit deployments that permit source-local capture but require centralized target apply operations.

## Comparison

| Pattern | Extract placement | Replicat placement | Principal trade-off |
|---|---|---|---|
| 1. Local capture / local apply | Source host | Target host | Direct placement; software on both database hosts |
| 2. Local capture / remote apply | Source host | Separate apply host | Source-local capture; remote target dependency |
| 3. Remote capture / local apply | Target-side or separate host | Target host | No source-host GoldenGate runtime; source Oracle Net dependency |
| 4. Dedicated hub / remote capture and apply | Dedicated hub | Dedicated hub | Centralized operations; shared hub/network dependencies |
| 5. Hub remote capture / local apply | Dedicated hub | Target host | Source isolation; split capture/apply administration |
| 6. Local capture / hub remote apply | Source host | Dedicated hub | Source-local capture; centrally hosted remote apply |

## Selection criteria

1. **Certification and compatibility:** database versions, GoldenGate build, supported operating systems, and database-specific runtime.
2. **Change control:** whether database hosts can run GoldenGate software and receive patches.
3. **Networking and security:** listeners, private connectivity, authentication, encrypted paths, firewall rules, and latency.
4. **Operational ownership:** Extract/Replicat lifecycle, patching, observability, checkpoint and trail management.
5. **High availability and recovery:** hub resilience, failure domains, trail preservation, restart procedures, and RPO/RTO expectations.
6. **Migration validation:** initial load/instantiation, supplemental logging, INSERT/UPDATE/DELETE tests, data reconciliation, cutover, and rollback.

## Decision recorded in the original lab

**Chosen: Pattern 3 — remote capture and local apply.**

- **Source:** Oracle Database 19c, Oracle Linux 7.9, with an existing Data Guard environment.
- **Target:** Oracle AI Database 26ai, Oracle Linux 9.8.
- **GoldenGate:** 26ai Microservices running on the target-side Oracle Linux 9.8 host.
- **Processes:** Remote Integrated Extract `EXT19C`; Integrated Replicat `REP26AI`.
- **Reason:** Keep the GoldenGate 26ai installation off the older source operating system while using target-local apply and preserving the source Data Guard environment.
- **Validation described in the project:** transactional replication from the Oracle source to the AI Database target.

**Related project:** [Oracle 19c to 26ai GoldenGate migration](https://github.com/omoriwor-commits/enterprise-data-platform-labs/tree/main/migrations/oracle-19c-to-26ai-goldengate)

**Related completed heterogeneous lab:** I completed the [OCI Oracle → Azure GoldenGate hub → SQL Server lab](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab) and validated end-to-end INSERT, UPDATE and DELETE apply. The published September checkpoints preserve earlier source-capture and target-preparation stages; final sanitized target-side apply output remains to be published during a rerun. Completed implementation and published evidence coverage are tracked separately.

## Source and documentation intent

The six categories and the selected pattern were recorded in the author's LinkedIn Oracle migration progress notes. This document preserves that architecture analysis as a reusable GitHub reference, distinguishes placement patterns from certified support, and links the related implementation evidence.
