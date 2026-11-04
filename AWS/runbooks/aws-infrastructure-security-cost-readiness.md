# AWS modernization — infrastructure, security and cost readiness

**Status: pre-deployment checklist (not evidence of deployed AWS resources).**

## Account and funding gate
- [ ] Confirm authorized account, region, billing owner, AWS service quotas and actual eligibility/pricing.
- [ ] Record expected operating time and estimated costs for RDS PostgreSQL, DMS capacity/replication, data transfer, storage, monitoring, snapshots and network services.
- [ ] Set AWS Budgets alerts and spend limit decisions; budgets are notifications and not guaranteed hard spending caps.
- [ ] Identify costly idle components, scheduled teardown and owner.
- [ ] Document whether the historical 2023 EC2/RDS resources are absent; never assume they are running.

## Terraform and state
- [ ] Use isolated folders/workspaces and explicit AWS provider version constraints.
- [ ] Create reusable network/security, database and DMS modules; separate source/target configuration from credentials.
- [ ] Protect backend state with encryption, least-privilege access, versioning/recovery and supported locking controls; no state or secret-bearing plan files in Git.
- [ ] Run fmt, validate, TFLint and an IaC/security scan; review plan cost and permissions before apply.
- [ ] Capture approved apply and destroy evidence; verify deletion of billable resources afterward.

## Network
- [ ] Design VPC, subnet groups across suitable AZs, routing, approved security groups, DNS, and an authorized path from Oracle source to DMS.
- [ ] Prefer private RDS endpoint and tightly scoped ingress/egress; no public database exposure by default.
- [ ] Validate network reachability for DMS to source/target without exposing listener credentials.
- [ ] Record transport encryption compatibility and certificate verification settings.

## Identity and data protection
- [ ] Scope IAM roles to required resources/actions, including DMS service permissions and secrets retrieval.
- [ ] Select KMS-backed encryption where supported and document rotation/recovery considerations.
- [ ] Keep credentials in protected secret storage; review database-level grants independently of AWS IAM.
- [ ] Avoid real personal/regulated data in independent tests; sanitize output and prevent publishing host IDs/IPs or credentials.
- [ ] Establish logging, metric retention, audit trail and alarm routing.

## Operational handoff
- [ ] Backup/snapshot retention and point-in-time recovery requirements reviewed.
- [ ] Maintenance windows, engine upgrades, DMS error handling and restart procedure documented.
- [ ] Migration acceptance matrix assigned to a tester; cutover owner and stop conditions defined.
- [ ] Resource inventory, cleanup commands, post-destroy cloud-billing check and open findings documented.

See [architecture decision](../architecture/ADR-001-postgresql-target.md), [implementation runbook](oracle-to-postgresql-dms-sct-implementation.md), and [acceptance matrix](../validation/aws-migration-acceptance-matrix.md).
