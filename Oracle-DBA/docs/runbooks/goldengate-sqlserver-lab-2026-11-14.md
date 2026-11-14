# Oracle Database Platform Automation — GoldenGate SQL Server Lab Runbook

**Baseline date:** 2026-11-14  
**Status (2026-11-14 checkpoint):** SQL Server 2025 TCP, ODBC authentication, SQL authorization, GoldenGate deployment process environment and DB credential registration verified. **GoldenGate-native connection failed with OGG-05310 because SQL Server 2025 (17.0.1155) is unsupported by installed GoldenGate 23.26.1.0.1.** Replicat not configured or started. SQL Server 2022 is a proposed remediation, not installed.  
**Scope:** Existing Oracle source deployment (`DEP2`), GoldenGate SQL Server deployment (`MSSQL_DEP`) on `stb23ai`, SQL Server target desktop, browser access from Windows.  
**Evidence provenance:** Screenshots, command outputs, and SQL Server Management Studio result grids supplied during troubleshooting. This is a reconstructed runbook, not a machine-generated inventory or live state verification.

## 1. Preservation principles

- Preserve `/u02/ogg26ai_home`, `/u02/ogg26ai_sm`, and `/u02/ogg26ai_deploy` (existing Oracle GoldenGate environment) without changes.
- Preserve `/u02/ogg_mssql_home`, `/u02/ogg_mssql_sm`, and `/u02/ogg_mssql_deploy` (SQL Server GoldenGate installation). Do not uninstall or overwrite while evaluating a new target.
- Do not attempt Replicat against SQL Server 2025 using the currently installed GoldenGate 23.26.1.0.1: GoldenGate-native validation **explicitly rejected version 17.0.1155 with OGG-05310** (see Section 14).
- Never save SQL login passwords, SSH private keys, connection-string secrets, or unredacted `authorized_keys` user identifiers in the repository.
- Maintain dated outputs of version, inventory, network tests, security mapping, configuration, and service status. Avoid recording secrets.

## 2. Topology and known endpoints

| Component | Host/address | Notes |
|---|---|---|
| Oracle GoldenGate Linux for SQL Server | `stb23ai`, `192.168.4.114/24` (`enp0s3`) | Secondary IPv4 `10.0.3.15/24` (`enp0s8`) observed, DHCP |
| SQL Server 2025 desktop | `DESKTOP-7A1862B`, Wi-Fi `192.168.4.32` | Other adapters `192.168.56.1`, VPN interfaces; Wi-Fi chosen for test |
| SQL Server TCP endpoint | `192.168.4.32:1433` | Default `MSSQLSERVER` service; listening on `0.0.0.0` and `::` |
| Windows browser host | Separate Windows machine | Connects to GoldenGate through SSH port forwarding, not directly via Linux loopback |
| Existing Oracle GoldenGate deployment | `DEP2` | Locally observed service ports `127.0.0.1:7830–7833` |
| SQL Server GoldenGate Service Manager | `127.0.0.1:7840` *on Linux* | Forwarded to Windows `127.0.0.1:17840` |
| SQL Server GoldenGate Administration | `127.0.0.1:7841` *on Linux* | Forwarded to Windows same port 7841 |
| Distribution / Receiver / Metrics | `127.0.0.1:7842/7843/7844` *on Linux* | Forwarded to Windows identical ports |

**Conceptual flow:** Oracle source → GoldenGate Extract/trails/distribution → SQL Server GoldenGate Receiver/Replicat → SQL Server target. The full CDC flow has **not** been established; diagram represents intended architecture.

## 3. GoldenGate installation and directories

### 3.1 Existing Oracle deployment — do not modify

- Software home: `/u02/ogg26ai_home`
- Service Manager: `/u02/ogg26ai_sm`
- Deployment: `/u02/ogg26ai_deploy`
- Existing local listeners observed: `7830` ServiceManager, `7831` adminsrvr, `7832` distsrvr, `7833` recvsrvr.

### 3.2 GoldenGate for SQL Server

- Software home: `/u02/ogg_mssql_home`
- Service Manager home: `/u02/ogg_mssql_sm`
- User deployment home: `/u02/ogg_mssql_deploy`
- Deployment name: `MSSQL_DEP`
- Administration, Distribution, Receiver and Performance Metrics services showed **Running** in the browser.
- Local ports on Linux were seen listening on `127.0.0.1:7840–7844`.
- Previously installed home `/u02/OGG_SQLSERVER26ai` was successfully deinstalled using `deinstall.sh`. Inventory then removed this old home; subsequent installation into `/u02/ogg_mssql_home` completed successfully through the silent installer with a response file. **Do not repeat deinstallation.**

### 3.3 Version and inventory — verified 2026-11-14

Commands:

