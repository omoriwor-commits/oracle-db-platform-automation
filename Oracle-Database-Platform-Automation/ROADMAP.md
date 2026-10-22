# Oracle Database Platform — Master Roadmap

**Version:** 1.2  
**Status:** Baseline / controlling roadmap  
**Target roles:** Database Migration Engineer / Cloud Database Engineer / Database Platform Engineer / Replication & CDC Engineer / Database Reliability Engineer (selective) / Cloud Infrastructure Engineer (selective)

> **Guiding question for every phase:**  
> How does this help me provision, operate, secure, recover, monitor, or automate a database platform?

**Pacing:** Phases advance by competency, not by calendar. Each phase is complete only when its **Done when** criteria are met and documented.

## Execution Order (controlling)

Phase numbers follow the DevOps syllabus. They are **not** the build order.
This section is the single controlling execution order; README.md links here
rather than repeating it. Pacing is by competency: a stage is complete only when its
**Done when** criteria are met and evidence is committed.

### Execution strategy — OCI and AWS as parallel cloud tracks

**One project, one roadmap.** OCI is the Oracle/GoldenGate platform engineering track; AWS is the complementary database modernization track. The tracks advance in parallel after Phase 0 controls, rather than delaying AWS until Phase 12. Azure remains the already completed, historically documented GoldenGate-to-SQL Server integration target, not a third new infrastructure build priority.

**Evidence boundary:** Prior independent Oracle/OCI/Azure implementations and 2023 EC2/RDS Oracle practice remain completed/user-confirmed work as recorded in their own repositories. Terraform, Ansible, database-specific CI/CD, DMS, schema conversion, Aurora PostgreSQL and newly automated recovery/migration workflows are planned until tested. The separate NGINX DevOps repository documents completed Docker/Kubernetes/GitHub Actions application CI/CD; it does not establish database CI/CD completion.

### AWS modernization implementation artifacts (proposed; not executed)

The initial target recommendation is **Amazon RDS for PostgreSQL**, subject to cost, supported-version and conversion-tool verification. **Aurora PostgreSQL** remains an optional extension. Current execution materials are: [target ADR](../AWS/architecture/ADR-001-postgresql-target.md), [DMS and schema-conversion runbook](../AWS/runbooks/oracle-to-postgresql-dms-sct-implementation.md), [acceptance matrix](../AWS/validation/aws-migration-acceptance-matrix.md), and [infrastructure/security/cost checklist](../AWS/runbooks/aws-infrastructure-security-cost-readiness.md). Schema assessment may use AWS SCT or DMS Schema Conversion only after verifying current support for the selected engine pair. The documentation does not establish deployed resources or completed tasks.

### Stage 1 — Shared controls and initial parallel workstreams (sequenced by competency, ~8-week planning target)

| Order | Workstream | Delivery target | Phase | Current status |
|---|---|---|---|---|
| 1 | Shared foundation | Protect main; inventory local/cloud resources; establish OCI/AWS budgets, IAM/secret hygiene, cost/teardown, branch/PR rules and acceptance templates | 0, 2 | In progress |
| 2 | Oracle reliability | Preserve 26ai RAC functional results, close compatibility/hardening Verify items, retain warnings and historical incident evidence | 10B, 1 | Functional build completed; follow-ups open |
| 3 | Shared quality tooling | Schedule existing RAC/Data Guard checks; store dated results; PR checks with ShellCheck/Python tests/SQL checks | 1–3 (partial) | Scripts exist; integration/validation ongoing |
| 4A | OCI infrastructure | Terraform modules for VCN, secure subnet, compute/storage, remote state and reproducible apply/destroy; use Ansible when provisioning is verified | 4–6 | Planned |
| 4B | AWS infrastructure | Terraform VPC, private database subnet/network policy, IAM/KMS/Secrets Manager and cost-controlled PostgreSQL target; reproducible apply/destroy | AWS extension, 5 | Planned |
| 5A | OCI replication | Rebuild Oracle 26ai → Azure GoldenGate → SQL Server 2022 as cost permits; publish end-to-end DML, lag, restart and reconciliation evidence | 11 | Previous independent implementation complete; automated rebuild planned |
| 5B | AWS modernization | Source Oracle 19c inventory; schema assessment/conversion; AWS DMS Full Load + CDC into PostgreSQL; document incompatible objects and supported methods | AWS extension | Planned; DMS/schema conversion not yet implemented |
| 6 | Shared database delivery | GitHub Actions gates; Oracle SQLcl/Liquibase and PostgreSQL migrations where compatible; explicit test/approval/rollback and separated secrets | 3 | Planned; NGINX application pipeline already completed elsewhere |
| 7 | Reliability and security | OCI Prometheus/Grafana and AWS CloudWatch checks; restore/cutover rehearsal, DMS lag/GoldenGate lag, least privilege, alert evidence and RCA | 9, AWS extension | Planned |
| 8 | Portfolio integration | Cross-platform validation matrix, architecture decisions, sanitized logs, demo and role-specific evidence map | 12 | Planned |

