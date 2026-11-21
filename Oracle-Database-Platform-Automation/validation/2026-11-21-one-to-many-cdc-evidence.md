# Evidence register — November 21, 2026

This document indexes the recorded November 21 validation screenshots. **Screenshots are not committed to this repository yet**: they need review/redaction for workstation names, users, host IPs, session metadata and any credentials before publication. The linked public runbook cites the observations without falsely implying that binaries are already in GitHub.

| Evidence | Observed state | Planned sanitized artifact |
|---|---|---|
| MSSQL_DEP Admin Client | `REPMSSQL RUNNING NONINTEGRATED`, trail `ms000000001`, RBA `10080`; ODBC connection to SQL Server `GG_TARGET` | `repmssql-start-and-checkpoint-redacted.png` |
| Oracle 26ai / SQL*Plus | ID `900010` INSERT and UPDATE present in `PDB23AI.HOLA.TEST1` | `oracle26ai-insert-update-redacted.png` |
| Windows SQL Server / SSMS | ID `900010` INSERT and UPDATE present in `GG_TARGET.dbo.TEST1` | `sqlserver-insert-update-redacted.png` |
| Oracle 19c primary / SQL*Plus | DELETE of ID `900010`, one row affected, COMMIT, final SELECT empty | `oracle19c-source-delete-redacted.png` |
| Oracle 26ai / SQL*Plus | Final SELECT for ID `900010` returned `no rows selected` | `oracle26ai-delete-redacted.png` |
| SQL Server / SSMS | Final SELECT for ID `900010` returned zero rows | `sqlserver-delete-redacted.png` |
| Data Guard standby / SQL*Plus | `PRDST PHYSICAL STANDBY READ ONLY WITH APPLY`; after DELETE, ID `900010` absent | `dataguard-standby-delete-redacted.png` |
| Data Guard Broker / DGMGRL | `my_dg` `SUCCESS`, `MaxAvailability`, `prodb` primary, `prdst` standby, FSFO disabled | `dataguard-broker-success-redacted.png` |
| Oracle GoldenGate / Admin Client | `DISTMSSQL` RUNNING; `INFO TRANDATA` returned `OGG-00664 / ORA-01031` | `distpath-trandata-privilege-error-redacted.png` |

The proposed filenames are an organizing convention, **not uploaded evidence**. Original screenshots are retained privately and will be added to this public evidence collection only after reviewing and redacting environment and session details. Do not publish unredacted screenshots in a resume or LinkedIn portfolio.