```bash
/u02/ogg_mssql_home/bin/adminclient -v
/u02/ogg_mssql_home/OPatch/opatch lsinventory -oh /u02/ogg_mssql_home
```

Observed output summary:

- `Oracle GoldenGate Administration Client for SQL Server`
- Executable version `23.26.1.0.1`, `OGGCORE_23.26.1.0.0OGGRU_LINUX.X64_260129.2210`, dated Jan 30, 2026.
- OPatch `12.2.0.1.48`, inventory product `Oracle GoldenGate Services for SQL Server 23.4.0.0.0`.
- `There are no Interim patches installed in this Oracle Home.`
- `OPatch succeeded.`

**Interpretation:** `23.4.0.0.0` is the installed product inventory metadata; the client executable reports runtime build `23.26.1.0.1`. Do not mistake them for the same version.

### 3.4 ODBC driver inspection — verified

```bash
ls -lah /u02/ogg_mssql_home/msodbc/lib64/
cat /u02/ogg_mssql_home/msodbc/odbcinst.ini
cat /u02/ogg_mssql_home/msodbc/mssql_odbcini_template.ini
env | grep -E '^(ODBCINI|ODBCSYSINI|LD_LIBRARY_PATH|OGG_HOME)='
```

- `/u02/ogg_mssql_home/msodbc/lib64/libmsodbcsql.so` exists (~2.0 MB).
- Driver entry in `odbcinst.ini`:

```ini
[Microsoft ODBC Driver for SQL Server]
Description=Microsoft ODBC Driver for SQL Server
Driver=/u02/ogg_mssql_home/msodbc/lib64/libmsodbcsql.so
```

- Vendor template: `mssql_odbcini_template.ini` demonstrates a DSN and `Encrypt=yes`, `TrustServerCertificate=yes`.
- `/u02/ogg_mssql_home/msodbc/odbc.ini` **did not exist at the initial inspection**. It was subsequently created with `GG_TARGET_DSN` pointing at `192.168.4.32:1433` / `GG_TARGET` (see Section 14).
- Initial interactive shell lacked `ODBCINI` / `ODBCSYSINI` / `OGG_HOME`; the variables were subsequently exported for the `isql` test. The running `MSSQL_DEP` services were independently checked through `/proc/<PID>/environ` and have the correct ODBC variables (see Section 14).
- Authenticated `isql` connection as `ggadmin`, `DB_NAME()` and `@@VERSION`, identity and `db_owner` checks **passed** (Section 14).

## 4. SSH tunneling: access and automation

### 4.1 Why direct browser access failed

The GoldenGate service manager listened on **Linux** `127.0.0.1:7840`; opening `http://127.0.0.1:7840` on **Windows** instead refers to the Windows loopback interface. Direct Windows connection attempts failed. SSH local forwarding is the supported lab access pattern used here; it avoids exposing unencrypted GoldenGate management ports on the LAN.

Earlier manual tunnel example:

```powershell
ssh -N -T -L 127.0.0.1:17840:127.0.0.1:7840 oracle@192.168.4.114
```

To support all GoldenGate services, the Windows user SSH config contains a `Host ogg-mssql` alias that resolves to `192.168.4.114` as user `oracle`, with these mappings:

```sshconfig
Host ogg-mssql
    HostName 192.168.4.114
    User oracle
    LocalForward 127.0.0.1:17840 127.0.0.1:7840
    LocalForward 127.0.0.1:7841 127.0.0.1:7841
    LocalForward 127.0.0.1:7842 127.0.0.1:7842
    LocalForward 127.0.0.1:7843 127.0.0.1:7843
    LocalForward 127.0.0.1:7844 127.0.0.1:7844
```

**Note:** This is the confirmed effective configuration as displayed via `ssh -G ogg-mssql`; actual config may include unrelated host aliases. Do not replace the whole `.ssh/config` with this excerpt.

### 4.2 Passwordless SSH — verified