The workstreams **4A/4B and 5A/5B are parallel, not assertions of simultaneous paid cloud deployments**. Start with infrastructure plans and local/short-lived tests; avoid recurring cost. If funding or quotas block a cloud component, document it as blocked, not completed.

**Stage 1 acceptance:** Both OCI and AWS have reviewed architectures and cost/security guardrails, with at least one reproducible infrastructure deployment per cloud before marking that track implemented. Each migration track is separately accepted only after source/target validation, CDC behavior, interruption/recovery and captured evidence. Stage 1 planning dates are targets, not historical accomplishments.

### Stage 2 — Operational depth

1. Complete Oracle SQLcl/Liquibase database CI/CD, plus PostgreSQL schema-change validation and controlled promotion.
2. Automate RMAN restore/validation and capture recovery reports; preserve Oracle Data Guard work.
3. Harden IAM, network paths, TLS, database privileges, KMS and protected secrets; test negative access cases.
4. Validate Data Guard switchover/failover and Oracle RAC node/service interruption after resolving open Verify items.
5. Prove AWS migration reconciliation, cutover/rollback and DMS failure/restart behavior; document CDC limitations.
6. Re-run older Oracle migrations only when evidence gaps or required automation justify the cost.

### Stage 3 — Containers and integration

1. Reuse demonstrated NGINX GitHub Actions/Docker/Kubernetes skills; independently implement database test containers, scan images and record new proof.
2. Add Helm/Kubernetes for supporting services where relevant, rather than forcing RAC or Aurora into Kubernetes.
3. Produce an integrated, reproducible platform demonstration with separate OCI and AWS tracks, operational runbooks and role-specific evidence.

### Stage 4 — Optional advanced extensions (after core acceptance)

Broader architecture, more heterogeneous sources/targets, deeper SRE security controls and advanced AI automation. **AWS is no longer held until Stage 4**; its core database modernization scope is moved to Stage 1 and Stage 2 alongside OCI.

**Certifications:** OCI Architect Associate and Terraform Associate remain optional study goals, not credentials held or required project milestones.


---

## Phase 0 — Foundation

**Focus:** Architecture, requirements, GitHub repository, README and roadmap, security rules, cost controls, lab inventory, naming standards, documentation standards.

### Cost controls
- Configure budget alerts on OCI, AWS, and Azure before cloud work.
- Stop or destroy cloud resources at the end of each session when they are not required.
- Prefer free-tier and local resources where practical.
- Treat current free-tier quotas as operational constraints and verify them before provisioning.
- Keep infrastructure reproducible in Terraform so disposable/reclaimed resources can be rebuilt.
- Use SQL Server 2022 Developer Edition for non-production lab work where appropriate.

### Done when
- Repository/project area exists and the `main` branch is protected.
- README describes the project goal and Architecture v1.
- This roadmap, security rules, naming standards, and documentation standards are committed.
- Lab inventory lists every server, VM, and cloud tenancy used by the project.
- Budget alerts are active on every cloud account used.

---

## Phase 1 — Linux + Bash + Oracle Operations

**Focus:** Oracle Linux administration, Bash scripting, Oracle process/service checks, listener checks, tablespace checks, ASM/Data Guard checks where available, RMAN status, and log parsing.

**Monitoring progression:** Detect → record → report → schedule → alert.

### Done when
- Health-check scripts detect database, listener, tablespace, and RMAN problems.
- Results are recorded to a log and summarized in a readable report.
- Checks run on a schedule using cron or a systemd timer.
- Scripts pass ShellCheck and include usage documentation.

