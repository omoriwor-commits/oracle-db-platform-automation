# Live validation and evidence gates

Updated 2026-10-21. Repository fixes and fake-tool tests do not establish live database recovery, patch compliance or scheduled execution. Existing completed lab experience remains recorded separately.

| Work | Required evidence | Tracker |
|---|---|---|
| RAC support and LMON | Both-node Grid/DB OPatch inventories, SQL patch registry, kernel versions; dated LMHB/LMON and host timeline; supported post-change state | [Issue 23](https://github.com/omoriwor-commits/oracle-db-platform-automation/issues/23) |
| Migration replay | Per-route identity and object scope; baseline SCN/CSN; Extract/Replicat reports; DML comparisons; restart/reconciliation output | [Issue 24](https://github.com/omoriwor-commits/oracle-db-platform-automation/issues/24) |
| RAC availability | Retained actual SCAN new-connection and instance-stop/restoration transcript; distinguish planned stop from unplanned loss | Issue 24 |
| Backup recovery | SHOW ALL, level-0 and restore validation; isolated restore/recovery result, independent copy and freshness monitoring | Issue 24 |
| Data Guard collection | Primary and standby runs; deliberate failed connection; role, lag and datum-time interpretation; broker result | Issue 24 |
| Scheduling | Node-2 tests/manual report and both-node cron/freshness observations | [Draft PR 21](https://github.com/omoriwor-commits/oracle-db-platform-automation/pull/21) |

## Read-only RAC evidence collection

Use the correct existing account and software home; run each node's Grid and DB inventory separately. Store raw output privately and sanitize before publication. Do not post full host logs or identifiers without review.

```bash
# As each software owner, with the verified absolute software home:
"$GRID_HOME/OPatch/opatch" lsinventory
"$ORACLE_HOME/OPatch/opatch" lsinventory
uname -r
date --iso-8601=seconds
```

In an authorized CDB-root SQL session:

```sql
SHOW CON_NAME;
SELECT instance_name, host_name, version_full FROM gv$instance ORDER BY inst_id;
SELECT patch_id, action, status, action_time, description
FROM dba_registry_sqlpatch ORDER BY action_time;
```

Use the incident trace paths referenced by the actual alert entries to collect the October 20 window and matching host journal. Preserve clock/timezone context. High CPU, a kernel support gap or an OPEN database alone does not establish the hang's cause.

## Evidence record

For each real run retain: UTC/local timestamps; operator; repository commit; source/target release and database identity; command and exit code; expected criteria; actual result; errors; sanitized artifact paths and SHA-256; unresolved limits. Never replace missing output with an expected-output transcript. Keep new AWS DMS/SCT/Terraform work planned until deployed and validated.

No cloud resources, patching, instance stops, cron schedules or database restore operations are activated by this document. Execute those changes only with access, a tested backup/rollback plan and the appropriate lab change window.