- An ED25519 public key from the Windows user's `.ssh/id_ed25519.pub` was appended to `/home/oracle/.ssh/authorized_keys` on `stb23ai`.
- `.ssh` was set to mode `700`; `authorized_keys` to `600`.
- Validation from Windows returned username `oracle` and hostname `stb23ai` without a password prompt:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 -o ClearAllForwardings=yes ogg-mssql "whoami; hostname"
```

Do not copy the private key or paste the public key into public project documentation.

### 4.3 Persistent Windows scheduled task — configured and tested

Task: `GoldenGate-MSSQL-SSH-Tunnel`  
Script: `%USERPROFILE%\.ssh\start-ogg-tunnel.ps1`  
Log: `%USERPROFILE%\.ssh\ogg-tunnel.log`  
Trigger: at user logon  
Principal: interactive Windows user, least privilege (`Limited`)  
Action: `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "<script path>"`  
Settings: no execution time limit; ignore duplicate task instances.

Script examined in Windows PowerShell (abridged from actual output):

```powershell
$ErrorActionPreference = "Stop"
$SshExe = "$env:WINDIR\System32\OpenSSH\ssh.exe"
$LogFile = "$env:USERPROFILE\.ssh\ogg-tunnel.log"
while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content $LogFile "$timestamp Starting GoldenGate SSH tunnel"
    & $SshExe -N -T -o BatchMode=yes ogg-mssql 2>> $LogFile
    $exitCode = $LASTEXITCODE
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content $LogFile "$timestamp SSH exited with code $exitCode"
    Start-Sleep -Seconds 10
}
```

**Runtime evidence:** Task state `Running`; all five Windows local forwarded TCP ports returned `True`; `curl.exe --noproxy "*" -sS -o NUL -w "HTTP %{http_code}\n" http://127.0.0.1:17840/` returned `HTTP 200`. On Windows, task last result `267009` (`0x41301`) indicates task was running, not that it had finished successfully. A reboot/sign-in resilience test remains **pending**.

### 4.4 Access URLs and checks

Windows browser endpoints (when task/tunnel is running):

- Service Manager: `http://127.0.0.1:17840/`
- Administration Server: `http://127.0.0.1:7841/services/v2/content/`
- Other service UIs use Windows loopback ports `7842–7844` as relevant.

```powershell
Get-ScheduledTask -TaskName 'GoldenGate-MSSQL-SSH-Tunnel' | Select-Object TaskName,State
Get-ScheduledTaskInfo -TaskName 'GoldenGate-MSSQL-SSH-Tunnel' | Select-Object LastRunTime,LastTaskResult
17840,7841,7842,7843,7844 | ForEach-Object { Test-NetConnection 127.0.0.1 -Port $_ | Select-Object RemotePort,TcpTestSucceeded }
Get-Content "$env:USERPROFILE\.ssh\ogg-tunnel.log" -Tail 20
curl.exe --noproxy "*" -sS -o NUL -w "HTTP %{http_code}\n" http://127.0.0.1:17840/
```

**Avoid:** Navigating to `/services/v2/content/` on port 17840, or adding `/**`/arbitrary query parameters to the URL. `OGG-12031` and `OGG-12033` were observed for nonexistent paths; these are not evidence of failed tunneling. Use the exact service roots above.

**Troubleshooting history:** Initial SSH tunnels failed because port forward process had stopped; a PowerShell task registration attempt used invalid `-RunLevel LeastPrivilege` (correct value `Limited`); a scheduled-task run initially exited with `LastTaskResult=1`; later changed task action to use PowerShell `-ExecutionPolicy Bypass`, after which task reported running and TCP/HTTP passed. When diagnosing, check logs and live port state rather than assuming every task state means health.

## 5. SQL Server 2025 target: inventory and network proof

SQL Server computer: `DESKTOP-7A1862B`; SQL Server product build `17.0.1155.3` = SQL Server 2025; edition **Standard Developer Edition (64-bit)**; instance service `MSSQLSERVER` running. `MSSQLFDLauncher` also observed running.

Windows PowerShell verification on **SQL Server desktop**, not tunnel PC:

```powershell
hostname
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' } | Select-Object InterfaceAlias,IPAddress,PrefixLength
Get-Service -Name 'MSSQL*' | Select-Object Name,Status
Get-NetTCPConnection -State Listen -LocalPort 1433 -ErrorAction SilentlyContinue
```

- SQL Server listens on `0.0.0.0:1433` and `[::]:1433`.
- SQL Server's Wi-Fi address `192.168.4.32`; GoldenGate Linux `192.168.4.114`.
- Linux `ip route get 192.168.4.32` returned `192.168.4.32 dev enp0s3 src 192.168.4.114 uid 1000`.
- `nc` was not installed; declined optional `nmap-ncat` installation. Used Bash TCP probe:

```bash
timeout 5 bash -c 'echo > /dev/tcp/192.168.4.32/1433' && echo 'SQL SERVER TCP CONNECTED' || echo 'SQL SERVER TCP FAILED'
```

- Result: `SQL SERVER TCP CONNECTED`.

**Scope of this early TCP proof:** A TCP socket opened to `192.168.4.32:1433`. **Later** authenticated ODBC queries proved authentication and SQL execution (Section 14), but neither test proved Replicat compatibility or CDC.

## 6. SQL Server database and security: verified

SSMS connected to `localhost` on the **SQL Server desktop** using Windows Authentication. A disconnected SSMS dialog caused earlier confusion; later query grids verified current state.

Read-only SQL:

```sql
SELECT SERVERPROPERTY('ProductVersion') AS ProductVersion,
       SERVERPROPERTY('Edition') AS Edition,
       SERVERPROPERTY('IsIntegratedSecurityOnly') AS WindowsAuthOnly;
SELECT name, state_desc FROM sys.databases WHERE name = 'GG_TARGET';
SELECT name, type_desc, is_disabled FROM sys.server_principals WHERE name = 'ggadmin';
```

Observed:
- Product version `17.0.1155.3`; Standard Developer Edition (64-bit).
- `GG_TARGET` exists, `ONLINE`.
- `IsIntegratedSecurityOnly = 0`, i.e. Mixed Mode authentication enabled.
- Initially `ggadmin` was absent as server login and database user, although `ggadmin` database **schema** already existed.
- `GG_TARGET` initially showed no user tables (`sys.tables` returned no rows).

Changes performed in SSMS during session:
- Dedicated SQL login `ggadmin` created (password never recorded here).
- `GG_TARGET` database user `ggadmin` created with default schema `ggadmin`.
- `db_owner` role membership granted in `GG_TARGET`.
- `msdb` user `ggadmin` created (conditional script) and assigned `SQLAgentUserRole` (conditional script).

**Final read-only validation in screenshot:**

| Context | Returned data |
|---|---|
| `master.sys.sql_logins` | `ggadmin`, `SQL_LOGIN`, `is_disabled=0` |
| `GG_TARGET.sys.database_role_members` | `db_owner` → `ggadmin` |
| `msdb.sys.database_role_members` | `SQLAgentUserRole` → `ggadmin` |
| `GG_TARGET.sys.schemas` | `ggadmin` exists |

Re-verification queries:

```sql
USE master;
SELECT name,type_desc,is_disabled,default_database_name
FROM sys.sql_logins WHERE name='ggadmin';
GO
USE GG_TARGET;
SELECT r.name AS DatabaseRole,m.name AS MemberName
FROM sys.database_role_members drm
JOIN sys.database_principals r ON drm.role_principal_id=r.principal_id
JOIN sys.database_principals m ON drm.member_principal_id=m.principal_id
WHERE m.name='ggadmin';
GO
USE msdb;
SELECT r.name AS DatabaseRole,m.name AS MemberName
FROM sys.database_role_members drm
JOIN sys.database_principals r ON drm.role_principal_id=r.principal_id
JOIN sys.database_principals m ON drm.member_principal_id=m.principal_id
WHERE m.name='ggadmin';
GO
```

**Security note:** `db_owner` grants broad permissions. It was used in this isolated lab following the role-based GoldenGate preparation. Reassess privileges for production and confirm requirements against the precise supported GoldenGate release. SQL Server Agent service state and actual job functionality remain to be checked; the UI earlier displayed Agent XPs disabled.

## 7. Compatibility and licensing decision

- Installed GoldenGate for SQL Server: `23.26.1.0.1`.
- SQL Server target: **SQL Server 2025**, version 17.x.
- Prior review of Oracle release notes indicated SQL Server 2025 support was introduced with GoldenGate `23.26.2.0.0`. **More importantly, the installed 23.26.1.0.1 build itself explicitly rejected SQL Server 2025 with OGG-05310** in its native database connection validator (Section 14).
- Oracle Software Delivery Cloud screenshot selected `V1054820-01.zip`, *Oracle GoldenGate 23.26.1.0.1 on Linux x86-64 for SQL Server* (~481.4 MB): **identical to installed build, not an upgrade**.
- Oracle support bundle patch mentioned in discussion (`40225919`, claimed `23.26.4.0.2`) was not accessible without paid support entitlement. **Patch ID and applicability should be rechecked against My Oracle Support before use.**
- GoldenGate Free 26ai download page offers separate container images for Oracle and for MySQL/PostgreSQL/SQL Server. It is a **different product/deployment model**, not a drop-in replacement for the conventional installed GoldenGate Microservices home. Its interoperability and licensing restrictions must be checked before integrating with the existing standard deployment.
- **Proposed no-cost remediation:** preserve SQL Server 2025 and configure a separate **SQL Server 2022 Developer Edition** target (VM or suitably isolated supported host). The OGG-05310 error lists SQL Server 2022 among the supported versions; this does not guarantee an end-to-end replication test will pass. No SQL Server 2022 deployment is evidenced yet. The user is considering a hub machine, but host OS and suitability must be verified before installation.

Official links to review at planning time:

- https://www.oracle.com/middleware/technologies/goldengate-downloads.html
- https://www.oracle.com/integration/goldengate/free/download/
- https://support.oracle.com
- https://www.microsoft.com/en-us/sql-server/sql-server-downloads

No entitlement or version-support guarantee is implied by these links.