---

## Phase 2 — Git + GitHub

**Focus:** Version control, feature branches, commits, pull requests, code review, protected branches, troubleshooting history, and documentation as code.

### Done when
- Project work goes through feature branches and pull requests.
- Pull requests include descriptions and self-review notes.
- `docs/progress-log.md` records progress, failures, and fixes.
- A merge conflict can be resolved and `git log` / `git bisect` can be used to trace a change.

---

## Phase 3 — Database CI/CD

**Focus:** GitHub Actions; lint → test → validate → deploy → verify; SQL/PLSQL validation; schema version control; dev → test → production promotion; rollback strategy; secrets handling.

**Tool choice:** Oracle SQLcl Liquibase functionality. Flyway may be added later only when a target role or project requirement justifies it.

### Implementation principle
Make it work locally → automate it → optimize it.

The pipeline should provision an ephemeral Oracle Database Free test database locally or in CI depending on runner capacity. Account for database startup/readiness, runner memory/disk limits, image source/licensing requirements, and secure credential handling.

### Done when
- A pull request triggers a pipeline that validates schema changes.
- Schema changes are tested against an ephemeral Oracle Database Free test database.
- Promotion from dev to test to production includes an approval gate.
- A rollback has been tested and documented.
- No credentials are stored in the repository.

---

## Phase 4 — Cloud

**Focus:** OCI and AWS are co-priority cloud tracks. OCI: IAM, VCN, subnets, NSGs, routing, compute/storage and Oracle database architecture. AWS: IAM, VPC, private database subnets, EC2/RDS or Aurora PostgreSQL target selection, database connectivity and cost controls. Azure is retained as the previous GoldenGate/SQL Server replication target, not a new full-scale build priority.

**Certification objective:** OCI Architect Associate at the end of Phase 4 or Phase 5, after building the components hands-on.

### Done when
- A VCN with public/private subnets, controlled administrative access, and NSGs is built manually in OCI.
- IAM policies follow least privilege.
- The design is documented with an architecture diagram explaining each choice.
- A separate AWS VPC/private subnet/security group/IAM design is implemented and tested before claiming AWS deployment completion; architecture knowledge alone is documented as conceptual.

---

## Phase 5 — Terraform

**Focus:** Infrastructure as code with OCI and AWS providers: VCN/VPC, subnets/security, compute and database targets, variables/outputs, separate protected state per cloud/environment, reusable modules, validation, cost controls and security scanning.

### Done when
- `terraform apply` builds the dev environment from a clean starting point.
- `terraform destroy` removes disposable resources cleanly.
- Terraform state is stored securely per environment/provider with documented backend configuration, locking where supported, encryption, restricted access and recovery/versioning. Verify backend-specific locking and retention behavior before asserting it.
- Terraform state and plan artifacts containing sensitive information are excluded from Git.
- Network and compute are implemented as reusable modules.
- TFLint and an IaC security scanner such as Checkov run in the pipeline.

---

## Phase 6 — Ansible

**Focus:** Terraform creates infrastructure; Ansible configures it. Oracle Linux configuration, users/groups, packages, kernel parameters, limits, directories, storage, Oracle prerequisites, templates, roles, idempotency, Ansible Vault, and Oracle installation/configuration automation.

### Done when
- A fresh server built by Terraform is configured for Oracle by Ansible without manual configuration steps.
- Running the playbook again produces no unintended changes (idempotency).
- Secrets handled by Ansible are encrypted appropriately.
- Oracle Database software installation and database creation are automated and validated.

---

## Phase 7 — Docker

**Focus:** Images, containers, Dockerfiles, volumes, networks, registries, security scanning, Oracle Database Free container, and supporting database tools/services.

### Done when
- Oracle Database Free runs in a container with persistent storage.
- At least one appropriate supporting/custom workload uses a well-constructed Dockerfile, including multi-stage build and non-root execution where applicable.
- Images are scanned with Trivy and published to a registry.
- The Phase 3 pipeline uses the Oracle test container/database workflow.

---

## Phase 8 — Kubernetes + Helm

**Focus:** Local Kubernetes first (kind or minikube). Pods, deployments, services, ConfigMaps, secrets, storage, RBAC, Helm, and monitoring workloads. Database-adjacent services run on Kubernetes; RAC is not forced into Kubernetes.

