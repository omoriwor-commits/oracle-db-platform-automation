# Oracle 19c migration to AWS: 2023 practice reference

**Historical practice:** 2023, as reported by Rotimi Omoriwo.  
**Documentation review:** 2026-10-20.  
**Status:** Preserved and corrected syntax from independent AWS migration practice. This review did not rerun the migrations. The supplied notes cover several alternatives; they do not independently establish a successful run of every method. Original logs, dates within 2023, database sizes, timings and reconciliation results have not been supplied here.

This is earlier database/cloud engineering experience. The current project's planned AWS/DevOps extension is a separate implementation and automation effort. No paid production DBA employment, automated deployment or production cutover is claimed.

## Scope and method selection

| Route | Methods in the supplied notes | Main consideration |
|---|---|---|
| On-premises Oracle 19c PDB to self-managed Oracle on EC2 | Remote PDB clone; unplug/plug archive; active RMAN PDB duplication | Availability window, compatibility, transfer capacity and rollback |
| Oracle on EC2 to standard RDS for Oracle | Schema/table Data Pump export, database-link file transfer, remote import | Managed-service restrictions, object compatibility and reconciliation |

Size, bandwidth and cost matter, alongside licensing, edition/options, encryption, recovery objectives, downtime and supported versions. A point-in-time clone or export alone does not keep later source changes synchronized. Freeze writes or design a separate supported catch-up/cutover method. This page does not claim CDC was part of the 2023 exercise.

## Preconditions and notation

- Verify source/target database identity, CDB/PDB service, release/RU, character sets, options and TDE keys before selecting a method. Record backup and rollback arrangements before changes.
- Use private routing and restricted security groups where available. Configure and verify database transport encryption separately. Do not expose TCP 1521 to the internet for these examples.
- All paths, names and aliases below are examples. Create staging/data directories with appropriate owner, permissions and capacity before database operations. Source and destination file locations must not collide.
- Angle-bracket values are deliberately non-executable placeholders. Enter credentials privately; do not commit completed credential statements or spooled secrets. Do not run these examples as one unattended script.
- `SOURCE_PDB` resolves the source HR_PDB service. `SOURCE_CDB` and `TARGET_CDB` resolve their respective root services. `RDSPDB` resolves the actual RDS endpoint/service. Validate aliases on each initiating host; matching alias spelling alone proves nothing about the destination.

For each SQL session, establish context first:

```sql
SHOW CON_NAME;
SELECT name, db_unique_name, open_mode FROM v$database;
SELECT instance_name, host_name, version FROM v$instance;
```

Example Oracle Net descriptor; substitute privately:

```text
SOURCE_PDB =
 (DESCRIPTION =
   (ADDRESS = (PROTOCOL = TCP)(HOST = <source-private-dns>)(PORT = 1521))
   (CONNECT_DATA = (SERVICE_NAME = <source-pdb-service>))
 )
```

On target EC2, verify an existing Oracle 19c CDB and a usable Oracle Managed Files destination. This is self-managed EC2 storage, not an RDS filesystem operation:

```sql
-- Target CDB$ROOT; change only after checking the directory and existing setting.
SHOW PARAMETER db_create_file_dest
ALTER SYSTEM SET db_create_file_dest = '/u01/CDB/' SCOPE=BOTH;
```

## Method 1: remote PDB clone to EC2

On source HR_PDB, an authorized administrator creates a temporary local account. The old broad CONNECT/RESOURCE grants are unnecessary for this example:

```sql
ALTER SESSION SET CONTAINER = HR_PDB;
CREATE USER migrate IDENTIFIED BY "<private-secret>";
GRANT CREATE SESSION, CREATE PLUGGABLE DATABASE TO migrate;
```

On target CDB$ROOT, using an administrator authorized to create the private link and PDB:

```sql
CREATE DATABASE LINK source_pdb_link
  CONNECT TO migrate IDENTIFIED BY "<private-secret>" USING 'SOURCE_PDB';

CREATE PLUGGABLE DATABASE hr_pdb_new FROM hr_pdb@source_pdb_link;
ALTER PLUGGABLE DATABASE hr_pdb_new OPEN READ WRITE;
```

For hot cloning, check ARCHIVELOG and local undo at the source and retain required archives; otherwise plan the required read-only window. This is a clone, not automatic source retirement or continuous synchronization. Inspect target files, plug-in violations and application data before any cutover. Remove temporary links/accounts only after checking their remaining dependencies.

