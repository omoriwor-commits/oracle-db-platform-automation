# Application Containers Lab (Oracle 26ai RAC)

**Date:** October 27–28, 2026
**Environment:** two-node Oracle 26ai RAC lab (CDB `RAC`, instances RAC1/RAC2), run as oracle with `sqlplus / as sysdba`.
**Status:** Verified. Install, two tenants, cross-tenant query, upgrade with partial sync, full sync and a patch all ran; results are recorded below.
**Exam link:** 1Z0-083, "Manage Application PDBs".

## The idea in one sentence

An application is installed **once** in an **application root**; **application PDBs** (tenants) get it through links and pick up new versions with **SYNC**.

```text
CDB
 ├── CDB$ROOT
 ├── PDB$SEED
 └── SALES_ROOT              application root  (head office: tables and code live here)
      ├── TENANT1            application PDB   (own data)
      ├── TENANT2            application PDB   (own data)
      └── F423270943_3_1     hidden application root clone, created by the upgrade
```

## Where to be connected

| Task | Connect to |
| ---- | ---------- |
| Create the application root | `CDB$ROOT` |
| Install, upgrade or patch the application | the application root |
| Create an application PDB or the application seed | the application root |
| Pick up the latest version or patch (`SYNC`) | the tenant itself |

## Sharing modes

| Mode | Tenant has | Result |
| ---- | ---------- | ------ |
| `METADATA` | a metadata link plus its own rows | same design, private data |
| `DATA` | a data link to the root's rows | one shared copy; tenants cannot change it |
| `EXTENDED DATA` | the root's rows plus its own rows | shared rows and local rows together |

Only objects created between `BEGIN` and `END` (install, upgrade, patch) belong to the application.

## 1. Check the undo mode

```sql
SELECT property_value FROM database_properties WHERE property_name = 'LOCAL_UNDO_ENABLED';
```

## 2. Create the application root (from CDB$ROOT)

```sql
CREATE PLUGGABLE DATABASE sales_root AS APPLICATION CONTAINER ADMIN USER appadm IDENTIFIED BY "<password>";
ALTER PLUGGABLE DATABASE sales_root OPEN INSTANCES=ALL;
```

## 3. Install version 1.0 (in the application root)

```sql
ALTER SESSION SET CONTAINER = sales_root;
ALTER PLUGGABLE DATABASE APPLICATION sales_app BEGIN INSTALL '1.0';
CREATE USER sales_owner IDENTIFIED BY "<password>" CONTAINER=ALL;
GRANT CREATE SESSION, CREATE TABLE, UNLIMITED TABLESPACE TO sales_owner CONTAINER=ALL;
CREATE TABLE sales_owner.countries SHARING=DATA (code VARCHAR2(2) PRIMARY KEY, name VARCHAR2(40));
INSERT INTO sales_owner.countries VALUES ('US', 'United States');
CREATE TABLE sales_owner.orders SHARING=METADATA (id NUMBER PRIMARY KEY, country VARCHAR2(2), amount NUMBER);
COMMIT;
ALTER PLUGGABLE DATABASE APPLICATION sales_app END INSTALL '1.0';
```

## 4. Create two tenants (from the application root)

```sql
CREATE PLUGGABLE DATABASE tenant1 ADMIN USER t1adm IDENTIFIED BY "<password>";
CREATE PLUGGABLE DATABASE tenant2 ADMIN USER t2adm IDENTIFIED BY "<password>";
ALTER PLUGGABLE DATABASE tenant1 OPEN INSTANCES=ALL;
ALTER PLUGGABLE DATABASE tenant2 OPEN INSTANCES=ALL;
```

## 5. Sync each tenant and add its own rows

Put each statement on its own line. In 26ai SQL*Plus, `INSERT …; COMMIT` on one line fails with `ORA-03405: End of query reached; no additional text should follow`.

```sql
ALTER SESSION SET CONTAINER = tenant1;
ALTER PLUGGABLE DATABASE APPLICATION sales_app SYNC;
INSERT INTO sales_owner.orders (id, country, amount) VALUES (1, 'US', 100);
COMMIT;

ALTER SESSION SET CONTAINER = tenant2;
ALTER PLUGGABLE DATABASE APPLICATION sales_app SYNC;
INSERT INTO sales_owner.orders (id, country, amount) VALUES (1, 'US', 250);
COMMIT;
```

## 6. Query all tenants at once (from the application root)

```sql
ALTER SESSION SET CONTAINER = sales_root;
SELECT con_id, id, country, amount FROM CONTAINERS(sales_owner.orders) ORDER BY con_id, id;
```

Result:

```text
    CON_ID         ID CO     AMOUNT
---------- ---------- -- ----------
         6          1 US        100
         7          1 US        250
```

Same table design (`METADATA`), different rows in each tenant, read in one query.

## 7. Upgrade to 2.0 and sync only tenant1

```sql
ALTER PLUGGABLE DATABASE APPLICATION sales_app BEGIN UPGRADE '1.0' TO '2.0';
ALTER TABLE sales_owner.orders ADD (status VARCHAR2(10));
ALTER PLUGGABLE DATABASE APPLICATION sales_app END UPGRADE TO '2.0';

ALTER SESSION SET CONTAINER = tenant1;
ALTER PLUGGABLE DATABASE APPLICATION sales_app SYNC;
```

