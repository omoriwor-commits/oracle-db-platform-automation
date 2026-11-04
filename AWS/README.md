# AWS

AWS is a **co-priority planned cloud implementation track alongside OCI** of [Oracle Database Platform Automation](../Oracle-Database-Platform-Automation/ROADMAP.md). New AWS modernization implementation evidence has not yet been added to this project. Historical Oracle EC2/RDS migration practice is separately documented.

The **proposed first implementation target is Amazon RDS for PostgreSQL**, subject to documented compatibility and cost review. Aurora PostgreSQL-Compatible Edition remains an optional subsequent extension. The architecture decision is proposed, not a deployed resource.

The planned scope includes Terraform-based VPC/private subnets/IAM/KMS/secrets, RDS/Aurora PostgreSQL target evaluation, Oracle schema assessment/conversion, AWS DMS Full Load + CDC, data reconciliation, CloudWatch, failure/restart and cutover/rollback tests. Keep prior EC2/RDS for Oracle experience distinct.

## AWS implementation readiness (documentation, not deployment)

- [ADR-001: PostgreSQL target decision](architecture/ADR-001-postgresql-target.md) — proposed RDS PostgreSQL target, Aurora alternative, outstanding checks.
- [Oracle-to-PostgreSQL DMS/SCT runbook](runbooks/oracle-to-postgresql-dms-sct-implementation.md) — source inventory, schema assessment, full load, CDC, resilience and cutover.
- [Migration acceptance and evidence matrix](validation/aws-migration-acceptance-matrix.md) — explicit not-run test gates and evidence template.
- [Terraform, security, cost and teardown readiness](runbooks/aws-infrastructure-security-cost-readiness.md) — pre-deployment checklist.

**Status:** All four documents are planning/acceptance artifacts. No DMS task, SCT conversion, RDS PostgreSQL target or Terraform apply is claimed as completed.

## Earlier Oracle migration experience

- [Oracle 19c migration to AWS: 2023 practice reference](runbooks/oracle-19c-aws-migration-2023.md) preserves syntax used in my independent on-premises-to-EC2 and EC2-to-RDS migration practice in 2023, with corrections for reuse.
- The historical practice is separate from the planned DevOps extension. Publishing corrected notes does not constitute a new deployment or a fresh execution test. Individual method outcomes and historical transcripts are identified separately in the reference.
