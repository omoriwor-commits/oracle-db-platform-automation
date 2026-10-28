# Multitenant Management Lab: Users, Resource Manager and Lockdown Profiles (Oracle 26ai RAC)

**Date:** October 27, 2026
**Environment:** two-node Oracle 26ai RAC lab (CDB `RAC`), run as oracle with `sqlplus / as sysdba`.
**Status:** RACPDB2 created and open. The user, Resource Manager and lockdown steps are written but their results are not yet recorded.
**Exam link:** 1Z0-083, "Manage CDBs and PDBs" and "Manage Security in Multitenant databases".

## Key points

- `STARTUP` opens the root; PDBs stay mounted unless opened or their state is saved (`SAVE STATE`).
- `SHUTDOWN IMMEDIATE` while connected to a PDB closes only that PDB.
- On RAC, open and close PDBs with `INSTANCES=ALL`.
- `V$PARAMETER.ISPDB_MODIFIABLE = 'TRUE'` means a PDB can have its own value.
- Common users: created in the root, `C##` prefix, `CONTAINER=ALL`. Local users: created inside one PDB.
- CDB resource plans: `shares` is a relative guarantee, `utilization_limit` is a cap, `parallel_server_limit` caps parallel servers. Performance profiles let many PDBs share one directive (`DB_PERFORMANCE_PROFILE`).
- Lockdown profiles restrict statements, features and options inside a PDB; apply them with the `PDB_LOCKDOWN` parameter.

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
ALTER SYSTEM SET pdb_lockdown = lab_lockdown;
ALTER SYSTEM SET open_cursors = 400;   -- expected to fail with ORA-01031
```

## 5. PDB-modifiable parameters

```sql
ALTER SESSION SET CONTAINER = CDB$ROOT;
SELECT name FROM v$parameter WHERE ispdb_modifiable = 'TRUE' AND name LIKE '%target%';
```

## 6. Clean up

```sql
ALTER SESSION SET CONTAINER = racpdb2;
ALTER SYSTEM SET pdb_lockdown = '';
ALTER SESSION SET CONTAINER = CDB$ROOT;
ALTER SYSTEM SET resource_manager_plan = '' SCOPE=BOTH SID='*';
ALTER PLUGGABLE DATABASE racpdb2 CLOSE INSTANCES=ALL;   -- when not in use, to save memory
```

## Results to record

Paste the output of steps 2–5 here when run, especially the `ORA-01031` from step 4, which shows the lockdown profile working.