## 8. Open items and acceptance gates

| Gate | Current status | Verification / action |
|---|---|---|
| Existing Oracle GoldenGate `DEP2` preserved | Previously observed running | Recheck before any maintenance |
| SQL Server GoldenGate `MSSQL_DEP` deployed | Passed | Recheck services after restart |
| SSH browser access | Passed at last check | Validate after Windows sign-out/reboot and VM restart |
| SQL Server 2025 TCP path | Passed | Recheck if IP/network changes |
| SQL Server 2025 `GG_TARGET` online | Passed | Existing desktop remains intact |
| SQL Server 2025 `ggadmin` mapped and roles | Passed | Remote authenticated `isql` session verified identity, user and `db_owner=1` |
| ODBC DSN and runtime `ODBCINI` | **Passed** | `GG_TARGET_DSN`; `isql` authenticated; four MSSQL service processes inherit correct variables |
| GoldenGate DB credential registered | **Passed** | `OracleGoldenGate / GG_TARGET_ALIAS`, user `ggadmin@GG_TARGET_DSN` |
| GoldenGate-native DB validation against SQL Server 2025 | **Blocked (OGG-05310)** | Rejected SQL Server major version 17; **do not retry as a Replicat workaround** |
| Compatible SQL Server target | **Required** | Separate SQL Server 2022 target or entitled compatible GoldenGate update; SQL Server 2025 rejected |
| SQL Server 2022 installation | Not created | Validate intended host OS/resources; decide VM versus standalone host |
| Target table DDL / initial load | Not configured | Define schemas/tables and load strategy |
| Replicat process | Not created | Configure only after version/ODBC/authentication gates pass |
| End-to-end CDC test | Not run | Insert/update/delete, trail delivery, lag/error and reconciliation evidence |

## 9. Proposed SQL Server 2022 target

**Proposal only — not deployed.** VM and separately supported host options were considered. Do not assume the hub machine is Windows until verified.

- VM name: `SQLSERVER2022`; possible Windows Server 2022 guest.
- Developer Edition SQL Server 2022, default instance and stable LAN-reachable IP; TCP 1433.
- Indicative resources: 2–4 vCPU, 6–8 GB RAM, ~80 GB dynamic virtual disk, subject to available host capacity and competing RAC/Data Guard VMs.
- Preserve existing SQL Server 2025 installation and database; do not rename or repurpose its `GG_TARGET` without migration planning.
- Use a **new endpoint and a clearly distinguished DSN**, then create `GG_TARGET` and least-necessary GoldenGate user/roles on the new server after validating vendor-specific prerequisites.
- Bridged networking only if local LAN supports it; otherwise design host-only/NAT routing so GoldenGate Linux can reach SQL Server guest. Do not assume an IP before VM build.

## 10. Suggested evidence capture and repository placement

Suggested path in `oracle-db-platform-automation` repository:

`Oracle-DBA/docs/runbooks/goldengate-sqlserver-lab-2026-11-14.md`

Suggested evidence directory:

`Oracle-DBA/evidence/goldengate-sqlserver/2026-11-14/`

Collect only **redacted** screenshots and saved output (no secrets):

```bash
/u02/ogg_mssql_home/bin/adminclient -v
/u02/ogg_mssql_home/OPatch/opatch lsinventory -oh /u02/ogg_mssql_home
ss -lntp | grep -E ':(7830|7831|7832|7833|7840|7841|7842|7843|7844)\b'
ip -4 addr show
ip route get 192.168.4.32
```

For Windows tunnel evidence:

```powershell
Get-ScheduledTask -TaskName 'GoldenGate-MSSQL-SSH-Tunnel' | Select-Object TaskName,State
Get-ScheduledTaskInfo -TaskName 'GoldenGate-MSSQL-SSH-Tunnel' | Select-Object LastRunTime,LastTaskResult
17840,7841,7842,7843,7844 | ForEach-Object { Test-NetConnection 127.0.0.1 -Port $_ | Select-Object RemotePort,TcpTestSucceeded }
```

## 11. Recovery quick reference

1. **Windows browser `ERR_CONNECTION_REFUSED` at `127.0.0.1:17840`:** Check scheduled task state, local port listeners and `ogg-tunnel.log`; check `ssh -G ogg-mssql`. Do not expose the server to `0.0.0.0` as a shortcut.
2. **Task shown Ready and ports closed:** Inspect `LastTaskResult`, the PowerShell script path, execution policy and task history. Run script interactively for debugging after checking for an existing tunnel to avoid port conflicts.
3. **Task shown Running, but browser shows JSON error:** Test the correct URL root. `HTTP 200` at `/` proves UI endpoint; JSON `OGG-12031` from a bad path is not a tunnel failure.
4. **Linux `nc` unavailable:** Use the Bash `/dev/tcp` probe shown in section 5, or install `nmap-ncat` only if needed.
5. **SSMS disconnected:** Reconnect to `localhost` on the *actual SQL Server desktop* before executing queries. The query text being present is not proof of execution.
6. **ODBC authentication fails:** Confirm target IP/port, `odbc.ini` location and deployment runtime environment, driver registration, SQL login status and SQL authentication mode; capture redacted driver errors. Do not change a working server firewall without evidence.
7. **Replicat blocked by support matrix:** Use version-matched target or supported updated SQL Server GoldenGate binaries. Do not try an undocumented patch or substitute another platform's GoldenGate binaries.

