# Oracle 19c → PostgreSQL: schema conversion and AWS DMS implementation runbook

**Status: PLANNED — no DMS task, schema conversion, PostgreSQL target, or Terraform deployment is claimed.**  
**Scope:** independent implementation, Oracle 19c to Amazon RDS for PostgreSQL (proposed); Aurora PostgreSQL-compatible edition is a later optional extension.

## 0. Approval, budget and source protection
- Confirm authorized AWS account, region, budget alarm, spending ceiling, credentials, and teardown owner.
- Record OCI/AWS workload boundaries; the 2023 EC2/RDS Oracle migration is historical and not this run.
- Capture current vendor documentation for engine/version compatibility, supported conversion path, DMS prerequisites, feature limits and estimated costs.
- Protect source and database credentials. No secrets, private endpoint details, wallet or dumps in Git.
- Create a dated execution record with operator, commit SHA, timestamps, commands, sanitized logs, criteria and rollback decisions.

## 1. Baseline Oracle 19c source
- Record database/host release and edition, CDB/PDB/container, time zone, character set, size, tables, keys, indexes, sequences, constraints, views, stored code and object status.
- Record a repeatable logical validation dataset, referential integrity checks and representative SQL/PLSQL behaviors.
- Verify Oracle source privileges and redo/archived-log/supplemental logging configuration **against the chosen DMS capture mode**; requirements vary with source type, task and LogMiner/Binary Reader configuration.
- Preserve backup/recovery point and record source baseline SCN where applicable. Do not enable source-affecting settings without an explicit review.

## 2. Schema assessment and conversion
- Choose **AWS SCT or DMS Schema Conversion** after checking current supported source/target engine combinations and tooling availability; they are not interchangeable in every workflow.
- Produce assessment report: automatically convertible objects, manual action items, incompatible data types/functions, triggers, sequences, stored procedures, packages, grants and extensions.
- Convert only a non-sensitive, approved schema. Store version-controlled resulting DDL and an exception/remediation register.
- Review Oracle-specific semantics: NUMBER precision, empty-string/NULL behavior, DATE/TIMESTAMP and time zone, case folding, sequences/identity, transactional behavior, exception handling, SQL functions, and PL/SQL versus PL/pgSQL differences.
- Apply schema changes to the isolated target, validate object creation and tests. AI-generated conversions require separate human review and executable regression tests.

## 3. Provision the AWS target and DMS path
- Terraform plan for VPC, private subnets, routing/security groups, IAM, encryption, secrets access, target database and relevant DMS resources; enforce private database connectivity.
- Use least privilege and narrowly scoped connectivity. Confirm DMS service network access to both endpoints, including on-prem/hosted Oracle source path if applicable.
- Confirm RDS target version, extensions, parameter values, backups, retention, storage and operational monitoring requirements.
- Verify Terraform backend controls and plan scanning before apply. Capture plan, approval, apply, resource inventory and teardown evidence without publishing secrets.

## 4. Initial load and CDC
- Create and test DMS Oracle source and PostgreSQL target endpoints.
- Define table mappings/selection rules and task settings for **Full Load + CDC**, including start position/consistency, handling of preexisting target tables, LOBs, DDL limitations, error handling and target constraints.
- Record task start timestamps and progress. Confirm initial table loads before asserting completion.
- Generate controlled source INSERT, UPDATE and DELETE cases, including transactions and restart scenarios. Observe target changes and latency metrics.
- Review DMS task logs, validation results and failed records. DMS CDC is not a substitute for schema conversion, procedural code migration or application-level validation.

## 5. Reconciliation, resilience and cutover
- Apply the linked [acceptance matrix](../validation/aws-migration-acceptance-matrix.md).
- Compare baseline and target row counts, keyed records, aggregate checksums or scoped hashes, data types, constraints, sequences, stored-code test results and application queries at an agreed consistency point.
- Test interruption/restart only after backup and rollback review. Capture task state, redo availability, lag, duplicates/errors and eventual convergence.
- Design controlled write freeze, final CDC catch-up, application connection switch and smoke tests. Define abort criteria before any change.
- Document rollback feasibility, source-of-truth ownership and any writes made to the new target. Do not promise automatic reverse replication.

## 6. Completion, evidence and cleanup
- Keep sanitized assessment output, Terraform references, DMS task config (redacted), migration reports, DDL, test cases, reconciliation and cutover/rollback rehearsal records.
- Revoke temporary privileges and remove database links, test credentials and disposable infrastructure through approved teardown; verify billable resources are gone.
- Update the tracker from Planned → Implemented only after the relevant checks actually pass. Preserve blocked and failed tests as evidence.

## Project links
- [Architecture decision](../architecture/ADR-001-postgresql-target.md)
- [Acceptance matrix](../validation/aws-migration-acceptance-matrix.md)
- [AWS cost and infrastructure readiness](aws-infrastructure-security-cost-readiness.md)
- [Historical Oracle EC2/RDS reference — separate work](oracle-19c-aws-migration-2023.md)