Reference: [Oracle 19c remote PDB cloning](https://docs.oracle.com/en/database/oracle/oracle-database/19/multi/cloning-a-pdb.html).

## Method 2: unplug/plug archive to EC2

This stops source-PDB availability. Arrange an outage and a recoverable rollback before unplugging. Execute from **source CDB$ROOT**, not from inside HR_PDB:

```sql
ALTER PLUGGABLE DATABASE hr_pdb CLOSE IMMEDIATE;
ALTER PLUGGABLE DATABASE hr_pdb UNPLUG INTO '/u01/stage/hr_pdb.pdb';
```

The `.pdb` file is a PDB archive, not a Data Pump export. Transfer it using an approved encrypted channel; compare SHA-256 at both ends. Budget for the archive, extracted files and target copies.

At target CDB$ROOT, test compatibility before creation:

```sql
SET SERVEROUTPUT ON
BEGIN
  IF DBMS_PDB.CHECK_PLUG_COMPATIBILITY(
       pdb_descr_file => '/u01/stage/hr_pdb.pdb',
       pdb_name => 'HR_PDB') THEN
    DBMS_OUTPUT.PUT_LINE('COMPATIBLE');
  ELSE
    DBMS_OUTPUT.PUT_LINE('STOP: inspect PDB_PLUG_IN_VIOLATIONS');
  END IF;
END;
/
```

Continue only after resolving incompatibilities and checking target names/storage:

```sql
CREATE PLUGGABLE DATABASE hr_pdb USING '/u01/stage/hr_pdb.pdb';
ALTER PLUGGABLE DATABASE hr_pdb OPEN READ WRITE;
SELECT name, open_mode FROM v$pdbs WHERE name = 'HR_PDB';
SELECT file_name FROM cdb_data_files
WHERE con_id = (SELECT con_id FROM v$pdbs WHERE name = 'HR_PDB');
```

Check extracted/stored locations rather than assuming the archive itself becomes a datafile. Back up the target and validate the application. The original immediate source `DROP ... INCLUDING DATAFILES` is deliberately excluded. Source retirement needs a separate decision after acceptance and the rollback-retention period. An unplugged source is not simply reopened; rollback requires a planned re-plug/restore procedure.

References: [Unplugging/removing PDBs](https://docs.oracle.com/en/database/oracle/oracle-database/19/multi/removing-a-pdb.html), [plugging an archive and compatibility checks](https://docs.oracle.com/en/database/oracle/oracle-database/19/multi/plugging-in-a-pdb.html).

## Method 3: active RMAN PDB duplication to an existing EC2 CDB

Check COMPATIBLE >= 18 on both CDBs, local undo on both, source PDB open, destination CDB read/write and using an SPFILE. Prepare password-file authentication and required Oracle Net/static-listener connectivity. Apply the full active-duplication prerequisites, including credential consistency and archiving requirements. For encrypted PDBs, plan the release-specific keystore/key handling separately.

At target CDB$ROOT, use an existing protected directory for foreign archive recovery:

```sql
ALTER SYSTEM SET remote_recovery_file_dest = '/u01/stage/remote_recovery' SCOPE=BOTH;
```

Run RMAN on a host with tested root-service aliases. Enter passwords at prompts:

```bash
rman
```

```text
CONNECT TARGET sys@SOURCE_CDB;
CONNECT AUXILIARY sys@TARGET_CDB;
DUPLICATE PLUGGABLE DATABASE HR_PDB AS HR_PDB_CLONE
  TO EC2CDB FROM ACTIVE DATABASE;
```

`EC2CDB` must be replaced by the actual destination database name; it is not the TNS alias or new PDB name. The destination CDB already exists and is open: do not apply a whole-CDB NOMOUNT recipe here. Choose either a preserved PDB name or an AS-renamed clone, not two duplicate commands in succession. Validate destination state/files/data after RMAN completes.

References: [DUPLICATE prerequisites and syntax](https://docs.oracle.com/en/database/oracle/oracle-database/19/rcmrf/DUPLICATE.html), [RMAN duplication guide](https://docs.oracle.com/en/database/oracle/oracle-database/19/bradv/rman-duplicating-databases.html).

## EC2 to standard RDS for Oracle: Data Pump

Standard RDS for Oracle provides neither host login nor SYS/SYSDBA access. Use application-scoped schema/table imports here. This does not mean Data Pump is the only migration technology; AWS also documents other approaches. Do not assume RDS Custom has identical controls.

Prepare the destination schema/tablespaces/quotas and required object privileges. Review unsupported objects and tablespace mappings. Use an authorized Data Pump account on EC2 rather than routine SYSDBA export. Cross-schema exports require appropriate Data Pump privileges; directory access and DBMS_FILE_TRANSFER permissions must be checked separately.

```sql
-- Source PDB, using the account that will export/transfer.
SELECT directory_name, directory_path FROM all_directories
WHERE directory_name = 'DATA_PUMP_DIR';

CREATE DATABASE LINK rdspdb
  CONNECT TO <rds-master-user> IDENTIFIED BY "<private-secret>" USING 'RDSPDB';
```

Source-host command, with password prompted. Use a fresh dump/log name per run; do not overwrite a retained migration artifact:

```bash
expdp export_user@SOURCE_PDB DIRECTORY=DATA_PUMP_DIR DUMPFILE=scott.dmp LOGFILE=scott_export.log SCHEMAS=SCOTT
```

In the source PDB, as the transfer/link owner:

```sql
BEGIN
  DBMS_FILE_TRANSFER.PUT_FILE(
    source_directory_object => 'DATA_PUMP_DIR',
    source_file_name => 'scott.dmp',
    destination_directory_object => 'DATA_PUMP_DIR',
    destination_file_name => 'scott.dmp',
    destination_database => 'RDSPDB');
END;
/
```

From an Oracle client host, the import connects to RDS and reads the dump **on RDS**. It does not read the client's local filesystem:

```bash
impdp admin@RDSPDB DIRECTORY=DATA_PUMP_DIR DUMPFILE=scott.dmp LOGFILE=scott_import.log SCHEMAS=SCOTT
```

If a deliberate schema rename is required, use the following **instead**, after preparing the target HR account and checking privileges/object references:

```bash
impdp admin@RDSPDB DIRECTORY=DATA_PUMP_DIR DUMPFILE=scott.dmp LOGFILE=scott_to_hr_import.log SCHEMAS=SCOTT REMAP_SCHEMA=SCOTT:HR
```

Here `admin` is an example RDS master username; substitute the actual authorized account. Avoid an unreviewed TABLE_EXISTS_ACTION=REPLACE on a populated target. A schema remap does not establish that all embedded schema references were rewritten.

### Table-only variant: consistent filenames

```bash
expdp export_user@SOURCE_PDB DIRECTORY=DATA_PUMP_DIR DUMPFILE=emp_table.dmp LOGFILE=emp_export.log TABLES=SCOTT.EMPLOYEES
```

Repeat the transfer block with **both** filename arguments set to `emp_table.dmp`. Then use one import option:

```bash
impdp admin@RDSPDB DIRECTORY=DATA_PUMP_DIR DUMPFILE=emp_table.dmp LOGFILE=emp_import.log TABLES=SCOTT.EMPLOYEES
# Alternative, after preparing HR:
impdp admin@RDSPDB DIRECTORY=DATA_PUMP_DIR DUMPFILE=emp_table.dmp LOGFILE=emp_to_hr_import.log TABLES=SCOTT.EMPLOYEES REMAP_SCHEMA=SCOTT:HR
```

The old table example incorrectly reused `scott.dmp` during import and cleanup; these are separate artifacts.

### Acceptance and cleanup

Before removal, reconcile source/target at a consistent point: scoped row counts, key totals/sample contents, invalid objects, constraints, indexes, sequences, grants and application behavior. Review every export/import error; a completed client process alone is insufficient. Establish target backup/recovery before cutover and retain logs.

After acceptance and retention checks, remove only the exact dump no longer required. On RDS:

```sql
-- Schema artifact: run only if this is the accepted artifact to remove.
EXEC UTL_FILE.FREMOVE('DATA_PUMP_DIR', 'scott.dmp');
```

For the table-only exercise, the matching cleanup filename is `emp_table.dmp`. This deletes the staged dump, not its imported tables. Keep sufficient storage for dumps, data/index growth and operational headroom. Revoke temporary access and remove unused links after checking dependencies.

Reference: [AWS Data Pump import, transfer prerequisites and cleanup](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Oracle.Procedural.Importing.DataPump.html). A future S3/DMS implementation requires its own design; it is not claimed as historical work by this page.

## Reuse through a DevOps and architecture lens

Preserve manual DBA knowledge first; automate only after parameter validation and observed results. Future improvements include protected secrets, explicit source/target checks, migration manifests, checksums, log/error handling, approval gates for write/cutover/retirement actions, and repeatable data reconciliation. These are development goals, not a claim that Terraform or CI/CD was implemented in 2023.

| Record | Current evidence status |
|---|---|
| AWS Oracle migration practice in 2023 | User-confirmed history |
| Methods and syntax | Supplied notes, corrected during this review |
| Individual method runs and exact outcomes | No historical execution transcripts attached here |
| Current environment rerun | Not performed by this documentation update |
| Automation, cutover and rollback proof | Record separately when implemented/tested |

This reference preserves earlier experience without turning illustrative syntax into fabricated results. Review against the exact target engine, RU and AWS service configuration before reuse; it is not a 26ai-on-RDS support assertion.