## 12. Change log

| Date | Change/evidence |
|---|---|
| 2026-11-14 | Reinstalled GoldenGate SQL Server into `/u02/ogg_mssql_home`; created `MSSQL_DEP`; observed 7840–7844 services running |
| 2026-11-14 | Configured Windows SSH tunnel, ED25519 key authentication and logon-triggered scheduled task; verified five local ports and HTTP 200 |
| 2026-11-14 | Identified SQL Server 2025 at `192.168.4.32:1433`; validated Linux-to-target TCP connection |
| 2026-11-14 | Verified `GG_TARGET ONLINE`, SQL login `ggadmin` enabled, `GG_TARGET.db_owner`, `msdb.SQLAgentUserRole` |
| 2026-11-14 | Verified GoldenGate SQL Server runtime `23.26.1.0.1`, no interim patches; deferred Replicat due to SQL Server 2025 compatibility risk |
| 2026-11-14 | Verified ODBC DSN, `isql` login, SQL identity and role, live GoldenGate service environment, DB credential creation; native connect failed with **OGG-05310** (SQL Server 2025 unsupported) |
| 2026-11-14 | Proposed SQL Server 2022 Developer as alternative; VM versus separate host not yet selected or deployed |

---

**Next planned change:** Preserve the OGG-05310 incident evidence and GoldenGate deployment backups; establish the intended SQL Server 2022 host operating system and resources before deciding on a VM or standalone installation. No SQL Server 2022 installation has been verified. Do not label future steps complete until supported by command output.

## 13. Completeness audit — outstanding evidence to preserve (2026-11-14)

This appendix records **gaps**, not completed tasks. The earlier sections preserve the substantial verified history; the following items must be captured before calling the environment fully recoverable.

| Priority | Missing evidence or safeguard | Why it matters / next capture |
|---|---|---|
| High | Actual silent-install response file `/home/oracle/software/ogg_mssql_install.rsp` and final `runInstaller` invocation | Critical for reproducible installation; preserve a **redacted** copy only after checking for credentials or host secrets. The observed installation used `./runInstaller -silent -responseFile /home/oracle/software/ogg_mssql_install.rsp`. |
| High | Actual `oggca` deployment inputs, listener settings, Service Manager/admin user configuration | Required to reconstruct `MSSQL_DEP`; gather safely from configuration and UI, redact authentication material. **Runtime ODBCINI is now verified** (Section 14). |
| High | Verified offline backups of `/u02/ogg_mssql_sm` and `/u02/ogg_mssql_deploy` and a tested restore procedure | **Not yet evidenced.** A runbook does not itself preserve application state or passwords. Arrange access-controlled backup before any upgrade or reconfiguration. |
| High | GoldenGate trail paths, deployment names, authentication/credential-store backup and exact source→target trail format | Replication has not started, and source-to-target interoperability was not established. Record when configured; never commit secrets. |
| Completed | SQL login remote authentication through ODBC | **Verified** from Linux as `ggadmin`; `DB_NAME()=GG_TARGET`, `USER_NAME()=ggadmin`, `IS_MEMBER('db_owner')=1` (Section 14). |
| High | GoldenGate build support evidence and failure screenshot | GoldenGate-native validation **explicitly rejected** SQL Server 2025 (`OGG-05310`). Retain redacted screenshot and release notes; validate SQL Server 2022 independently after setup (Section 14). |
| Medium | Full effective Windows SSH config, task XML export, script checksum and log retention policy | Runbook includes the core configuration, not a byte-for-byte recovery image. Export with account/host identifiers reviewed and restrict sensitive details. |
| Medium | Reboot/sign-in auto-recovery proof for Windows tunnel, plus Linux GoldenGate startup after VM reboot | Port tests and HTTP 200 establish the live state, not persistence across reboot. |
| Medium | Exact software archive checksum, stage path and prerequisite checklist | Needed for provenance and reproducible reinstall; installation zip identifier seen was `V1054820-01.zip`. |
| Medium | Resource baseline and VirtualBox host network topology | Must capture before provisioning SQL Server 2022 VM to avoid contention with RAC / Data Guard VMs. |
| Medium | Tested SQL Server `GG_TARGET` database backup and scripted logins/permissions without plaintext passwords | Separate persistence/restore control; no successful backup or restore test was shown. |
| Medium | Evidence artifacts in Git with redaction review and commit identifier | The Markdown file is local; there is no verified repository commit or off-host copy. |

