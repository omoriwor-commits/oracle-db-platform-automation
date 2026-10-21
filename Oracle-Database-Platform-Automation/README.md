# Oracle Database Platform Automation

> **Project overview: one integrated project, not separate Oracle/DevOps/multi-cloud projects.** The controlling roadmap is [ROADMAP.md](ROADMAP.md).

## Mission

**Starting point:** Before this project, I took one Oracle workload through three GoldenGate 26ai migrations: (1) Oracle database upgrade and OS migration with replication, (2) on-premises to OCI cloud migration with replication, and (3) cross-cloud heterogeneous Oracle-to-SQL Server migration with replication. This project rebuilds that path as a repeatable, automated platform and publishes the evidence.

Build a repeatable, automated, secure, observable and recoverable Oracle database platform using the **DevOps syllabus** as the learning and implementation framework.

**Career target:** Database Platform Engineer / Oracle Database Engineer with DevOps and Cloud Automation skills.

**Method:** Learn → Build → Test → Prove → Document → Publish.

## Portfolio layout

One Oracle Database Platform Automation project spans three linked repositories:

| Repository | Holds |
|---|---|
| oracle-db-platform-automation (this repo) | Controlling roadmap, DBA runbooks, operational scripts and incident reports; Terraform, Ansible and CI/CD integration remain planned |
| [enterprise-data-platform-labs](https://github.com/omoriwor-commits/enterprise-data-platform-labs) | Migrations 1 and 2: Oracle 19c to 26ai, and on-premises 26ai to OCI |
| [enterprise-multicloud-database-platform-lab](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab) | Migration 3: OCI Oracle 26ai to Azure SQL Server 2022; RAC build runbooks, health checks and validation evidence |

Migration evidence stays in its implementation repository and is linked here rather than duplicated. Completed lab results and remaining evidence-publication work are identified in each repository.

## Architecture v1

```text
OCI: Oracle Database 26ai (source)
       |
       | Site-to-site IPsec VPN / BGP
       | One-way heterogeneous CDC
       v
Azure: GoldenGate 26ai services
       |
       | Replicat / apply and validation
       v
Azure: SQL Server 2022 (target)

Cross-cutting: GitHub Actions | Terraform | Ansible | Security
               Prometheus/Grafana | Backup/Recovery | Runbooks

Local supporting lab: Oracle RAC / ASM
Parallel core track: AWS database modernization (Terraform + schema conversion + DMS Full Load/CDC + PostgreSQL)
Advanced extension: AI automation
```

**Status:** The pipeline shown was completed in my earlier lab. Within this project it will be rebuilt with Terraform, Ansible and CI/CD.

## DevOps syllabus mapped to project deliverables

| Phase | Subject | Working evidence / deliverable |
| --- | --- | --- |
| 0 | Foundation | Goals, architecture, scope, security baseline, cost controls |
| 1 | Linux and Bash | Oracle health checks and operational scripts |
| 2 | Git and GitHub | Version control, branches, pull requests, documentation |
| 3 | Database CI/CD | SQLcl/Liquibase, GitHub Actions, dev→test→prod, tfsec/Trivy and secret hygiene |
| 4 | OCI | IAM, VCN/networking, compute, storage and database infrastructure |
| 5 | Terraform | Modules, provisioning, protected remote state |
| 6 | Ansible | Oracle Linux/database configuration, Vault for secrets |
| 7 | Docker | Oracle Database Free container and tools |
| 8 | Kubernetes | Helm, StatefulSets, persistent volumes; learning/lab scope |
| 9 | Observability | Prometheus/Grafana; availability, CDC lag, backup success SLOs |
| 10A | Data Guard | Standby automation, switchover/failover testing |
| 10B | RAC / ASM | Local cluster/storage lab, node-failure and recovery tests |
| 11 | GoldenGate | Oracle 26ai → SQL Server 2022 one-way heterogeneous CDC, validated |
| 12 | Integrated platform | Demonstration, runbooks, architecture, tests and portfolio evidence |
| Co-priority cloud track | AWS | Oracle 19c modernization to PostgreSQL using Terraform, schema assessment/conversion, DMS Full Load + CDC, validation, CloudWatch and cutover/recovery tests (planned) |
| Advanced | Agentic AI | Guardrailed diagnostics and operational automation |

**Phase numbers describe the syllabus, not a rigid execution order.**

## Execution order

The build order, stage targets and status live in one place: [ROADMAP.md, Execution Order](ROADMAP.md#execution-order-controlling). Phase 0 work is in [phase-00-foundation](phase-00-foundation/README.md).

## Target project directory structure

```text
oracle-db-platform-automation/
└── Oracle-Database-Platform-Automation/
    ├── README.md                  # project overview
    ├── ROADMAP.md                 # controlling roadmap and execution order
    ├── incident-reports/
    ├── docs/
    │   ├── architecture/
    │   ├── roadmap/
    │   ├── runbooks/
    │   └── evidence/
    ├── phase-00-foundation/
    ├── phase-01-linux-bash/
    ├── phase-02-git-github/
    ├── phase-03-database-cicd/
    ├── phase-04-oci/
    ├── phase-05-terraform/
    ├── phase-06-ansible/
    ├── phase-07-docker/
    ├── phase-08-kubernetes/
    ├── phase-09-observability/
    ├── phase-10a-data-guard/
    ├── phase-10b-rac-asm/
    ├── phase-11-goldengate/
    ├── phase-12-integrated-platform/
    └── extensions/
        ├── aws/
        └── ai-automation/
```

The directories above are **planned** and should be created as deliverables are added. Git does not track empty directories.

## Completion standard

Every phase must include:
- A reproducible implementation (commands, IaC, scripts or configuration).
- Successful tests with dated outputs and explicit acceptance criteria.
- Troubleshooting notes, security checks, and a rollback/recovery approach where relevant.
- A README/runbook and sanitized evidence committed to GitHub.
- Resume/LinkedIn claims **only after verification**.

Status legend: **Done** = verified evidence; **In progress** = actively implemented, not yet fully verified; **Planned** = not yet validated. Historical experience is not proof that this repository contains the evidence.

## Project governance

- **One project identity:** Oracle Database Platform Automation.
- **One master roadmap:** [ROADMAP.md](ROADMAP.md).
- **One learning framework:** DevOps syllabus applied to Oracle database platform engineering.
- **One primary data pipeline:** OCI Oracle → Azure GoldenGate → Azure SQL Server (one-way CDC).
- Oracle DBA, GoldenGate, RAC, Data Guard, RMAN, DevOps, cloud, and automation are **workstreams/phases within this project**, not competing project identities.
- Existing repositories and technical reference folders can continue to hold reusable notes or prior lab artifacts; link verified evidence rather than claiming it has moved.
- Never commit credentials, SSH private keys, connection secrets, production data, or unredacted screenshots.

## Current RAC checkpoint — October 19, 2026

The two-node Oracle 26ai RAC build and functional validation are complete in the independent VirtualBox lab. RAC1/RAC2 are OPEN and RACPDB1 is READ WRITE on both; archiving, SCAN connection distribution, controlled RAC2 stop/new-connection availability and instance/service restoration have been reported complete. Revision `2026-10-19.3` of the Python health check collected OS, Clusterware, database and ASM results in the supplied 10:46 CDT grid run: zero critical findings and four review warnings. [Health evidence](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/docs/evidence/oracle-rac/2026-10-19-rac26-health-check-v3.md).

HugePages, the OL9 UEK8/23.26.1 compatibility gap and remaining runbook Verify items are still open. This checkpoint does not mark the entire automation roadmap complete; Terraform, Ansible and CI/CD remain separately tracked goals.

## Next checkpoint

Stage 1, Order 1 — close Phase 0.
