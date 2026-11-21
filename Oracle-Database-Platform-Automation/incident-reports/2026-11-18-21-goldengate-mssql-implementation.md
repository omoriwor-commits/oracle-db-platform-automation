# Incident register — November 18–21, 2026

In this register, historical failed commands are evidence, not instructions to repeat. See main runbook for approved sequence. No raw screenshots are distributed because they may contain sensitive information.

| Incident | Evidence / cause | Correction and validation | Remaining limitation |
|---|---|---|---|
| MSSQL startup wrong home | OGG_HOME pointed to Oracle software; startSM.sh not in software bin | Separate software and deployment homes; historical working Oracle service inspected | Installer workflow not preserved |
| MSSQL 203/EXEC | AVC init_t denied execute on default_t startSM.sh | Root-owned bin_t wrapper, Type=simple, exec, separate unit | Lab-only confinement; reboot not tested |
| Shutdown left old children | distsrvr, recvsrvr, AIService retained old PIDs and waited on futex after TERM; listener ports released | Stop new MSSQL service; verify executable identity and no active dependencies; targeted KILL of three persistent old children; verify ports free; restart and confirm all ten listeners | Exact cause of incomplete shutdown unproven |
| SQL Server 2025 rejected | OGG-05310 version 17.0.1155 unsupported by installed build | SQL Server 2022 16.0.1220.3 installed and DBLOGIN successful | No upgrade performed |
| ODBC warning | libodbc.so no version information available | Retained bundled driver, actual DBLOGIN passed | ABI warning not resolved |
| GUI blank credentials | CLI and REST GET returned alias but GUI empty on 17841 | Same-number SSH forwards 7840–7844; alias displayed | Origin mismatch leading explanation, not isolated independently |
| GUI blank checkpoint | INFO CHECKPOINTTABLE confirmed create, SSMS showed main and _lox | Do not recreate; verify directly | GUI visibility unresolved |
| Receiver unreachable | No route to host, then connection refused; SSH and ping passed; listener loopback | Restricted firewall rule attempted, then SSH forwarding selected | Remove unused rule after dependency check |
| REST OGG-12062 | Service Manager configuration request unauthorized | Inspect configuration read-only locally; no privilege escalation | Exact authorization cause unknown |
| Wrong host | Firewall/listener checks on pry23ai instead of stb23ai | hostname before each phase | Prevent via host labels |
| Missing path alias | Mandatory Network alias empty | Target ggnet account and source Network/MSSQL_NET; distinct from DB alias | Verify actual target role |
| Wrong GUI | Service Manager 7820 lacks Path Connections; Add Path wizard confused with Add Path Connection | Admin 7821 > Path Connections | None |
| Wizard timeout | Unsaved data lost or not submitted | Reauthenticate, confirm path absent, revalidate tunnel, re-enter six pages; preserve saved credentials/checkpoint | Permanent timeout fix pending |
| SSH tunnel lost | Port 17843 connection refused HTTP 000 | Dedicated key + persistent systemd service | Reboot test pending |
| BatchMode denied | No usable noninteractive key | Dedicated ED25519 credential | No passphrase, documented exception |
| OCI removal did not happen | rm -i confirmation not entered | Confirm dependencies, remove retired files only | Remote revocation not verified |
| ssh-copy-id failed | Restricted public key basename lacks corresponding private key | ssh-copy-id -f -i restricted.pub once, verify authorized_keys | Avoid duplicate entries |
| authorized_keys missing | Verification on source instead of target | Verify on stb23ai | None |
| Tunnel 203/EXEC | AVC init_t → ssh_exec_t denied execute | Root-owned wrapper preserving SSH label | unconfined_service_t exception |
| Wrapper 203/EXEC | Exec format error; first line blank, file ASCII text | Heredoc, first line #!/bin/bash, file and syntax validation | bash -n alone insufficient |
| reset-failed unit not loaded | Inactive unit unloaded after stop | Start unit normally and check status | Not a restart failure itself |
| kill no such process | Repeated signal after PID disappeared | Recheck PID, do not repeat | None |
| Logdump CONNECT | Admin Client command entered in Logdump | OPEN physical trail, GHDR ON, DETAIL ON, COUNT | None |
| SQL*Plus #### | Numeric NUM_ROWS formatted A12 | COLUMN num_rows FORMAT 9999999999 | NUM_ROWS statistics not exact count |
| Distribution filter uncertainty | Trail contained five other tables despite proposed Include rule | Preserve exact proposed filter, verify effective setting and new records; explicit MAP for apply | Data minimization not verified |