**Operational rule:** Before upgrading, uninstalling, or creating the new target VM, separately back up configuration/state and validate recovery. Do not present this Markdown document as a substitute for those backups.

**Accuracy note:** Credential **registration** and successful standalone ODBC authentication are verified, but GoldenGate-native authentication **was blocked by version validation**. Complete service continuity, reboot survivability, source trails, recovery backups, and CDC remain unverified. Add evidence and dates as checks finish.


## 14. SQL Server 2025 integration attempt — complete checkpoint through OGG-05310 (2026-11-14)

**Outcome:** Verified ODBC authentication, authorization, GoldenGate service environment and credential registration; **failed at GoldenGate-native SQL Server version validation**. This is the definitive lab roadblock; do not misattribute it to networking, login, DSN, or firewall.

### 14.1 ODBC configuration created and inspected — PASS

As Linux user `oracle` on `stb23ai`, inspected the bundled driver at `/u02/ogg_mssql_home/msodbc/odbcinst.ini`, then created `/u02/ogg_mssql_home/msodbc/odbc.ini`:

```ini
[GG_TARGET_DSN]
Driver=Microsoft ODBC Driver for SQL Server
Server=tcp:192.168.4.32,1433
Database=GG_TARGET
Encrypt=yes
TrustServerCertificate=yes
```

Interactive validation environment:

```bash
export OGG_HOME=/u02/ogg_mssql_home
export ODBCSYSINI=$OGG_HOME/msodbc
export ODBCINI=$OGG_HOME/msodbc/odbc.ini
command -v isql || true
command -v sqlcmd || true
command -v odbcinst || true
```

Observed `/usr/bin/isql` and `/usr/bin/odbcinst` present; `sqlcmd` was not present in PATH. The driver identified itself during the SQL error message as **Microsoft ODBC Driver 18 for SQL Server**. `TrustServerCertificate=yes` is a lab convenience that bypasses server-certificate validation; replace with a correctly validated TLS configuration for production.

### 14.2 Authentication and SQL authorization through Linux ODBC — PASS

After prompting for the existing `ggadmin` password without echo, executed `isql -v GG_TARGET_DSN ggadmin "$GG_PASS"`; output: **`Connected!`**. Queries and observed results:

```sql
SELECT DB_NAME();
-- GG_TARGET
SELECT @@VERSION;
-- Microsoft SQL Server 2025 (RTM-GDR) KB5132748, 17.0.1155.3 (X64)
-- Standard Developer Edition (64-bit) on Windows 10 Pro
SELECT SYSTEM_USER AS LoginName, USER_NAME() AS DatabaseUser, DB_NAME() AS DatabaseName;
-- ggadmin | ggadmin | GG_TARGET
SELECT IS_MEMBER('db_owner') AS IsDbOwner;
-- 1
```

The initial `isql` command `clear screen` produced `Could not find stored procedure 'clear'` because it was sent as SQL; this is **not** a driver, network, or authorization failure. End `isql` with `quit`, then `unset GG_PASS`. Avoid printing secrets or capturing shell history with plaintext passwords.

### 14.3 GoldenGate deployment configuration and live process environment — PASS

Initial read-only inspection:

```bash
ls -ld /u02/ogg_mssql_deploy/etc/conf
find /u02/ogg_mssql_deploy/etc/conf -maxdepth 2 -type f -printf '%p\n'
grep -RniE 'ODBCINI|ODBCSYSINI|LD_LIBRARY_PATH' /u02/ogg_mssql_deploy/etc/conf 2>/dev/null
```

Found `etc/conf/ogg/GLOBALS` and `etc/conf/deploymentConfiguration.dat`; `grep` returned no text matches. **Do not treat the absence of text matches as absence of service environment**; do not hand-edit `deploymentConfiguration.dat`.

The Service Manager web UI at `http://127.0.0.1:17840/`, deployment **MSSQL_DEP → Configuration**, displayed:

| Variable | UI configuration |
|---|---|
| `ODBCSYSINI` | `${OGG_HOME}/msodbc` |
| `ODBCINI` | `${OGG_HOME}/msodbc/odbc.ini` |
| `LD_LIBRARY_PATH` | `${OGG_HOME}/lib:/u02/ogg_mssql_home/lib:/u01/app/oracle/product/26ai/dbhome_1/lib` |

The actual process environment was inspected with:

