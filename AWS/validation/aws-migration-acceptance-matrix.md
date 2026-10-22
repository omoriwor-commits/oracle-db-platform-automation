# AWS Oracle-to-PostgreSQL migration — acceptance and evidence matrix

**Status: planned / not executed.** Every row starts unverified. Do not replace actual run evidence with expected results.

| Gate | Test and pass criterion | Retained evidence | Status |
|---|---|---|---|
| Source inventory | Version, PDB/schema scope, objects, sizing and baseline approved | Sanitized inventory + timestamps | Not run |
| Architecture/security | Private endpoints, approved CIDRs, least privilege, encryption and logging verified | Redacted Terraform plan, access tests | Not run |
| Budget/teardown | Budget alert configured, estimated cost approved, destroy procedure documented | Budget proof, plan, teardown checklist | Not run |
| Schema assessment | Incompatible objects enumerated and assigned remediation | SCT/DMS Schema Conversion report | Not run |
| Schema apply | Target DDL applies cleanly; invalid/unsupported objects resolved or excepted | DDL and automated test output | Not run |
| Conversion semantics | Critical Oracle SQL/PLSQL logic passes defined input/output and negative tests | Test scripts and result diffs | Not run |
| Endpoints | DMS source/target tests succeed through approved network path | DMS endpoint test output | Not run |
| Full load | All selected tables load; counts and keyed comparisons meet declared tolerance | DMS statistics and reconciliation | Not run |
| CDC | Controlled INSERT/UPDATE/DELETE and transaction cases converge in target | Source/target queries, checkpoints, lag | Not run |
| Schema/key consistency | PK/FK/index/sequence/constraint expectations verified | DDL/object catalog comparison | Not run |
| Failure/restart | DMS task interruption/restart recovers without unexplained loss or duplicate effects | Timeline, task logs, reconciliation | Not run |
| Observability | CloudWatch alerts for relevant lag/errors/resource health are exercised | Alarm configs, test alert output | Not run |
| Cutover rehearsal | Write freeze, final sync, application smoke tests and abort criteria executed | Cutover transcript and decision log | Not run |
| Rollback rehearsal | Recovery boundary and source-of-truth handling tested | Rollback decision and outcome | Not run |
| Teardown | Temporary resources removed; no unintended billable resources remain | Terraform destroy output, resource/cost check | Not run |

## Evidence-record template
- **Run ID / UTC timestamp / local time zone:**
- **Operator / repo commit SHA / AWS region:**
- **Source and target engine/release / object scope:**
- **Tool and method (SCT vs DMS Schema Conversion; DMS task mode):**
- **Preconditions / source backup / rollback point:**
- **Command/action and exit status:**
- **Expected behavior / actual behavior / delta:**
- **Sensitive-output redaction check:**
- **Artifacts (path + SHA-256):**
- **Unresolved limitations / remediation issue:**
- **Verifier and acceptance decision:**

### Evidence policy
No fabricated durations, zero data loss claims, full compatibility claims, or successful cutover claims. Document any warning, unsupported mapping, blocked budget, unexpected row difference or untested rollback.
