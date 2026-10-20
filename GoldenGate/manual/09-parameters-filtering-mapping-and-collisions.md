# 09 — Parameters, Filtering, Mapping and Collisions

> **Reference scope:** Oracle-documented procedures and illustrative examples. Lab results are recorded separately.
>
> **Reference scope:** Oracle-documented procedures and illustrative examples. Lab results are recorded separately.

## Scope and configuration controls

This page covers parameter-file management, directive scope, row filtering, column mapping, collision handling and safe table onboarding without transaction gaps.

## 1. What is a parameter file?

A GoldenGate process parameter file describes what a specific Extract or Replicat should capture/apply and how. A separate GLOBALS configuration can affect broader environment-level settings. In Microservices deployments, parameter/configuration files are normally associated with a deployment runtime home, rather than the installation binary home.

A commonly used deployment configuration location resembles:
`$DEPLOYMENT_HOME/etc/conf/ogg/`.

**Verify your installation's actual home and use supported administration interfaces.** Deployment directory layout varies; verify the actual runtime configuration home.

### Safe change-control sequence

1. Identify the exact Service Manager, deployment, process and current parameter version.
2. Record current process health, checkpoint and outstanding transactions.
3. Obtain change approval, impact window and application owner notification as appropriate.
4. Back up the **current** parameter file and record a redacted before/after diff.
5. Validate syntax and whether a directive affects all subsequent TABLE/MAP clauses.
6. Stop/restart only the processes the approved procedure requires.
7. Validate reports, capture/apply progress and source-versus-target rows.
8. Retain a precise rollback file plus position and recovery requirements.

**Never** publish real credentials, wallet contents or site-specific secrets embedded in copied configurations.

## 2. Understand scoped directives

Relevant DML-selection directives include:

```text
GETINSERTS
IGNOREINSERTS
GETUPDATES
IGNOREUPDATES
GETDELETES
IGNOREDELETES
GETTRUNCATES
IGNORETRUNCATES
```

These govern whether corresponding operations are selected for extraction or replication, subject to their exact documented placement and supported process types.

**Configuration example:** If a broad IGNOREUPDATES directive applies before two TABLE statements, its effect may be broader than the DBA intended. Do not assume a directive is always limited to the nearest subsequent line. Identify the documentation-defined scope, defaults and reset/opposing directives.

Always confirm DDL, TRUNCATE and DML support individually. A claim that GETTRUNCATES is universally enabled would be unsafe.

## 3. WHERE and FILTER — selective replication

WHERE supports simple row selection; FILTER supports more advanced conditions subject to the relevant process and image semantics. Both require testing with before and after images as appropriate.

**Conceptual filtering example** (exact release-specific expressions and column case need validation):

```text
TABLE APP_SRC.ORDERS, WHERE (REGION = 'US');
```

This is an configuration illustration, **not** an endorsed general rule for a live application. An UPDATE that changes whether a row meets a WHERE condition can produce different results from naïvely filtering one after-image. Understand which DML and image is evaluated.

Validate FILTER functions, operator spelling, and operation-specific semantics against the installed GoldenGate release before using them. Verify operator spelling, function signatures and specific operation behavior against the current Oracle parameter manual.

### Filter acceptance test

For a controlled source/target lab, create two rows (one matching the filter, one not), then test:
- INSERT of a matching and a nonmatching row.
- UPDATE that keeps the row matching.
- UPDATE that crosses from matching to not matching and back.
- DELETE of both matching and nonmatching rows.
- Restart/recovery and source-target reconciliation according to **intended** filter semantics.

Check Extract/Replicat reports, not just final row count. Use separate transport-filter checks if 05 path filters are configured.

## 4. COLMAP and USEDEFAULTS

Use `COLMAP` to define target-to-source column mappings and `USEDEFAULTS` to map compatible same-name columns.

```text
MAP APP_SRC.CUSTOMERS,
    TARGET APP_TGT.CUSTOMERS,
    COLMAP (
      USEDEFAULTS,
      CUSTOMER_NAME = FULL_NAME
    );
```

**Meaning:** same-named target columns are mapped automatically where compatible; target CUSTOMER_NAME gets source FULL_NAME. Both example schemas and columns are illustrative, and should be adapted to the actual PDB-qualified namespace.

**Important constraints:** Confirm compatible data types, character sets, keys, generated/identity columns, NOT NULL constraints and existing row mapping. Complex transformations should have explicit INSERT/UPDATE/DELETE tests and documented rollback.

Oracle describes `COLMAP (USEDEFAULTS, target_column = source_expression)` and specifies that `USEDEFAULTS` precedes the explicit mappings.

