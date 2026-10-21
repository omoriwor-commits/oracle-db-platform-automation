# AWS

AWS is a **co-priority planned cloud implementation track alongside OCI** of [Oracle Database Platform Automation](../Oracle-Database-Platform-Automation/ROADMAP.md). New AWS modernization implementation evidence has not yet been added to this project. Historical Oracle EC2/RDS migration practice is separately documented.

The planned scope includes Terraform-based VPC/private subnets/IAM/KMS/secrets, RDS/Aurora PostgreSQL target evaluation, Oracle schema assessment/conversion, AWS DMS Full Load + CDC, data reconciliation, CloudWatch, failure/restart and cutover/rollback tests. Keep prior EC2/RDS for Oracle experience distinct.

## Earlier Oracle migration experience

- [Oracle 19c migration to AWS: 2023 practice reference](runbooks/oracle-19c-aws-migration-2023.md) preserves syntax used in my independent on-premises-to-EC2 and EC2-to-RDS migration practice in 2023, with corrections for reuse.
- The historical practice is separate from the planned DevOps extension. Publishing corrected notes does not constitute a new deployment or a fresh execution test. Individual method outcomes and historical transcripts are identified separately in the reference.