## Detailed diagnostic recipes

### MSSQL service lifecycle
On stb23ai:
```bash
sudo journalctl -u OracleGoldenGateMSSQL.service -n 80 --no-pager
sudo ausearch -m AVC,USER_AVC -ts today -i
ls -lZ /u02/ogg_mssql_sm/bin/ /u02/ogg_mssql_home/bin/ServiceManager
namei -l /u02/ogg_mssql_sm/bin/startSM.sh
ps -eo pid,ppid,user,stat,args | grep '[o]gg_mssql_home/bin/'
ps -eo pid,ppid,user,args | grep -E '[e]xtract|[r]eplicat'
ss -ntp state established | grep -E ':784[23]\b'
```
Check configured paths as well: absence of TCP connections does not prove no replication dependencies. Historical PIDs 162188, 162192, 162194 are stale evidence, never reuse blindly. For a future incident, inspect `readlink -f /proc/PID/exe` and `ps -p PID -o pid,ppid,stat,wchan:32,cmd`. Obtain approved outage; prefer administrative stop then TERM. KILL only confirmed stuck processes after graceful attempt and dependency review. Verify all matching processes and ports vanish before starting. Preserve Oracle service and existing trails.

### Firewall attempt and reversal
Historical command on stb23ai:
```bash
sudo firewall-cmd --zone=public --add-rich-rule='rule family="ipv4" source address="192.168.4.113/32" destination address="192.168.4.114/32" port port="7843" protocol="tcp" accept'
```
It did not solve loopback binding. With SSH design, inspect runtime and permanent rules. If rule exists and is not needed by another service, remove just this rule using `--remove-rich-rule` instead of `--add-rich-rule`; use `--permanent` only if present in permanent configuration. Verify afterward. Do not disable firewall or broaden receiver access.

### Credential display
On stb23ai, use curl without response headers (password prompted privately):
```bash
curl --noproxy '*' -sS -u oggadmin http://127.0.0.1:7841/services/v2/credentials
curl --noproxy '*' -sS -u oggadmin http://127.0.0.1:7841/services/v2/credentials/OracleGoldenGate
```
Expected alias name; never publish cookies or tokens. Browser port must match advertised API port for this lab. If still blank check browser DevTools Network/Console. Do not delete credentials to fix display.

### Tunnel execution failures
On pry23ai:
```bash
sudo systemctl stop GoldenGateMSSQLTunnel.service
sudo journalctl -u GoldenGateMSSQLTunnel.service -n 40 --no-pager
sudo ausearch -m AVC,USER_AVC -ts recent -i
ls -lZ /usr/bin/ssh /usr/bin/bash /usr/bin/GoldenGateMSSQLTunnel.sh
matchpathcon /usr/bin/ssh
sudo restorecon -nv /usr/bin/ssh
head -n 1 /usr/bin/GoldenGateMSSQLTunnel.sh | cat -A
file /usr/bin/GoldenGateMSSQLTunnel.sh
findmnt -T /usr/bin/GoldenGateMSSQLTunnel.sh
systemctl is-active fapolicyd
```
Direct denial observed 07:06–07:08, format failure 07:14–07:15; distinct root causes. Corrected wrapper started; PID 175247 terminated at 07:23:53 and restarted at 07:24:03 with PID 176948; HTTP 200. Never disable security controls to bypass failure.

## Supporting diagnostics (private retention)