```bash
for pid in $(pgrep -u oracle -f 'adminsrvr|distsrvr|recvsrvr|pmsrvr'); do echo "PID=$pid"; tr '\0' '\n' < /proc/$pid/environ 2>/dev/null | grep -E '^(OGG_HOME|ODBCSYSINI|ODBCINI)='; done
```

**Observed separation:**

- Oracle deployment processes: PIDs `1795`, `1803`, `1813`, `1820`; `OGG_HOME=/u02/ogg26ai_home`; no matching ODBC variables shown.
- SQL Server `MSSQL_DEP` processes: PIDs `234191`, `234193`, `234195`, `234198`; each reported `OGG_HOME=/u02/ogg_mssql_home`, `ODBCSYSINI=/u02/ogg_mssql_home/msodbc`, `ODBCINI=/u02/ogg_mssql_home/msodbc/odbc.ini`.
- PIDs are evidence from that instant, **not persistent identifiers**. No environment change or restart was needed.

### 14.4 GoldenGate native DB credential registered — PASS (registration only)

In `MSSQL_DEP` Administration Server at Windows-forwarded `http://127.0.0.1:7841/services/v2/content/`, logged in as GoldenGate management user `oggadmin`. The deployment dashboard showed **zero** Extracts, Replicats and transport paths and **no displayed critical events** before the native test.

Used **DB Connections → Add DB Connection**, with:

| Form field | Recorded choice |
|---|---|
| Credential Domain | `OracleGoldenGate` |
| Credential Alias | `GG_TARGET_ALIAS` |
| Connection Type | Data Source Name (DSN) |
| DSN | `GG_TARGET_DSN` |
| User ID | `ggadmin` (SQL Server login; distinct from web user `oggadmin`) |
| Password | Existing SQL Server login password, **not recorded** |

After Submit, the connection list showed `OracleGoldenGate`, alias `GG_TARGET_ALIAS`, user ID `ggadmin@GG_TARGET_DSN`. **Saving a credential proves registration, not that GoldenGate successfully validated the target.**

### 14.5 GoldenGate-native connection validation — FAIL / definitive roadblock

Clicked the first **Connect to Database** action in the DB Connections row. The UI raised:

```text
The handler method registered for 'GET
/services/v2/credentials/OracleGoldenGate/GG_TARGET_ALIAS/valid' caused an exception:
OGG-05310 - Oracle GoldenGate does not support SQL Server version 17.0.1155.
Supported versions are SQL Server 2014, SQL Server 2016, SQL Server 2017,
SQL Server 2019, SQL Server 2022.

Code: OGG-12025
Cause: The handler method caused an exception. See error messages for details.
Action: Contact Oracle GoldenGate Support.
```

**Root cause (confirmed from GoldenGate's own error):** installed GoldenGate for SQL Server `23.26.1.0.1` excludes SQL Server 2025 (major version `17`) in its native database-version validation. Microsoft ODBC connectivity and SQL login security are operational. No evidence suggests firewall, DSN, or password is the blocker.

**Disposition:** Stop SQL Server 2025 Replicat setup; preserve registered alias as reference but do not assume it is usable. Do not falsify server version, bypass checks, or change production-impacting settings. Plan one of: (a) separate SQL Server 2022 Developer target, explicitly listed in the rejection message, with a fresh test against its endpoint; or (b) an entitled GoldenGate build supporting SQL Server 2025. Oracle GoldenGate Free containers are a separate edition and should not be treated as a drop-in replacement without confirming licensing/interoperability.

### 14.6 Recovery and continuation checklist

1. Preserve original SQL Server 2025 desktop `DESKTOP-7A1862B` (`192.168.4.32`) and `GG_TARGET`; do not uninstall or downgrade.
2. Preserve both GoldenGate software homes, Service Managers and deployment directories.
3. Make access-controlled backups of `/u02/ogg_mssql_sm` and `/u02/ogg_mssql_deploy`; export/redact task and installation response-file evidence separately. **Not yet shown as complete.**
4. Confirm the operating system, capacity, network and intended role of the proposed *hub machine* before deciding how to install SQL Server 2022. No new host or VM was installed during this checkpoint.
5. Once a compatible target exists, test TCP and ODBC first, use a distinct DSN (e.g., `GG_TARGET_2022_DSN`) to preserve this baseline, register a new alias, and validate it through the native Connect action before any Replicat creation.
6. Collect evidence for target DDL, trail delivery, checkpoint table creation, Replicat state and insert/update/delete reconciliation before claiming end-to-end CDC. **None of these were verified by the SQL Server 2025 attempt.**

**Security/control note:** A successful `isql` session shows standalone database authentication, but a stored GoldenGate credential does not prove the GoldenGate connection succeeded. Separate the two in audit and incident records.