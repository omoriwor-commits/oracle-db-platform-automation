# Oracle users, roles and profiles

**Last updated:** 2026-10-20.  
**Status:** Reference reviewed against Oracle 26ai documentation; lab execution and enforcement tests remain pending. No accounts, grants, profiles or parameters were changed by this publication.

Preserves the supplied administration topics for database/cloud engineering and later controlled automation. Users can represent people, applications or schema owners. Roles group privileges; profiles govern selected password and resource limits. These are distinct controls.

## 1. Read-only baseline and container context

Use an authorized account in the intended PDB, such as RACPDB1. The examples below create local objects there, not common CDB-wide identities. DBA views require appropriate access; do not grant DBA merely to run an inventory query. Names are examples; use exact spelling for quoted identifiers.

```sql
SHOW CON_NAME;
SHOW USER
SELECT username, account_status, default_tablespace,
       temporary_tablespace, profile, authentication_type
FROM dba_users ORDER BY username;

SELECT property_name, property_value FROM database_properties
WHERE property_name IN ('DEFAULT_PERMANENT_TABLESPACE', 'DEFAULT_TEMP_TABLESPACE');

SELECT username, tablespace_name, bytes, max_bytes FROM dba_ts_quotas
WHERE username = 'USR1';

SHOW PARAMETER resource_limit
SELECT inst_id, value FROM gv$parameter
WHERE name = 'resource_limit' ORDER BY inst_id;
```

Record the container and RAC instances covered. The documented 26ai RESOURCE_LIMIT default is **TRUE**, contrary to the old FALSE claim. Inspect the effective value; password controls do not depend on this switch. [RESOURCE_LIMIT](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/RESOURCE_LIMIT.html).

## 2. Account lifecycle examples — changes

Check existing names, approved access and application dependencies before changes. Angle-bracket passwords are non-executable placeholders. Provision actual secrets privately, outside Git/spools/command-line arguments.

```sql
-- Intended application PDB; create initially locked.
CREATE USER usr1 IDENTIFIED BY "<private-secret>"
  DEFAULT TABLESPACE users TEMPORARY TABLESPACE temp ACCOUNT LOCK;

GRANT CREATE SESSION TO usr1;
ALTER USER usr1 QUOTA 10M ON users;
-- Unlock only after provisioning and authorization are complete.
ALTER USER usr1 ACCOUNT UNLOCK;
```

CREATE SESSION is a system privilege, not a role; a quota does not grant CREATE TABLE. An application runtime account accessing another schema's tables may need neither table-creation privileges nor its own storage quota. Default tablespace changes do not move existing objects. Quotas cap allocation and do not reserve free space; also check for UNLIMITED TABLESPACE privilege. [CREATE USER](https://docs.oracle.com/en/database/oracle/oracle-database/26/sqlrf/CREATE-USER.html).

Separate maintenance alternatives; do not paste as a block:

```sql
ALTER USER usr1 ACCOUNT LOCK;
```

```sql
ALTER USER usr1 IDENTIFIED BY "<new-private-secret>";
```

```sql
-- Only if EXAMPLE exists and is the approved destination for future objects.
ALTER USER usr1 DEFAULT TABLESPACE example;
```

Coordinate service-account password rotation with clients and secret storage. Locking an account is not a substitute for investigating existing sessions or compromised credentials. Avoid unrelated password resets during an access review.

## 3. Role-based access example — changes

Create the local role as an authorized administrator. Object grants require the owner or appropriately authorized grantor. SCOTT objects must already exist in this PDB.

```sql
CREATE ROLE sales_manager;
GRANT INSERT ON scott.emp TO sales_manager;
GRANT INSERT ON scott.dept TO sales_manager;
GRANT UPDATE ON scott.dept TO sales_manager;
GRANT DELETE ON scott.bonus TO sales_manager;
GRANT sales_manager TO usr1;
```

