# Multitenant Management Lab: Users, Resource Manager and Lockdown Profiles (Oracle 26ai RAC)

**Date:** October 27, 2026
**Environment:** two-node Oracle 26ai RAC lab (CDB `RAC`), run as oracle with `sqlplus / as sysdba`.
**Status:** RACPDB2 created and open. The user, Resource Manager and lockdown steps are written but their results are not yet recorded.
**Topic area:** Oracle Multitenant — CDB/PDB management, common and local users, Resource Manager and PDB lockdown profiles.

## Key points

- `STARTUP` opens the root; PDBs stay mounted unless opened or their state is saved (`SAVE STATE`).
- `SHUTDOWN IMMEDIATE` while connected to a PDB closes only that PDB.
- On RAC, open and close PDBs with `INSTANCES=ALL`.
- `V$PARAMETER.ISPDB_MODIFIABLE = 'TRUE'` means a PDB can have its own value.
- Common users: created in the root, `C##` prefix, `CONTAINER=ALL`. Local users: created inside one PDB.
- CDB resource plans: `shares` is a relative guarantee, `utilization_limit` is a cap, `parallel_server_limit` caps parallel servers. Performance profiles let many PDBs share one directive (`DB_PERFORMANCE_PROFILE`).
- Lockdown profiles restrict statements, features and options inside a PDB; apply them with the `PDB_LOCKDOWN` parameter.

## Before changing the lab

Run only in the disposable lab. Record `SHOW USER`, `SHOW CON_NAME`, database release and the RAC instances covered. Capture existing `PDB_LOCKDOWN` in RACPDB2 and `RESOURCE_MANAGER_PLAN` in CDB$ROOT, including per-instance memory and SPFILE settings. Check whether the named users, profile and plan already exist; stop rather than replacing pre-existing objects. Keep a separate authorised CDB$ROOT session available for recovery. Empty strings in cleanup are correct only when the recorded original value was empty.

## 1. A second PDB

```sql
CREATE PLUGGABLE DATABASE racpdb2 ADMIN USER pdbadmin IDENTIFIED BY "<password>";
ALTER PLUGGABLE DATABASE racpdb2 OPEN INSTANCES=ALL;
ALTER PLUGGABLE DATABASE racpdb2 SAVE STATE;
SELECT inst_id, name, open_mode FROM gv$pdbs ORDER BY name, inst_id;
```

## 2. Common and local users

```sql
CREATE USER c##labadmin IDENTIFIED BY "<password>" CONTAINER=ALL;
GRANT CREATE SESSION TO c##labadmin CONTAINER=ALL;
ALTER SESSION SET CONTAINER = racpdb1;
CREATE USER app1 IDENTIFIED BY "<password>";
ALTER SESSION SET CONTAINER = CDB$ROOT;
```

## 3. CDB resource plan

```sql
BEGIN
  DBMS_RESOURCE_MANAGER.CREATE_PENDING_AREA;
  DBMS_RESOURCE_MANAGER.CREATE_CDB_PLAN('lab_cdb_plan', 'Week 1 lab plan');
  DBMS_RESOURCE_MANAGER.CREATE_CDB_PLAN_DIRECTIVE('lab_cdb_plan', 'RACPDB1', shares => 3);
  DBMS_RESOURCE_MANAGER.CREATE_CDB_PLAN_DIRECTIVE('lab_cdb_plan', 'RACPDB2', shares => 1, utilization_limit => 50);
  DBMS_RESOURCE_MANAGER.VALIDATE_PENDING_AREA;
  DBMS_RESOURCE_MANAGER.SUBMIT_PENDING_AREA;
END;
/
ALTER SYSTEM SET resource_manager_plan = 'lab_cdb_plan' SCOPE=BOTH SID='*';
SELECT plan, pluggable_database, shares, utilization_limit FROM dba_cdb_rsrc_plan_directives WHERE plan = 'LAB_CDB_PLAN';
```

## 4. Lockdown profile

