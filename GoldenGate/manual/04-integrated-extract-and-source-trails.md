# 04 — Integrated Extract and Source Trails

**Scope:** Oracle GoldenGate 26ai Microservices and Oracle source databases. Identifiers (`EXTLAB`, `gg_source`, `ea`, `HR.EMPLOYEES`) are placeholders. See the separately documented [Oracle 19c → 26ai migration project](https://github.com/omoriwor-commits/enterprise-data-platform-labs/tree/main/migrations/oracle-19c-to-26ai-goldengate) for recorded `EXT19C` remote integrated capture and `REP26AI` apply.

**Prerequisite:** [03 — Oracle Database Preparation](03-oracle-database-preparation.md), including archived redo, supplemental logging, appropriate source privileges, and an approved capture/initial-load boundary.

## 1. Capture architecture

Integrated Extract interacts with Oracle's integrated capture infrastructure to read logical changes from database redo and write local GoldenGate trail files. Distribution and apply are separate components.

```text
Oracle redo -> integrated database capture -> Integrated Extract
           -> local trail (ea#########) -> Distribution Path (05)
           -> target trail -> Replicat (06)
```

A RUNNING Extract does not establish that transport completed or target data is correct. Registration, trail writes, transport delivery, and target apply require distinct evidence.

## 2. Preflight checklist

| Check | Verification | Operational risk |
|---|---|---|
| Supported versions | Oracle certification for source database and exact GoldenGate release | Capture support and commands vary |
| Database scope | `SHOW CON_NAME`, DB alias/service, `DBLOGIN` | Wrong CDB/PDB or mining database |
| Redo/logging | 03 checks and `INFO TRANDATA` | Incomplete logical changes or lost redo |
| Capture privileges | Version-specific capture roles/procedures | Blanket DBA privileges are not appropriate |
| Deployment | Secured endpoint and authorized operator | Wrong deployment changes |
| Table selection | Approved `TABLE` list and exclusions | Capturing unintended objects |
| Start position | SCN/CSN and initial-load plan | Duplicate or missing transactions |
| Trail storage | Data home, available space, purge/retention | Capture interruption or irrecoverable gaps |

**Database-version caveat:** Oracle Database 19c and Oracle AI Database 26ai have different supported capture privilege-granting approaches. Do not universally prescribe `DBMS_GOLDENGATE_AUTH` or `GRANT DBA`; validate the target database release and Oracle guidance.

## 3. Read-only source inspection

```sql
SHOW CON_NAME;
SHOW USER;

SELECT name, db_unique_name, database_role, open_mode, log_mode,
       force_logging, supplemental_log_data_min
FROM v$database;

SHOW PARAMETER enable_goldengate_replication;

SELECT capture_name, status
FROM dba_capture
ORDER BY capture_name;
```

Before registration, zero rows in `DBA_CAPTURE` can be expected. After registration, verify the intended capture exists in the correct source/mining database. This does not prove Extract has emitted trail records. Retain necessary redo for Extract's recovery checkpoint and other database recovery consumers.

## 4. Connect through Admin Client

```bash
cd "$OGG_HOME/bin"
./adminclient
```

Authenticate to the correct secured GoldenGate deployment through a supported method without exposing a service password in shell history. Establish the database session using a configured credential alias:

```text
DBLOGIN USERIDALIAS gg_source DOMAIN OracleGoldenGate
```

This command authenticates to the **source database**, not to the GoldenGate administration service. Confirm the alias targets the intended source service and PDB before changing registration.

## 5. Register Integrated Extract

```text
REGISTER EXTRACT EXTLAB DATABASE
```

Integrated Extract registration precedes the `ADD EXTRACT` operation. Inspect the Admin Client response and database capture metadata.

For Oracle multitenant topologies, Oracle documents `REGISTER EXTRACT ... DATABASE CONTAINER (...)` options. Root, PDB and remote/downstream mining configurations are not interchangeable. Apply only the clause validated for the topology.

Reference: [REGISTER EXTRACT](https://docs.oracle.com/en/database/goldengate/core/26/gclir/register-extract.html).

## 6. Create Extract and local trail

```text
ADD EXTRACT EXTLAB, INTEGRATED TRANLOG, BEGIN NOW
ADD EXTTRAIL ea, EXTRACT EXTLAB, MEGABYTES 200
```

| Directive | Purpose | Important qualification |
|---|---|---|
| `ADD EXTRACT` | Creates a managed Extract | Creation is not evidence of captured transactions |
| `INTEGRATED TRANLOG` | Selects Oracle integrated capture | Requires prior successful registration |
| `BEGIN NOW` | Chooses initial source read boundary | Not a safe default for an already populated target |
| `ADD EXTTRAIL ea` | Binds the local trail prefix | Physical files appear after Extract writes data |
| `EXTRACT EXTLAB` | Identifies the owning Extract | Do not bind competing Extracts to one trail |
| `MEGABYTES 200` | Sets maximum size of each trail file | Size according to tested workload/retention |

Sequence-based trail files use the configured prefix and GoldenGate-generated sequence, for example `ea000000001`. Confirm naming and sequence length for the actual build.

## 7. Parameter configuration

```text
EXTRACT EXTLAB
USERIDALIAS gg_source DOMAIN OracleGoldenGate
EXTTRAIL ea
TABLE HR.EMPLOYEES;
```

`EXTRACT` identifies the process; `USERIDALIAS` references a credential store entry; `EXTTRAIL` must match the registered trail prefix; `TABLE` defines captured objects. In a multitenant environment the table may require a PDB-qualified form such as `PDB1.HR.EMPLOYEES` depending on the database connection and registration.

Manage parameter changes through Administration Service or the supported Admin Client editor. Preserve a previous version and assess downstream table mappings and initial-load impact before changing object scope.

## 8. Start and verify source capture

```text
START EXTRACT EXTLAB
INFO ALL
INFO EXTRACT EXTLAB, DETAIL
INFO EXTRACT EXTLAB, SHOWCH
STATS EXTRACT EXTLAB
INFO EXTTRAIL *
```

Verify supplemental logging separately after database login:

```text
DBLOGIN USERIDALIAS gg_source DOMAIN OracleGoldenGate
INFO TRANDATA HR.EMPLOYEES
```

Inspect trail storage through the **actual deployment data directory**, not an assumed default:

```bash
# OGG_DATA_HOME is documented for MA trail artifacts; ensure it is set correctly.
printf 'Data home: %s\n' "$OGG_DATA_HOME"
df -hT "$OGG_DATA_HOME"
ls -lh "$OGG_DATA_HOME"
```

Oracle's default is `<deployment-location>/var/lib/data`, but deployments may use customized locations. Never mistake `$OGG_HOME` (installation home) for the trail data directory.

With an approved isolated test table, commit controlled INSERT, UPDATE and DELETE operations. Record matching Extract stats, report, trail sequence/RBA and checkpoints. A source that has no committed matching DML can correctly show zero operations. **Source capture validation does not prove target delivery or apply.**

## 9. Incident diagnostics

| Symptom | Check | First response |
|---|---|---|
| Registration failure | Database service/container, capture privileges, exact error | Identify cause before retrying |
| Extract ABENDED | Process report, error log, redo access, parameter syntax | Preserve log and recovery position |
| RUNNING with zero output | Source commit, TABLE selection, capture state | Test controlled committed source DML |
| No local trail | `EXTTRAIL` declaration/binding, path, disk permissions | Compare parameters to `INFO EXTTRAIL *` |
| Trail grows but target does not | Distribution/Receiver/Replicat status | Investigate next pipeline boundary |
| Increasing checkpoint lag | Long transactions, redo backlog, host/database resources | Inspect checkpoints and reports |
| Trail sequence missing | Purge policy, retained files, consumer positions | Preserve state and plan supported recovery |

Do not delete/re-register Extract, force a new capture position or remove trails merely to clear a process error. Such changes require a recovery and continuity plan.

## 10. Lab results

**Evidence pending:** Oracle documentation confirms the command forms below, but no command in this replacement was executed against a current 26ai deployment. Add sanitized results only after an actual lab run.

```text
Date/time and operator:
Source Oracle release / CDB-PDB:
GoldenGate release and deployment:
Capture topology (local, remote, downstream):
Registration output:
Credential alias (no secret):
Actual trail data directory:
Extract parameter file (redacted):
INFO EXTRACT and INFO EXTTRAIL output:
INFO TRANDATA output:
First trail sequence and RBA:
STATS after separately committed DML:
Report warnings/errors and corrective action:
Source capture outcome: VERIFIED / FAILED / NOT TESTED
```

## References

- [Add an Extract — Oracle 26ai](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/extract-add-primary-extract.html)
- [REGISTER EXTRACT](https://docs.oracle.com/en/database/goldengate/core/26/gclir/register-extract.html)
- [ADD EXTRACT](https://docs.oracle.com/en/database/goldengate/core/26/gclir/add-extract.html)
- [ADD EXTTRAIL](https://docs.oracle.com/en/database/goldengate/core/26/gclir/add-exttrail.html)
- [START EXTRACT](https://docs.oracle.com/en/database/goldengate/core/26/gclir/start-extract.html)
- [INFO EXTRACT](https://docs.oracle.com/en/database/goldengate/core/26/gclir/info-extract.html)
- [INFO TRANDATA](https://docs.oracle.com/en/database/goldengate/core/26/gclir/info-trandata.html)
- [INFO EXTTRAIL](https://docs.oracle.com/en/database/goldengate/core/26/gclir/info-exttrail.html)
- [Deployment Directories](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/deployment-directories.html)

**Next:** [05 — Distribution and Receiver Services](05-distribution-and-receiver-services.md).