Reference: [Oracle 26ai Parameters and Functions Reference (PDF)](https://docs.oracle.com/en/database/goldengate/core/26/reference/reference-oracle-goldengate.pdf).

## 5. Collision handling and apply correctness

**Oracle GoldenGate 26ai defaults to NOHANDLECOLLISIONS.**

Oracle's collision feature can attempt to handle duplicate INSERT, missing UPDATE and missing DELETE situations associated with some initial-load workflows. It is not a general data-repair mechanism and may hide divergence. Actual behavior and compatibility depend on process type and version.

```text
HANDLECOLLISIONS
NOHANDLECOLLISIONS
```

**Do not apply HANDLECOLLISIONS indiscriminately.** Oracle's documented SOURCEISTABLE initial-load workflow specifies a **non-integrated Replicat** for collision handling and warns not to use this mechanism with Integrated Replicat; use precise instantiation for Integrated Replicat.

If a supported workflow temporarily enables collision handling, explicitly disable it when baseline loading and catch-up are completed, and remove the parameter from persistent configuration if appropriate. A runtime SEND REPLICAT change by itself may not persist through restart.

Vendor: [HANDLECOLLISIONS / NOHANDLECOLLISIONS](https://docs.oracle.com/en/database/goldengate/core/26/reference/handlecollisions-nohandlecollisions.html); [SOURCEISTABLE initial load](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/initial-load-sourceistable.html).

## 6. Add a new table to an existing replication pipeline

**High-impact workflow**: adding a table is not merely appending TABLE and MAP statements. Determine source and target baseline first.

Oracle's procedure specifically assumes the new source and target tables are **empty or already contain identical data**, unless you arrange an additional initial-load procedure.

### Prechange checks

- Does the existing TABLE/MAP wildcard already include the new table?
- Are source and target structures/columns/keys compatible?
- Does the table have adequate TRANDATA/SCHEMATRANDATA coverage?
- Is new-table DDL replication configured and supported?
- Are the target rows empty, fully synchronized or in need of a consistent initial load?
- What is the oldest safe capture and apply checkpoint for the new table?
- Do multiple table groups share the same Extract/Replicat, creating broader restart impact?

### General Oracle-documented sequence

1. Coordinate access/writes for the **new table** and establish its correct initial data state.
2. Back up affected process parameters and capture all process checkpoints.
3. Add/check the table on source and target and enable required supplemental logging.
4. Update Extract TABLE scope when not already captured by a wildcard.
5. Update Replicat MAP, optional COLMAP and data-definition compatibility where needed.
6. Use the vendor-specific stop/start sequence required for these configuration changes; **do not shut down unrelated processes by default**.
7. Perform initial load and establish instantiation boundaries when table data were not already identical.
8. Start/restart the affected processes, then verify committed source INSERT/UPDATE/DELETE against target.
9. Capture reports, positions, row counts, checksum and postchange status.

**Why no single unconditional command script?** Capturing a table before its baseline is instantiated can cause missing-row failures; starting it too late can create a gap. Wildcard matching and DDL support change the recommended approach.

Vendor: [Adding Tables to the Oracle GoldenGate Configuration](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/adding-tables-oracle-goldengate-configuration.html).

## 7. Administration example — read-only diagnostics

Connect Admin Client to the correct Microservices deployment and confirm identities before inspecting.

```text
INFO ALL
INFO EXTRACT EXTLAB, DETAIL
INFO REPLICAT REPLAB, DETAIL
STATS EXTRACT EXTLAB
STATS REPLICAT REPLAB
```

For table logging inspection, connect to the correct source DB before checking:

```text
DBLOGIN USERIDALIAS gg_source
INFO TRANDATA APP_SRC.NEW_TABLE
```

Example process and alias names are invented. These commands do not alter replication and cannot alone prove data correctness.

## 8. Troubleshooting matrix

| Symptom | Investigation | Avoid |
|---|---|---|
| New table's DML never reaches target | TABLE scope/wildcard, TRANDATA, source Extract report | Assuming wildcard covers all new objects |
| Replicat reports unknown column | COLMAP, source/target definitions, schema drift | Dropping target columns without plan |
| Replicat abends on duplicate key | Baseline consistency and instantiation SCN | Leaving HANDLECOLLISIONS enabled indefinitely |
| Updates missing after WHERE change | Old/new filter membership and image semantics | Verifying only final row counts |
| Parameter change causes abend | Exact syntax, scope, restart and error report | Restart loops without collecting logs |
| Added table contains source rows but target empty | Missing initial load or skipped start position | Moving checkpoint to NOW |
| Different target values | Mapping functions, defaults, value conversion, constraints | Declaring success from STATS counters |

## 9. Validation labs

**Lab A — parameter scoping:** Provide two TABLE statements and several IGNORE/GET directives. Trace which DML are captured and identify where an opposing directive must be placed. Check against release-specific documentation.

**Lab B — column mapping:** Source has FULL_NAME; target has CUSTOMER_NAME. Use COLMAP to map a controlled row. Validate NULL, multibyte text, updates and a DELETE.

**Lab C — controlled table onboarding:** Add one table in a **disposable lab** whose target starts empty. Plan logging, source capture, target instantiation, restart and source-target reconciliation. Save every decision and prove no missing or duplicated transactions.

**Lab D — collision diagnosis:** Insert the same key independently on source and target to illustrate why a duplicate-key error may signal inconsistent baseline data. Reconcile and repair the condition using an approved method; do not silence the error as the lesson's default answer.

## 10. Evidence checklist


## Verification notes

- **reference-derived:** Days 11–12 and 16–17 concepts and original examples.
- **Vendor-verified correction:** NOHANDLECOLLISIONS default; scoped collision logic; per-table onboarding assumptions; COLMAP syntax.
- **Examples:** Process identifiers, schema/table names and lab scenarios are illustrative.
- **Not tested here:** actual source/target configuration, collision experiments, new-table capture or successful mappings.

### Oracle references

- [HANDLECOLLISIONS / NOHANDLECOLLISIONS](https://docs.oracle.com/en/database/goldengate/core/26/reference/handlecollisions-nohandlecollisions.html)
- [Oracle initial load using SOURCEISTABLE](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/initial-load-sourceistable.html)
- [Adding Tables to an Existing Configuration](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/adding-tables-oracle-goldengate-configuration.html)
- [Parameters and Functions Reference](https://docs.oracle.com/en/database/goldengate/core/26/reference/reference-oracle-goldengate.pdf)
- [Before Adding Extract and Replicat](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/configure-ogg-adding-extract-and-replicat.html)

**Next:** [10 — Security and Interoperability](10-security-credentials-and-interoperability.md)
