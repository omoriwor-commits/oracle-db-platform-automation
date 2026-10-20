# Oracle Database Platform Engineering

Oracle database lab portfolio focused on **migration and GoldenGate replication** across Oracle Cloud Infrastructure (OCI), Azure and local VirtualBox environments, with RAC, Data Guard and RMAN lab work and a DevOps automation project in progress.

These are independent hands-on lab projects. The current goal is to bring the strongest existing Oracle DBA work into one repeatable, version-controlled **Oracle Database Platform Automation** platform using DevOps practices.

## Migration path

I took one Oracle workload through three GoldenGate 26ai migrations:

```text
Oracle 19c / OL 7.9 (on-prem)
   | 1. Upgrade + OS migration (remote capture, local apply)
   v
Oracle 26ai / OL 9.8 (on-prem)
   | 2. On-prem to cloud (local capture, remote apply)
   v
Oracle 26ai / OCI Compute
   | 3. Cross-cloud, heterogeneous (Azure hub: remote capture, remote apply)
   v
SQL Server 2022 / Azure
```

## Engineering projects

### Migration 1 — Oracle 19c → 26ai Upgrade, OS Migration & GoldenGate Replication

[Migration architecture and implementation notes](https://github.com/omoriwor-commits/enterprise-data-platform-labs/tree/main/migrations/oracle-19c-to-26ai-goldengate)

```text
Oracle 19c / PRODBHR (Oracle Linux 7.9)
   -> Remote Integrated Extract EXT19C
   -> GoldenGate trail
   -> Integrated Replicat REP26AI
   -> Oracle AI Database 26ai / PDB23AI (Oracle Linux 9.8)
```

**Engineering decision:** Run GoldenGate off-box on the newer Oracle Linux environment rather than install GoldenGate 26ai on the older source OS. Tested DML (INSERT, UPDATE, DELETE) and DDL (CREATE TABLE, DROP TABLE) replication. Sanitized configuration and test output will be added to the project repository.

### Migration 2 — Oracle 26ai On-Premises to OCI Migration & GoldenGate Replication

[Implementation and rerun playbook](https://github.com/omoriwor-commits/enterprise-data-platform-labs/tree/main/migrations/oracle-26ai-to-oci-goldengate)

Local Oracle 26ai (OL 9.8) → self-managed Oracle 26ai on OCI Compute (OL 9.8). I used **RMAN and Data Pump for the initial load**, then GoldenGate 26ai for CDC with **local capture at the source-side GoldenGate tier and remote apply to OCI**. I tested DML (INSERT, UPDATE, DELETE) and DDL (CREATE TABLE, DROP TABLE) replication, and confirmed each change reached the OCI target.

```text
LOCAL LAB / OL9.8                           OCI COMPUTE / OL9.8
Source Oracle 26ai                          Self-managed Oracle 26ai
  + GoldenGate source-side tier                 ^
    Extract: LOCAL capture                     |
    Replicat: REMOTE apply --------------------+
Initial load: RMAN / Data Pump
```

### Migration 3 — Oracle 26ai (OCI) to Azure SQL Server 2022: Heterogeneous Cross-Cloud Migration & GoldenGate Replication

[Enterprise Multi-Cloud Database Platform Lab](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab)

```text
OCI Oracle 26ai / PDB23AI
         |
         | Oracle Net over private OCI-Azure IPsec/BGP connection
         v
Azure GoldenGate hub (OL9.8)
   DEP1: EXTORA — REMOTE Integrated Extract / source trail ea
   MSSQLDEP: REPSQL — REMOTE apply via SQL_TGT ODBC
         |
         v
Azure SQL Server 2022 / OGGTargetDB.HOLA.FOX
```

I completed the OCI-to-Azure implementation and verified INSERT, UPDATE and DELETE replication through GoldenGate into Azure SQL Server 2022. The archived September checkpoint records earlier VPN/BGP, Extract, trail, SQL Server ODBC and Replicat preparation work; final sanitized target-side validation output will be published after the rerun. [Implementation incidents and resolution history](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/docs/project-history/project-history-and-troubleshooting.md) preserve the obstacles encountered.

### RMAN backup and recovery

Full and incremental backup, restore, and point-in-time recovery scenarios. Reusable commands and sanitized validation records are being consolidated.

### Oracle RAC / ASM — two-node local lab

[Two-node RAC build and troubleshooting runbook](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/docs/runbooks/oracle-rac/oracle19c-2node-rac-build-and-troubleshooting.md) — full Oracle 19c Grid, ASM and RAC database build, tested and reused.

[Oracle 26ai two-node RAC build runbook (tested; open Verify items listed)](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/docs/runbooks/oracle-rac/oracle26ai-2node-rac-build-runbook.md) — two-node 26ai build and functional validation completed October 19, 2026; remaining configuration and compatibility checks are tracked in the runbook.

[October 18, 2026 — 26ai node 2 root-script VM freeze and VT-x investigation](Oracle-Database-Platform-Automation/incident-reports/2026-10-18-rac26-node2-root-script-vm-freeze.md)

[Earlier 19c node startup investigation](Oracle-Database-Platform-Automation/incident-reports/2026-10-rac-node2-startup-investigation.md)

The former 19c VMs were retired. The new 26ai cluster runs RAC1/RAC2 with RACPDB1 READ WRITE on both nodes. Functional validation includes archiving, SCAN connection distribution, new connections while RAC2 is stopped, and service restoration after restart. The SCAN availability test is user-confirmed; its raw transcript remains to be published. The older 19c incident retains its original, unconfirmed root cause.

Operational code: [RAC health-check Python script](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/scripts/oracle-rac/rac_health_check.py). Revision `2026-10-19.3` was live-tested as grid on October 19 at 10:46 CDT, collecting database and ASM checks with zero critical findings and four warnings. [Health evidence](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/docs/evidence/oracle-rac/2026-10-19-rac26-health-check-v3.md) records alert-history and kernel/RU review items; HugePages remains unconfigured.

### Oracle Data Guard — health-check automation

[Data Guard health-check Bash script](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/scripts/dataguard/dataguard_health_check.sh) implements database role detection and checks for redo transport, apply lag, archive gaps, archive destinations, and broker connectivity. Published as an operational command pack; full lab validation remains pending.

## Featured project — Oracle Database Platform Automation

[Architecture, phases, and engineering roadmap](Oracle-Database-Platform-Automation/README.md)

```text
Git / GitHub
     |
     v
Bash / Python -> GitHub Actions -> Terraform / Ansible (planned integration)
     |
     +-- Oracle 19c / 23ai / 26ai databases
     +-- GoldenGate capture and replication
     +-- RAC / ASM and Data Guard
     +-- RMAN backup, restore and recovery
     |
     v
Monitoring, validation, runbooks, and recovery testing
```

**Current platform:** Local VirtualBox hosts with Oracle 19c, Oracle 23/26ai, and GoldenGate 26ai available for further testing. The cloud environments have since been shut down; their implementation records remain in the linked project repositories.

## DevOps integration roadmap

| Capability | Position |
|---|---|
| Local Oracle 19c, 23/26ai and GoldenGate labs | Available for continued validation |
| Oracle migrations and RMAN recovery | Completed lab work; evidence consolidation underway |
| OCI–Azure VPN, Extract, and SQL connectivity | Completed and validated |
| SQL Server Replicat end-to-end apply | Completed; final apply logs to be archived during rerun |
| Oracle health-check automation | RAC Python revision 2026-10-19.3 live-tested on 26ai; Data Guard validation tracked separately |
| RMAN automation and recovery controls | Planned integration |
| Terraform / Ansible infrastructure automation | Planned |
| Database CI/CD with GitHub Actions | Planned |
| Prometheus / Grafana monitoring | Planned |

## Technical knowledge archive

The [Oracle Database Engineering Knowledge Base](KNOWLEDGE-BASE.md) organizes reusable architecture decisions, procedures, incident analysis, and engineering experience.

## Repository guide

| Location | Material |
|---|---|
| [Oracle Database Platform Automation](Oracle-Database-Platform-Automation/) | Integrated architecture, roadmap, and incident reports |
| [Oracle DBA](Oracle-DBA/) | [Operational runbooks](Oracle-DBA/runbooks/README.md): Clusterware, OCR/OLR, RMAN backup automation, daily/weekly health checks and SQL Tuning Advisor; each lists its tested or pending status |
| [GoldenGate](GoldenGate/) | Replication references |
| [OCI](OCI/) / [Azure](Azure/) / [AWS](AWS/) | Cloud engineering references |
| [DevOps](DevOps/) | Git, SSH, and reusable shell tooling |

### Related project repositories

- [Enterprise Multi-Cloud Database Platform Lab](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab) — OCI–Azure GoldenGate and SQL Server integration.
- [Enterprise Data Platform Labs](https://github.com/omoriwor-commits/enterprise-data-platform-labs) — Oracle 19c–26ai migration.
- [NGINX DevOps Project](https://github.com/omoriwor-commits/nginx-devops-project) — Docker, Kubernetes, Docker Hub, and GitHub Actions CI/CD.

## Publication practice

Code, configuration examples, logs, and screenshots are sanitized before publication. Sensitive credentials, private keys, wallet files, and confidential data must not be committed.
