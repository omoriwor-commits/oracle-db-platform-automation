# Oracle DBA Runbooks

Operational notes from my self-directed Oracle lab work, checked against my two-node Oracle 26ai RAC (Grid 23.26.1, Oracle Linux 9.8, VirtualBox). Each page states what I've verified and what's still to run.

| Runbook | Status |
| ------- | ------ |
| [Clusterware crsctl reference](rac-clusterware-crsctl-reference.md) | Verified on the 26ai RAC |
| [OCR, OLR and voting files](ocr-olr-administration.md) | Draft; log locations confirmed, commands to verify |
| [RMAN backup automation](rman-backup-automation.md) | Draft; script written, first run to do |
| [DBMS_SCHEDULER](dbms-scheduler.md) | Reference reviewed; runtime/calendar tests pending |
| [Daily and weekly health checks](database-health-checks.md) | Partly automated in the RAC health-check script |
| [Space management](space-management.md) | Reference reviewed; SQL and lab exercises to verify |
| [SQL Tuning Advisor](sql-tuning-advisor.md) | Planned exercise |

Scripts: [`../scripts/rman/rman_backup.sh`](../scripts/rman/rman_backup.sh)
