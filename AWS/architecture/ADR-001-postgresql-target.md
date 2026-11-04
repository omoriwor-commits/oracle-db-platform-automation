# ADR-001 — Initial AWS PostgreSQL migration target

**Date:** 2026-10-22  
**Status:** Proposed; implementation decision pending cost and compatibility checks  
**Project:** Oracle Database Platform Automation

## Context
The existing roadmap includes AWS DMS Full Load + CDC and schema conversion from an Oracle 19c source to PostgreSQL. It alternates between describing PostgreSQL generically and Aurora PostgreSQL as the target. The 2023 Oracle EC2/RDS for Oracle migrations are separate, completed user-confirmed historical work.

## Proposed decision
Use **Amazon RDS for PostgreSQL** as the first AWS modernization target for a small, short-lived independent implementation. Keep **Aurora PostgreSQL-Compatible Edition** as a subsequent optional comparative extension. This is a proposed technical choice, **not an implemented database**.

## Rationale
- A conventional RDS PostgreSQL instance offers a narrower initial operational surface to validate schema conversion, full load, CDC, migration acceptance and teardown.
- It complements the previous independent RDS for Oracle experience without asserting that those migrations used DMS or SCT.
- Aurora remains a valid target option, but must be evaluated for actual pricing, instance availability, supported engine versions and required features.

## Decisions still required before resource creation
1. Confirm Oracle 19c source engine, edition, CDB/PDB, connectivity and selected non-sensitive sample schema.
2. Compare current RDS PostgreSQL versus Aurora pricing and service limits in the actual account/region. Record costs and quotas; do not assume free-tier eligibility.
3. Choose and record compatible source/target versions, AWS DMS version/mode, and the appropriate **AWS SCT or AWS DMS Schema Conversion** workflow based on current AWS support documentation.
4. Identify application SQL/PLSQL objects requiring manual conversion and regression testing.
5. Define source write freeze and rollback boundaries before cutover. DMS replication is not by itself a reversible cutover.

## Consequences and acceptance
No AWS architecture can be called implemented until Terraform apply/outputs, private connectivity, least-privilege tests, target access, resource inventory and cleanup/destroy have been observed and logged. No migration can be called validated until schema-object testing, full-load reconciliation, CDC replay, lag/failure observations, and cutover/rollback evidence pass.

## References
- [Master roadmap](../../Oracle-Database-Platform-Automation/ROADMAP.md)
- [AWS implementation runbook](../runbooks/oracle-to-postgresql-dms-sct-implementation.md)
- [Migration validation matrix](../validation/aws-migration-acceptance-matrix.md)
- [Cost/security readiness](../runbooks/aws-infrastructure-security-cost-readiness.md)
