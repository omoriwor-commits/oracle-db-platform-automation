# Generate Oracle object DDL with DBMS_METADATA

**Last updated:** 2026-10-20.  
**Status:** Reference reviewed against Oracle 26ai documentation; extraction/output validation in the lab is pending. No database commands were executed for this publication.

Consolidates the two identical supplied references into one reusable DBA procedure. Use it for migration preparation, change review and schema comparison. Generating DDL does not execute it or prove that it will deploy successfully elsewhere.

## Session and output setup

Use a dedicated SQL*Plus session connected to the PDB that owns the objects, such as RACPDB1. HR and the object names below are examples; confirm they exist. Use exact dictionary spelling for quoted identifiers.

```sql
SHOW CON_NAME;
SELECT USER FROM dual;

SET LONG 1000000
SET LONGCHUNKSIZE 1000000
SET PAGESIZE 0
SET LINESIZE 32767
SET HEADING OFF
SET FEEDBACK OFF
SET VERIFY OFF
SET TRIMSPOOL ON
SET TAB OFF
```

Place SQL*Plus SET commands on separate lines without SQL semicolons. LONG limits displayed CLOB output: increase it if necessary and inspect the end of the result for truncation. These settings affect client output, not object definitions. See [SQL*Plus SET](https://docs.oracle.com/en/database/oracle/oracle-database/26/sqpug/SET-system-variable-summary.html).

Initialize session transforms explicitly:

```sql
BEGIN
  DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'DEFAULT', TRUE);
  DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'SQLTERMINATOR', TRUE);
  DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'PRETTY', TRUE);
END;
/
```

## Table, view and materialized view

Choose the query for the required object:

```sql
SELECT DBMS_METADATA.GET_DDL('TABLE', 'EMPLOYEES', 'HR') FROM dual;

SELECT DBMS_METADATA.GET_DDL('VIEW', 'TEST_VIEW', 'HR') FROM dual;

SELECT DBMS_METADATA.GET_DDL('MATERIALIZED_VIEW', 'TEST_MVIEW', 'HR') FROM dual;
```

GET_DDL is a function in the DBMS_METADATA package. A table definition alone is not a complete schema migration: inventory separate indexes, grants, triggers and dependencies before deciding what else to extract. Materialized-view refresh arrangements also need review. See [Oracle Metadata API usage](https://docs.oracle.com/en/database/oracle/oracle-database/26/sutil/using-oracle-dbms_metadata-api.html).

## Table DDL without the STORAGE clause

```sql
BEGIN
  DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'SEGMENT_ATTRIBUTES', TRUE);
  DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'TABLESPACE', TRUE);
  DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'STORAGE', FALSE);
END;
/

SELECT DBMS_METADATA.GET_DDL('TABLE', 'EMPLOYEES', 'HR') FROM dual;
```

This retains tablespace and other segment attributes; it does **not** produce only logical table DDL plus TABLESPACE. To omit segment attributes, use the alternative below; it also suppresses tablespace clauses:

```sql
BEGIN
  DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'SEGMENT_ATTRIBUTES', FALSE);
END;
/

SELECT DBMS_METADATA.GET_DDL('TABLE', 'EMPLOYEES', 'HR') FROM dual;
```

## User creation DDL: restricted output

Run only in a private session with authorized access, no public spool and no shared terminal recording:

```sql
SELECT DBMS_METADATA.GET_DDL('USER', 'HR') FROM dual;
```

Authentication material can appear depending on caller privileges. Treat raw output as sensitive. Do not commit it; produce a reviewed template with authentication replaced by a placeholder. GET_DDL('USER', ...) does not constitute a full user migration with all grants and owned objects.

An owner can retrieve its own object metadata. Cross-schema retrieval requires appropriate catalog access; ordinary SELECT access to a table is insufficient. Avoid granting broad catalog roles solely to run an example. Definer-rights wrappers have different role behavior. See the [DBMS_METADATA security model and transforms](https://docs.oracle.com/en/database/oracle/oracle-database/26/arpls/DBMS_METADATA.html).

## Finish and validate before reuse

Reset transforms at the end, or close the dedicated session:

```sql
BEGIN
  DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'DEFAULT', TRUE);
END;
/
```

DEFAULT resets to Oracle defaults, not to custom settings present before this procedure.

Retain sanitized evidence of container, owner/object, version, transform choices and complete output. For deployment, review target compatibility, tablespaces, dependencies and privileges, then test in an isolated target. Generated DDL can create or replace objects when executed; extraction is not approval to deploy it. For DevOps reuse, keep reviewed definitions and intended changes in version control, with secrets provisioned separately.

## Provenance

Adapted from the user's duplicated [DBA Genesis DDL reference](https://support.dbagenesis.com/oracle-database/generate-table-ddl-command), with corrected formatting and reviewed Oracle references above. No article prose or generated live DDL is reproduced. Individual lab checks remain pending; this status does not reclassify earlier independent DBA experience.

- [Oracle DBA runbook index](README.md)
