# Oracle Database Platform — Master Roadmap

**Version:** 1.1  
**Status:** Baseline / controlling roadmap  
**Target role:** Oracle Database Automation / Platform Engineer

> **Guiding question for every phase:**  
> How does this help me provision, operate, secure, recover, monitor, or automate a database platform?

**Pacing:** Phases advance by competency, not by calendar. Each phase is complete only when its **Done when** criteria are met and documented.

## Execution Order (controlling)

Phase numbers follow the DevOps syllabus. They are **not** the build order.
This section is the single controlling execution order; README.md links here
rather than repeating it. Pacing is by competency: a stage is complete only when its
**Done when** criteria are met and evidence is committed.

### Stage 1 — Core Platform v1 (target: ~8 weeks)

| Order | Target week | Work | Phase | Status |
|---|---|---|---|---|
| 1 | 1 | Close Phase 0: protect `main`, budget alerts, lab inventory, security/naming/documentation standards (repo rename done Oct 2026) | 0 | In progress |
| 2 | 1 | Maintain completed 26ai RAC build/functional-validation evidence; resolve compatibility and hardening follow-ups. Preserve the retired 19c incident separately with its unconfirmed root cause | 10B | Build and functional validation complete; follow-ups in progress |
| 3 | 2 | Extend existing Oracle health checks with scheduling, retained evidence and automated quality checks; all work via PRs | 1–2 | RAC Python 2026-10-19.3 live-tested; scheduling/integration and Data Guard validation tracked separately |
| 4 | 3–4 | Rebuild GoldenGate 26ai pipeline (OCI Oracle → Azure SQL Server): DML, row-count validation, lag, restart | 11 | Planned |
| 5 | 5 | Terraform OCI VCN + compute modules; remote state in Object Storage; clean apply/destroy | 4–5 | Planned |
| 6 | 6 | Ansible configures the fresh server and installs Oracle with no manual steps; idempotent rerun | 6 | Planned |
| 7 | 7 | GitHub Actions: ShellCheck, `terraform validate` + TFLint, ansible-lint on every PR | 3 (partial) | Planned |
| 8 | 8 | Grafana dashboard (availability, tablespace, backup status); 5-minute recorded demo | 9A (partial), 12 (partial) | Planned |

**Stage 1 done when:** a new OCI server can be provisioned, configured and
health-checked from this repository, every PR runs the pipeline, the
GoldenGate pipeline has published evidence, and a recorded demo exists.

### Stage 2 — Platform Operations

1. Database CI/CD with SQLcl Liquibase and an ephemeral Oracle Database Free test database (Phase 3, full)
2. RMAN automated restore testing and recovery reports (Phase 9C)
3. Security hardening and secrets via Vault (Phase 9B)
4. Data Guard automation, switchover and failover tests (Phase 10A)
5. Rerun and document migrations 1 and 2: 19c → 26ai and on-premises → OCI (Phase 11)

### Stage 3 — Containers and Integration

1. Docker: Oracle Database Free container, Trivy scanning (Phase 7)
2. Kubernetes + Helm for supporting services (Phase 8)
3. Integrated capstone: full rebuild from runbooks, final architecture, demo (Phase 12)

### Stage 4 — Extensions (only after Phase 12)

AWS extension, then Phase II advanced platform engineering and agentic AI.

**Certifications:** OCI Architect Associate after Stage 1 week 5;
HashiCorp Terraform Associate after Stage 1.

**Learning baseline:** Coding Macaw AI-Powered DevOps syllabus (Linux, Git/GitHub, CI/CD, AWS, Terraform, Azure, Docker, Kubernetes, Ansible, SRE, DevSecOps), applied to database platform engineering.

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

**Focus:** OCI as the primary cloud: IAM, VCN, subnets, routing, NSGs/security, compute, storage, and OCI database architecture. AWS is supporting knowledge. Azure is retained for the existing environment and Phase 11.

**Certification objective:** OCI Architect Associate at the end of Phase 4 or Phase 5, after building the components hands-on.

### Done when
- A VCN with public/private subnets, controlled administrative access, and NSGs is built manually in OCI.
- IAM policies follow least privilege.
- The design is documented with an architecture diagram explaining each choice.
- Equivalent AWS concepts can be explained, including VPC, security groups, and IAM.

---

## Phase 5 — Terraform

**Focus:** Infrastructure as code using the OCI provider: VCN/subnets/security, compute/storage, variables/outputs, remote state, reusable modules, dev/test environments, validation, and security scanning.

### Done when
- `terraform apply` builds the dev environment from a clean starting point.
- `terraform destroy` removes disposable resources cleanly.
- Terraform state is stored remotely in OCI Object Storage using the appropriate OCI backend with locking and bucket versioning enabled.
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