The original Linux journal entries, SELinux AVC diagnostics, GoldenGate process outputs, remote trail checks and SQL Server metadata observations are retained as private diagnostic material. They are not included in the public repository because some records contain environment-specific identifiers. Relevant findings and timestamps are summarized above. The November 20 Logdump inspection counted 29 records, including 15 DML and four DDL records, involving unrelated tables; the inspected sequence did not show the intended target table. Sanitized extracts can be published after review.


## November 21 follow-up: GoldenGate application, Extract recovery and verification

These follow-ups occurred **after** the November 20 transport-only checkpoint. The authoritative current procedure is the [public Revision 3.0 GoldenGate runbook](../../GoldenGate/runbooks/oracle19c-dataguard-to-oracle26ai-and-sqlserver2022.md), especially sections 4.9–4.11 (Replicat creation, checkpoint alignment, start and transaction tests).

| Finding | My observation | What I did | Result / limit |
|---|---|---|---|
| REPCUT Oracle DDL mismatch | CREATE TABLE for `HOLA.GG_DDL_CDC_2026` was excluded while mappings were narrow; a later source DROP was mapped with wildcard and target had no table | Read REPCUT report showing `ORA-00942`, `OGG-00519`, `OGG-30538`; corrected the interpretation rather than resetting trail | DDL mapping issue identified; do not claim older excluded CREATE replayed |
| EXTTEST stopped progressing | Earlier showed RUNNING with stale checkpoint; later web showed ABENDED and `LAG EXTRACT` produced `OGG-25116` timeout; PID 5836 still existed | Inspected source CDB integrated capture `OGG$CAP_EXTTEST` (ENABLED); copied checkpoint, report and ggserr.log to pry23ai incident folder; attempted STOP; then SIGTERM **only** PID 5836, verified exit and restarted existing Extract | Extract checkpoint advanced and resumed; did not unregister capture or reset its SCN; full transaction-gap reconciliation pending |
| REPMSSQL setup confusion | First ADD succeeded, second ADD gave `OGG-12030`; separate CHECKPOINTTABLE statement invalid | Kept the existing new group and wrote `repmssql.prm` with `MAP PRODBHR.HOLA.TEST1, TARGET dbo.TEST1;` | No DELETE/ADD needed |
| Initial SQL Server checkpoint | New REPMSSQL showed initialized `ms000000000` despite `BEGIN NOW` | Verified four matching baseline rows, inspected `ms000000001` EOF (RBA 10080); altered **stopped** REPMSSQL to sequence 1, RBA 10080 | Start succeeded at that RBA. **Lab-specific only**; do not reuse RBA or claim SCN-verified production cutover |
| First actual Oracle-to-SQL Server CDC | `REPMSSQL` started successfully and connected to `GG_TARGET` using ODBC Driver 18.4 | From Oracle 19c `PRODBHR.HOLA.TEST1`, used test row `900010`; verified INSERT, UPDATE and DELETE in Oracle 26ai `PDB23AI` and SQL Server `GG_TARGET.dbo.TEST1` | DML PASS for tested table; target checks alone do not certify latency, capacity or zero data loss |
| Data Guard alongside CDC | `my_dg` reported SUCCESS with Maximum Availability, `prodb` primary, `prdst` standby; standby READ ONLY WITH APPLY | Checked test row absent after source DELETE on standby `PRODBHR` | Verified final logical state; Fast-Start Failover DISABLED; no switchover/failover or RPO/RTO test |

### Safety and evidence rules

- Do not confuse the GoldenGate SQL Server VM `stb23ai` with Oracle 19c physical standby `stb` (DB unique name `PRDST`).
- Do not run historical failed commands as troubleshooting recipes.
- No automatic "green status = healthy" conclusion: validate source row, trail position, target row and report.
- Keep screenshots/logs private and redacted. Record command date, host, observed message, impacted checkpoint, change authorization, recovery and rollback.
- This is a lab incident archive, not evidence that all production controls were implemented.