Grant only required operations; consider column-specific UPDATE where appropriate. Avoid ADMIN OPTION/GRANT OPTION unless delegation is required. Roles are not a universal replacement for direct grants: stored-code authorization and enabled/default roles need separate review. See [Oracle privilege and role authorization](https://docs.oracle.com/en/database/oracle/oracle-database/26/dbseg/configuring-privilege-and-role-authorization.html).

## 4. Profiles and enforcement

| Parameter | Meaning |
|---|---|
| FAILED_LOGIN_ATTEMPTS | Consecutive authentication failures before lockout |
| PASSWORD_LOCK_TIME | Lockout duration in days; 15/1440 represents 15 minutes |
| PASSWORD_LIFE_TIME / PASSWORD_GRACE_TIME | Password age and grace period in days; expiration is not the same as account locking |
| PASSWORD_REUSE_TIME / PASSWORD_REUSE_MAX | Days and number of password changes required before reuse; evaluate together |
| PASSWORD_VERIFY_FUNCTION | Approved password-complexity verification function |
| SESSIONS_PER_USER | Concurrent-session limit |
| IDLE_TIME / CONNECT_TIME | Inactive duration / total connection duration, in minutes |

DEFAULT values inherit from the DEFAULT profile. For reuse settings, finite values must both be satisfied; one finite value plus UNLIMITED prevents reuse, while both UNLIMITED disable reuse restrictions. Password policy, authentication method and resource enforcement require separate checks. Resource Manager is preferred for workload resource governance. [CREATE PROFILE](https://docs.oracle.com/en/database/oracle/oracle-database/26/sqlrf/CREATE-PROFILE.html).

Inspect before assignment:

```sql
SELECT username, profile FROM dba_users WHERE username = 'USR1';
SELECT profile, resource_name, resource_type, limit FROM dba_profiles
WHERE profile IN ('MY_PROFILE', 'DEFAULT')
ORDER BY profile, resource_type, resource_name;
```

The following is a **disposable lab example**, not an approved production password policy. A one-session limit and five-minute idle timeout can break connection pools and DBA tooling. Unspecified limits inherit; it does not establish a complete complexity/expiration policy.

```sql
CREATE PROFILE my_profile LIMIT
  FAILED_LOGIN_ATTEMPTS 3
  PASSWORD_LOCK_TIME 1
  SESSIONS_PER_USER 1
  IDLE_TIME 5;

ALTER USER usr1 PROFILE my_profile;
```

Only if resource enforcement is intentionally disabled and enabling it has been assessed for all affected users, change it in the approved container/SPFILE scope. For a RAC setting intended on all instances, verify persistence and effective values on each node:

```sql
ALTER SYSTEM SET resource_limit = TRUE SCOPE=BOTH SID='*';
```

This can activate existing resource limits for other profiles too. An idle session is not necessarily consuming CPU continuously. IDLE_TIME does not time out a long-running active query; timeout notification/cleanup need not occur at the exact minute boundary. Validate behavior using a disposable account and fresh sessions, not a live application identity.

## 5. Permission review — read-only, scoped inventory

Direct grants to a user and role:

```sql
SELECT grantee, privilege, admin_option FROM dba_sys_privs
WHERE grantee IN ('USR1', 'SALES_MANAGER') ORDER BY grantee, privilege;

SELECT grantee, owner, table_name, privilege, grantable FROM dba_tab_privs
WHERE grantee IN ('USR1', 'SALES_MANAGER') ORDER BY grantee, owner, table_name;

SELECT grantee, owner, table_name, column_name, privilege, grantable
FROM dba_col_privs WHERE grantee IN ('USR1', 'SALES_MANAGER')
ORDER BY grantee, owner, table_name, column_name;

SELECT grantee, granted_role, admin_option, default_role FROM dba_role_privs
WHERE grantee IN ('USR1', 'SALES_MANAGER') ORDER BY grantee, granted_role;
```

Role hierarchy reachable from USR1; this lists grant paths, not necessarily enabled access:

```sql
SELECT LEVEL role_depth, grantee, granted_role,
       SYS_CONNECT_BY_PATH(granted_role, ' -> ') role_path
FROM dba_role_privs
START WITH grantee = 'USR1'
CONNECT BY NOCYCLE PRIOR granted_role = grantee;
```

Repeat the grant inventory for discovered roles. Include PUBLIC, ownership, ANY privileges, schema-wide grants and administrative authentication where applicable. In 26ai, inspect DBA_SCHEMA_PRIVS as part of the review; the old system/object-only checklist is incomplete. In a CDB-wide review use appropriate CDB views with CON_ID and record visibility restrictions.

As the subject user, inspect its own current session:

```sql
SELECT role FROM session_roles ORDER BY role;
SELECT privilege FROM session_privs ORDER BY privilege;
```

SESSION_PRIVS does not enumerate every effective object permission. ROLE_SYS_PRIVS, ROLE_TAB_PRIVS and ROLE_ROLE_PRIVS are also useful but limited to accessible roles; an empty result is not proof of no privileges. Compare with authorized DBA-view inventories. [Privilege/role dictionary views](https://docs.oracle.com/en/database/oracle/oracle-database/26/dbseg/user-privilege-and-role-data-dictionary-views.html), [ROLE_TAB_PRIVS visibility](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/ROLE_TAB_PRIVS.html), [column grants](https://docs.oracle.com/en/database/oracle/oracle-database/26/refrn/DBA_COL_PRIVS.html).

## 6. Validation and controlled reuse

For each lab change, retain sanitized before/after state, grantor, container, reason, expected access and observed positive/negative tests. Test allowed DML with disposable data and rollback; test denied operations separately. Do not deliberately lock a working service account to demonstrate enforcement.

For later automation, separate inventory from changes, check current state before CREATE/GRANT/ALTER, protect secret delivery, and record exact revoke/profile-restoration steps. Reverting a profile assignment to the recorded prior profile does not restore a changed password or undo all parameter effects. Do not add DROP USER CASCADE as generic cleanup.

**Pending:** runtime SQL verification, profile inheritance/enforcement tests, role-enabled access tests and sanitized evidence. No successful execution is implied by this reference review.

Provenance: rewritten from the user's supplied users/roles/profiles administration notes; source article prose and promotional image text are not republished. Oracle references are linked by topic.

- [Runbook index](README.md)