### Done when
- Supporting services are deployed with a Helm chart.
- Persistent storage, ConfigMaps, and secrets are used appropriately.
- RBAC limits access to the required namespace/resources.
- A failed pod can be diagnosed using `kubectl describe` and `kubectl logs`.

---

## Phase 9 — Observability + Security + Recovery Assurance

### Phase 9A — Observability
**Focus:** Prometheus, Grafana, Oracle/Linux metrics, database availability, tablespace usage, backup status, and alerting.

### Phase 9B — Security
**Focus:** Least privilege, secrets management, hardening, and pipeline/security scanning.

### Phase 9C — Recovery Assurance
**Recovery workflow:** RMAN scheduled backup → automated restore test → database validation → recovery report.

**Note:** Data Guard lag and GoldenGate status dashboards are added after Phases 10A and 11 are operational.

### Done when
- Grafana dashboards show database availability, tablespace usage, and backup status.
- Alerts fire for a controlled simulated failure.
- A scheduled job restores the latest suitable RMAN backup to a scratch environment, validates the restored database, and produces a recovery report.
- Critical security findings are remediated or explicitly documented with justification and a remediation plan.

---

## Phase 10A — Data Guard Automation

**Focus:** Primary/standby databases, redo transport/apply, Data Guard Broker, monitoring, lag detection, switchover, failover exercises, and automation using Ansible, Bash, and Python.

**Resource strategy:** Prefer the local lab when cloud capacity/cost is unsuitable. Short-lived paid OCI resources may be used only with explicit cost controls and teardown procedures.

### Done when
- A standby is built through documented automation.
- Data Guard Broker reports a healthy configuration.
- Apply/transport lag is monitored and visualized in Grafana.
- Switchover and failover are each performed, timed, validated, and documented in runbooks.

---

## Phase 10B — RAC + ASM (Local Lab)

**Focus:** Oracle Grid Infrastructure, ASM, shared storage, Clusterware, RAC, failure simulation, troubleshooting, and automation where practical.

**Prerequisite:** Validate host CPU, RAM, storage, and virtualization capacity before committing to the two-node topology. Adjust VM sizing based on the Oracle version and actual host capacity.

### Current checkpoint — 2026-10-19

Two-node 26ai RAC is built and functional validation is complete: both instances OPEN, RACPDB1 READ WRITE on both, archiving and SCAN connection distribution checked, controlled RAC2 stop/new-connection availability and service restoration confirmed. The [health evidence](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/docs/evidence/oracle-rac/2026-10-19-rac26-health-check-v3.md) separates collected output from user-confirmed results. HugePages, kernel/RU compatibility, further restart/node-failure testing and other runbook Verify items remain open. This does not mark every Phase 10B criterion or the overall automation platform complete.

### Done when
- A two-node RAC database runs on ASM-backed shared storage.
- A controlled node/service failure is simulated and service behavior/relocation is observed and documented.
- At least one genuine installation/operations failure is diagnosed, root-caused, fixed, and recorded.

---

## Phase 11 — GoldenGate Heterogeneous CDC

**Focus:** Rebuild my previously completed heterogeneous CDC pipeline within this project and publish its evidence:

```text
Oracle Database 26ai (OCI)
        ↓
Oracle GoldenGate 26ai (Azure)
        ↓
SQL Server 2022 (Azure)
```

Also rerun and document migrations 1 and 2 of my completed three-stage path: 19c → 26ai (OL 7.9 → 9.8) and 26ai → OCI Compute.

Validate INSERT, UPDATE, DELETE, DDL where appropriate, lag monitoring, failure/restart, checkpoint behavior, recovery, data validation, and documentation.

**Cost control:** Stop Azure VMs between sessions when safe and appropriate; use SQL Server 2022 Developer Edition for lab/non-production use.

### Done when
- INSERT, UPDATE, and DELETE replicate end to end.
- Results are verified using row counts and data comparison.
- Replication recovers correctly after controlled process interruption/restart.
- Checkpoint/recovery behavior is understood and documented.
- Replication lag is monitored and visualized.
- Architecture, validation steps, troubleshooting, and recovery procedures are documented.

---