Check the versions from the application root:

```sql
ALTER SESSION SET CONTAINER = sales_root;
COLUMN pdb_name FORMAT A12
COLUMN app_name FORMAT A15
COLUMN app_version FORMAT A10
COLUMN app_status FORMAT A12
SELECT p.pdb_name, s.app_name, s.app_version, s.app_status
FROM dba_app_pdb_status s
JOIN dba_pdbs p ON p.con_uid = s.con_uid
WHERE UPPER(s.app_name) = 'SALES_APP'
ORDER BY p.pdb_name;
```

Result:

```text
PDB_NAME     APP_NAME        APP_VERSIO APP_STATUS
------------ --------------- ---------- ------------
TENANT1      SALES_APP       2.0        NORMAL
TENANT2      SALES_APP       1.0        NORMAL
```

Tenant2 kept working on 1.0. The upgrade created a hidden clone of the old application root, visible in `SHOW PDBS` as `F423270943_3_1`; unsynced tenants use it.

## 8. See the upgrade in the table, then sync tenant2

```sql
ALTER SESSION SET CONTAINER = tenant1;
DESC sales_owner.orders
ALTER SESSION SET CONTAINER = tenant2;
DESC sales_owner.orders
ALTER PLUGGABLE DATABASE APPLICATION sales_app SYNC;
DESC sales_owner.orders
SELECT id, country, amount, status FROM sales_owner.orders;
```

Result: `STATUS` appeared in tenant2 only after its sync; both tenants then showed version 2.0.

## 9. Experiment: can a tenant change shared (DATA) rows?

```sql
ALTER SESSION SET CONTAINER = tenant1;
INSERT INTO sales_owner.countries VALUES ('CA', 'Canada');
```

Result:

```text
ORA-65097: DML into a data link table is outside an application action
```

In tenant1, `COUNTRIES` is only a data link to the rows in the application root. Shared rows can only be changed in the application root, inside an application action.

## 10. Change shared data the right way: a patch

```sql
ALTER SESSION SET CONTAINER = sales_root;
ALTER PLUGGABLE DATABASE APPLICATION sales_app BEGIN PATCH 1;
INSERT INTO sales_owner.countries VALUES ('CA', 'Canada');
COMMIT;
ALTER PLUGGABLE DATABASE APPLICATION sales_app END PATCH 1;

SELECT * FROM dba_app_patches;
SELECT con_uid, app_name, app_version, app_status FROM dba_app_pdb_status;
```

Result: patch 1 `INSTALLED` with `PATCH_MIN_VERSION` 2.0; both tenants still at version 2.0. A patch does not change the version number (an upgrade does).

Still to record: `SELECT * FROM sales_owner.countries;` in tenant1 after `SYNC`, and in tenant2 before `SYNC`, to see whether data-linked rows appear before a sync.

## 11. Optional experiments (not yet run)

```sql
-- B: an object created outside BEGIN/END does not reach tenants
ALTER SESSION SET CONTAINER = sales_root;
CREATE TABLE sales_owner.notes (id NUMBER);
ALTER SESSION SET CONTAINER = tenant1;
ALTER PLUGGABLE DATABASE APPLICATION sales_app SYNC;
SELECT COUNT(*) FROM sales_owner.notes;

-- C: a new tenant before and after SYNC
ALTER SESSION SET CONTAINER = sales_root;
CREATE PLUGGABLE DATABASE tenant3 ADMIN USER t3adm IDENTIFIED BY "<password>";
ALTER PLUGGABLE DATABASE tenant3 OPEN INSTANCES=ALL;
ALTER SESSION SET CONTAINER = tenant3;
SELECT COUNT(*) FROM sales_owner.orders;
ALTER PLUGGABLE DATABASE APPLICATION sales_app SYNC;
SELECT COUNT(*) FROM sales_owner.orders;

-- D: a tenant's private table is not visible to other tenants
ALTER SESSION SET CONTAINER = tenant1;
CREATE TABLE sales_owner.t1_only (x NUMBER);
ALTER SESSION SET CONTAINER = tenant3;
SELECT COUNT(*) FROM sales_owner.t1_only;
```

## 12. Close everything (memory is tight on the lab VMs)

```sql
ALTER SESSION SET CONTAINER = CDB$ROOT;
ALTER PLUGGABLE DATABASE tenant1 CLOSE INSTANCES=ALL;
ALTER PLUGGABLE DATABASE tenant2 CLOSE INSTANCES=ALL;
ALTER PLUGGABLE DATABASE sales_root CLOSE INSTANCES=ALL;
SHOW PDBS
```

To remove the lab completely, drop the tenants first, then the application root clone, then the application root, each with `INCLUDING DATAFILES`.

## Five exam rules

1. The application root is created from the CDB root with `AS APPLICATION CONTAINER`.
2. Application PDBs and the application seed are created from the application root.
3. Install, upgrade and patch happen in the application root, between `BEGIN` and `END`.
4. Tenants get changes only after `SYNC`, run in the tenant.
5. `METADATA` shares the design; `DATA` shares the rows; `EXTENDED DATA` shares rows and allows local rows.