```sql
CREATE LOCKDOWN PROFILE lab_lockdown;
ALTER LOCKDOWN PROFILE lab_lockdown DISABLE STATEMENT = ('ALTER SYSTEM');
ALTER SESSION SET CONTAINER = racpdb2;
ALTER SYSTEM SET pdb_lockdown = lab_lockdown SCOPE=BOTH SID='*';
ALTER SYSTEM SET open_cursors = 400;   -- negative test: record the actual result/error
```

Record the active profile/rules, principal and container before the negative test. A privilege failure alone does not prove that the lockdown rule caused it. Compare an authorised baseline with the restricted test, retain the exact observed error and restore the original `OPEN_CURSORS` if the test unexpectedly changes it. This runbook has no recorded enforcement result yet.

## 5. PDB-modifiable parameters

```sql
ALTER SESSION SET CONTAINER = CDB$ROOT;
SELECT name FROM v$parameter WHERE ispdb_modifiable = 'TRUE' AND name LIKE '%target%';
```

## 6. Restore settings; optional teardown

This procedure is **not yet lab-validated**. Use only the disposable objects created by this exercise; check all profile/plan assignments first. Do not assume that `ALTER SYSTEM` remains usable from the restricted PDB.

If the PDB rejects cleanup, use the retained authorised CDB$ROOT session to remove the exercise's ALTER SYSTEM restriction from its dedicated lab profile:

```sql
ALTER SESSION SET CONTAINER = CDB$ROOT;
ALTER LOCKDOWN PROFILE lab_lockdown ENABLE STATEMENT = ('ALTER SYSTEM');
```

This changes the rule for every PDB assigned this profile; proceed only after confirming it is dedicated to this exercise. Return to RACPDB2 and restore its recorded prior profile and `OPEN_CURSORS` settings. For the specific case where the prior PDB profile was empty:

```sql
ALTER SESSION SET CONTAINER = racpdb2;
ALTER SYSTEM SET pdb_lockdown = '' SCOPE=BOTH SID='*';
```

If the original value was non-empty or used per-instance overrides, restore that exact baseline instead. In CDB$ROOT, restore the recorded original resource plan; use the following only when it was originally empty:

```sql
ALTER SESSION SET CONTAINER = CDB$ROOT;
ALTER SYSTEM SET resource_manager_plan = '' SCOPE=BOTH SID='*';
```

Optional teardown, only after confirming the lab profile and plan were created here, have no remaining consumers and are inactive on every RAC instance:

```sql
-- CDB$ROOT; authorised lab administrator
DROP LOCKDOWN PROFILE lab_lockdown;
BEGIN
  DBMS_RESOURCE_MANAGER.CREATE_PENDING_AREA;
  DBMS_RESOURCE_MANAGER.DELETE_CDB_PLAN(plan => 'LAB_CDB_PLAN');
  DBMS_RESOURCE_MANAGER.VALIDATE_PENDING_AREA;
  DBMS_RESOURCE_MANAGER.SUBMIT_PENDING_AREA;
END;
/
```

Dropping the profile alone does not clear a stored `PDB_LOCKDOWN` name. Verify memory/SPFILE values and effective rules across both instances after restoration. If plan validation fails, inspect the pending area and discard only this exercise's pending changes before retrying.

This restores settings and optionally removes the profile/plan; it is **not a complete object teardown**. The created common/local users and RACPDB2 remain. Remove only accounts proved to have been created for this exercise, after checking ownership and dependencies; do not add blanket `DROP USER ... CASCADE` or drop a retained PDB. Close RACPDB2 on all instances only if it is no longer in use.

References: [Oracle lockdown-profile administration](https://docs.oracle.com/en/database/oracle/oracle-database/26/dbseg/restricting-operations-pdbs-using-pdb-lockdown-profiles.html), [ALTER LOCKDOWN PROFILE](https://docs.oracle.com/en/database/oracle/oracle-database/26/sqlrf/ALTER-LOCKDOWN-PROFILE.html), [Resource Manager](https://docs.oracle.com/en/database/oracle/oracle-database/26/admin/managing-resources-with-oracle-database-resource-manager.html).

## Results to record

Retain before/after settings, identity/container, the actual positive and negative access results from steps 2–5, both RAC instance values and cleanup output. Record the exact error returned; do not prefill ORA-01031 or claim enforcement/cleanup has passed before running it.