## AWS modernization workstream — co-priority with OCI

**Existing baseline:** The 2023 independent Oracle 19c → EC2 → RDS for Oracle work is documented in `AWS/runbooks/oracle-19c-aws-migration-2023.md`. Original historical execution logs for each alternative were not supplied; do not retroactively claim AWS DMS, Aurora or Terraform.

**New scope (planned):** Inventory Oracle 19c source/redo and network prerequisites; compare RDS PostgreSQL vs Aurora PostgreSQL cost/fit; use an AWS-supported schema assessment/conversion workflow; remediate unsupported SQL/PLSQL; load via AWS DMS and then validate CDC. Terraform provision networks/IAM/target; monitor DMS/task and database metrics in CloudWatch; document recovery, data validation, cutover and rollback.

### AWS acceptance gates
- [ ] Architecture, target choice, pricing/quotas, secure networking and rollback plan recorded before provisioning.
- [ ] Terraform AWS apply/validate/destroy results published with secret-safe logs.
- [ ] Schema conversion assessment, incompatibility list and functional validation captured.
- [ ] DMS Full Load + CDC insert/update/delete, SCN/log prerequisites and task lag demonstrated.
- [ ] Source/target counts, key aggregates and sampled transactions reconciled at a defined consistency point.
- [ ] Interruption/restart, CDC convergence, cutover and rollback rehearsal measured and documented.
- [ ] CloudWatch alerts, access restrictions, key/secret handling, and actual costs/teardown recorded.

Do not treat a plan, a service console screenshot or a successful DMS task state as proof of database/application correctness.

---

## Phase 12 — Integrated Capstone

**Focus:** Integrate the platform: architecture, infrastructure code, configuration automation, database CI/CD, monitoring, security, backup/recovery, HA/DR, CDC, testing, runbooks, troubleshooting records, demo, and GitHub portfolio.

### Done when
- The reproducible portions of the platform can be rebuilt from the repository by following the README/runbooks.
- Final architecture diagram and operational runbooks are committed.
- A recorded demo walks through provisioning, database change deployment, monitoring, and recovery/failure handling.
- Every component can be explained, including why it was selected and what trade-offs were made.

---

## Phase II — Advanced Platform Engineering

**Starts only after Phase 12 is complete.**

**Focus:** GitLab CI/CD, HashiCorp Vault, advanced Ansible, REST/API automation, Oracle 26ai Vector Search, Oracle Graph, MCP, tool calling, AI diagnostics, agentic workflows, human-in-the-loop approval, policy enforcement, evaluation/tracing, and guardrails.

Agentic automation is built on top of a working, monitored platform rather than being used as a substitute for platform fundamentals.

---

# Phase Completion Record

Each phase must include a completion record.

```markdown
## Phase Completion Record

Status: Not Started / In Progress / Complete
Started:
Completed:

### What I built
-

### What failed
-

### Root cause
-

### How I fixed it
-

### Validation performed
-

### Skills demonstrated
-

### Evidence
- Pull request:
- Scripts:
- Screenshots:
- Runbook:
- Architecture update:

### Interview story
-
```

---

# Project Operating Rules

1. **Learn → Build → Prove.**
2. Oracle/database-platform relevance must be visible throughout the project.
3. Nothing is claimed as completed until it is tested and documented.
4. Failures and troubleshooting are engineering evidence and should be documented.
5. Never commit passwords, private SSH keys, API keys, cloud secrets, Oracle credentials, wallets, or sensitive Terraform state.
6. Prefer reproducible infrastructure/configuration over undocumented manual changes.
7. Use feature branches and pull requests rather than treating `main` as a scratch branch.
8. Control cloud cost deliberately; temporary resources should have explicit teardown procedures.
9. Finish the core platform before expanding into advanced AI/agentic automation.
10. The goal is not tool accumulation. Every tool must support provisioning, operating, securing, recovering, monitoring, or automating the database platform.

---

# Career Progression

```text
Oracle DBA
    ↓
Oracle Database Engineer
    ↓
Database Automation / Platform Engineer
    ↓
Advanced Database / Data Platform Engineering
    ↓
Architecture
```

This roadmap is the controlling baseline. Changes discovered during implementation should be made deliberately through versioned Git commits/pull requests rather than repeatedly redesigning the project from scratch.
