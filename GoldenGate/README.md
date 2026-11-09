# Oracle GoldenGate

My GoldenGate reference work and field guide.

- [GoldenGate 26ai Engineering Field Guide](manual/README.md): architecture, Extract, Replicat, monitoring, recovery and troubleshooting.
- [Six deployment methodologies](six-deployment-methodologies.md): process placement patterns and trade-offs.

My completed GoldenGate migrations are in [enterprise-data-platform-labs](https://github.com/omoriwor-commits/enterprise-data-platform-labs) (Migrations 1 and 2) and [enterprise-multicloud-database-platform-lab](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab) (Migration 3).

## Runbooks

- [GoldenGate 26ai Oracle-to-Oracle setup runbook (draft)](runbooks/goldengate26ai-oracle-to-oracle-setup-runbook.md) — single-hub Microservices deployment, Integrated Extract and Replicat, Data Pump initial load at SCN, validation and teardown.

## Verified local recovery and validation

- [19c to 26ai recovery runbook](runbooks/goldengate-19c-to-26ai-recovery-runbook.md) — November 7–8, 2026: retained-redo recovery, timezone correction, four mapped DDL operations, TEST1/FOX DML and logging checks; unresolved items remain explicit.
- [Incident report](../Oracle-Database-Platform-Automation/incident-reports/2026-11-07-08-goldengate-recovery-and-validation.md) — lab findings, diagnostic reasoning, validation counters and limits. Public editions use endpoint placeholders; raw evidence is retained separately.
