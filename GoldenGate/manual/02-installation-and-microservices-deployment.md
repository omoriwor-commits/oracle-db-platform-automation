# 02 — Installation and Microservices Deployment

**Scope:** Oracle GoldenGate 26ai software installation, OGGCA deployment creation, Linux service lifecycle, security and acceptance checks. Paths and process names are examples. Executed deployment evidence belongs in the project records.

## 1. Software home versus deployment home

Installing GoldenGate creates a software home (`OGG_HOME`). Oracle GoldenGate Configuration Assistant (`oggca.sh`) configures Service Manager and replication deployments. Service Manager can administer multiple local deployments.

```text
Linux host
  /u01/app/ogg/ogg26ai   Example GoldenGate software home
  /u02/ogg/srvmgr        Example Service Manager runtime home
  /u02/ogg/DEP1          Example replication deployment home
```

Keep executable files distinct from writable deployment state, trail storage and logs. Actual Oracle variables and home locations depend on installation choices, so never assume these example directories exist on a particular host.

## 2. Read-only host preflight

Run as an approved OS account; record output in a sanitized installation inventory.

```bash
hostnamectl
cat /etc/os-release
uname -r
id
groups
df -hT
lsblk -f
free -h
ip -br addr
ss -lnt
```

Confirm the exact GoldenGate build, Oracle source/target releases, compatible Linux version, hardware, OS permissions, database network connectivity, trail volume estimates, and TLS/certificate/port plan before installation.

## 3. OS ownership and deployment layout

The Linux installation user, GoldenGate service administrator, and Oracle database capture/apply accounts have different responsibilities and should not be conflated.

Example filesystem provisioning (**not an instruction to run without approval**):

```bash
# sudo install -d -o <gg_os_user> -g <gg_os_group> -m 0750 /u02/ogg/srvmgr
# sudo install -d -o <gg_os_user> -g <gg_os_group> -m 0750 /u02/ogg/DEP1
```

Plan ownership, runtime write permissions, log retention, trail capacity, secure backups and service restart authority. Never publish wallets, private keys, passwords or completed secret-bearing response files.

## 4. Install software and identify its build

Oracle documents interactive and silent installation options; commands depend on the actual distribution and installer supplied with the selected release. Confirm the supported 26ai installer package and documented response-file syntax before using automation.

**Software-home verification after approved installation:**

```bash
test -x "$OGG_HOME/bin/oggca.sh" && echo "OGGCA available"
test -x "$OGG_HOME/bin/adminclient" && echo "Admin Client available"
ls -ld "$OGG_HOME"
```

Presence of binaries is not proof that OGGCA or a deployment has been configured. Retain the installer version, log, software inventory and installation approvals.

[Oracle GoldenGate deployment documentation](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/deploy.html).

## 5. Configure Service Manager and deployment with OGGCA

From the **approved** GoldenGate software home:

```bash
cd "$OGG_HOME/bin"
./oggca.sh
```

During configuration select Service Manager mode (manual/daemon/XAG as supported), deployment identity, administration/receiver/metrics ports, runtime home, source/target service connectivity, security and TLS.

For repeatable unattended deployments, use an Oracle 26ai-compatible **complete response file**. The reference command structure is:

```bash
# Only after preparing and securing a valid response file:
./oggca.sh -silent -responseFile /secure/path/deployment.rsp
```

A sample syntax line is not independently executable without a valid file and actual host prerequisites. Never reuse another deployment's populated response file without checking embedded secrets, paths and ports.

References: [Silent deployment](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/deploy-silent-deployment.html) and [OGGCA response template](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/reference-oggca-sample-file-silent-deployment.html).

## 6. Service Manager lifecycle

Confirm the selected lifecycle owner **before** issuing START or STOP.

| Mode | Lifecycle owner | Operational requirement |
|---|---|---|
| Manual | GoldenGate Service Manager scripts | Correct runtime environment and service directories |
| Daemon/systemd | Linux service manager | Verify actual unit name and systemd configuration |
| XAG | Oracle Grid Infrastructure Agent | Use supported Clusterware/XAG resource operations |

### Daemon-mode inspection

```bash
systemctl status OracleGoldenGate --no-pager
systemctl is-enabled OracleGoldenGate
systemctl cat OracleGoldenGate
journalctl -u OracleGoldenGate -n 80 --no-pager
```

### Change-controlled daemon operations

```bash
sudo systemctl start OracleGoldenGate
sudo systemctl stop OracleGoldenGate
```

These commands are valid only where the unit is present and daemon mode owns the service lifecycle.

### Manual mode

```bash
"$OGG_SRVMGR_DIRECTORY/bin/startSM.sh"
"$OGG_SRVMGR_DIRECTORY/bin/stopSM.sh"
```

Use only when the installed manual-mode scripts and required environment exist. Do not mix systemd, direct scripts and XAG controls on the same service lifecycle.

[Oracle: Start and Stop Service Manager](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/deploy-start-stop-sm.html).

## 7. Secure deployment acceptance

| Component | Evidence to collect |
|---|---|
| Software | Installed exact release/build and installer success log |
| Service Manager | Correct lifecycle owner and healthy service |
| Administration Service | Authenticated and scoped operator access |
| Distribution and Receiver | Expected ports, listeners and approved TLS/WSS |
| Performance Metrics | Monitoring access and expected service health |
| Storage | Runtime directory ownership, log/trail capacity and retention |
| Database connectivity | Correct service aliases and container context |
| Recovery | Approved service restart/failover runbook and result |

**Security:** Prefer TLS and role-scoped users; do not expose internal GoldenGate service ports publicly without deliberate controls. Secure credential stores using Oracle-supported administration, not direct wallet copying.

## 8. OGGCA service registration incident

A separately documented [GoldenGate Microservices incident](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/main/docs/goldengate/troubleshooting/goldengate-26ai-oggca-daemon-registration-troubleshooting.md) concerned a DEP1 deployment whose Admin, Distribution, Receiver and Metrics processes remained alive after Service Manager stopped. OGGCA could not safely register the deployment while conflicting processes and ports remained.

Read-only triage:

```bash
systemctl status OracleGoldenGate --no-pager
ss -lntp
ps -ef | grep -E 'adminsrvr|distsrvr|recvsrvr|pmsrvr|ServiceManager' | grep -v grep
```

Correlate PIDs, port ownership, process ancestry, configured homes and logs. Do not blindly kill process groups, destroy deployment directories or transplant credential wallets. This incident is recorded separately; it is not evidence that a fresh deployment test was executed as part of the field guide.

## 9. Acceptance and recovery record

- [ ] Supported GoldenGate/Oracle/Linux combination confirmed.
- [ ] Installer output and deployed software build archived.
- [ ] Service Manager mode and deployment home recorded.
- [ ] TLS, administrative authorization and listener exposure reviewed.
- [ ] Runtime directories are writable by approved identities.
- [ ] Admin/Distribution/Receiver/Metrics services verified.
- [ ] Service restart/recovery behavior recorded from controlled testing.
- [ ] No end-to-end replication claim made until Extract, transport, Replicat and target rows are validated.


## Oracle references

- [Deployment guide](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/deploy.html)
- [Silent deployment](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/deploy-silent-deployment.html)
- [Response file example](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/reference-oggca-sample-file-silent-deployment.html)
- [Service Manager lifecycle](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/deploy-start-stop-sm.html)

**Next:** [03 — Oracle Database Preparation](03-oracle-database-preparation.md)
