# Oracle RAC Lab Incident Report — Node 2 Root-Script VM Freeze

**Project:** Oracle Database Platform Automation  
**Environment:** Two-node Oracle 26ai Grid Infrastructure lab on Oracle Linux 9 / VirtualBox  
**Incident period:** October 18, 2026 (CDT)  
**Status:** Root-script retry and Clusterware recovery succeeded; host hypervisor correction in progress, not yet confirmed  
**Type:** Independent lab incident, not an employer production outage

## Executive summary

Node 2's first Grid root script failed with `CLSRSC-117` at checkpoint `ROOTCRS_STACK` after its VM froze for about 71 minutes. I reran the root script and it succeeded. Both VMs were running through Hyper-V "snail mode" rather than native VT-x. I identified that host virtualization path and CPU contention as the leading explanation; the final Windows correction is not yet confirmed.

I completed Phases 0–7 of the RAC runbook, including Grid/ASM OCR and Clusterware checks. Phases 8–12 are not run: DATA/FRA diskgroups, database software, DBCA and database availability validation are not completed.

## Observed symptoms and evidence

- Node 2's root script stalled while starting the CRS stack.
- VBox.log reported a heartbeat lost for 4292 seconds and timer catch-up being given up.
- Both VM logs reported `VT-x is not available` and `Snail execution mode is active`.
- The host has four physical cores; the two guests each had two vCPUs, with Windows and the installer sharing the host.
- The first run ended with `CLSRSC-117`; the retry ended with `CLSRSC-325` success.

**Evidence limitation:** The timeline and log messages below are my build record supplied for this report. Raw logs were not attached to this update or committed with it. No independent replay of the failure is claimed.

## Investigation sequence and timeline

All times are CDT on October 18, 2026.

| Time | Event |
|---|---|
| 09:37:55 | Root script starts the CRS stack on node 2 |
| About 09:38–10:50 | VM frozen; VBox.log records heartbeat loss of 4292 s and timer catch-up abandoned |
| 10:52:46 | `CLSRSC-117`; `ROOTCRS_STACK` checkpoint fails |
| 10:57:53 | Root-script rerun starts |
| 11:00:45 | StartCluster completes in 42 seconds |
| 11:00:50 | `CLSRSC-325` reports success |
| 11:08 | Installer ends with `INS-43080`; post-install CVU findings are SCAN/DNS only |

## Root cause and confidence

The immediate failure was a prolonged VM freeze while the root script was waiting for Clusterware startup. Both VMs were using Hyper-V "snail mode", a known source of VirtualBox performance degradation. Windows Virtual Machine Platform, used by WSL2/Docker Desktop, was the suspected trigger for the Windows hypervisor on this host. CPU contention on the four-core host was an additional likely contributor.

I have not isolated which Windows feature started the hypervisor or proved that disabling it prevents recurrence. Snail mode remained after the first `bcdedit` attempt. The host-layer explanation is supported by my reported logs, but the exact trigger and permanent fix remain unconfirmed. [VirtualBox's Hyper-V troubleshooting guidance](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/Troubleshooting.html) supports checking Windows virtualization features and VBS; it does not establish this incident's cause by itself.

## Follow-on cluster recovery

`CRS-4405` blocked `crsctl stop cluster -all`: each node's High Availability Services could not see the other. I stopped CRS locally on both nodes with `crsctl stop crs`, confirmed the stopped state, then started both again. Cluster membership recovered.

Node 2's VIP remained failed over to node 1. Once node 2 was healthy, I relocated it with srvctl and checked the VIP/listener resources. The listener restarted automatically; an "already running" PRCZ-4054 message was harmless in that confirmed state.

## Commands captured in the investigation

From an elevated Windows terminal, followed by a Windows reboot:

```powershell
bcdedit /set hypervisorlaunchtype off
```

Rollback of that boot setting is `bcdedit /set hypervisorlaunchtype auto`, followed by reboot. This change affects WSL2/Docker availability; VBS and related Windows feature settings still need checking.

On each node as root, when the cluster-wide stop failed:

```bash
crsctl stop crs
crsctl check crs
crsctl start crs
crsctl check cluster -all
crsctl stat res -t
```

I confirmed both nodes were stopped before starting them again. `CRS-4639` was the expected local stopped-state result.

As grid after node 2 recovered:

```bash
srvctl config vip -node racnode2
srvctl relocate vip -vip racnode2-vip -node racnode2
crsctl stat res ora.racnode2.vip ora.LISTENER.lsnr -t
```

## Corrective actions and verification

| Action | Status / acceptance check |
|---|---|
| Disable hypervisor launch and reboot | In progress; first attempt did not remove snail mode. Check fresh logs for native hardware virtualization |
| Set Windows sleep to Never during lab runs | Added to the runbook after the host suspended overnight; verify the active power plan |
| Check VBox.log before long install steps | Added to the runbook; repeat for both VMs |
| Retain logs before VM restart | Copy before the next start because VirtualBox rotates logs |
| Verify installed cluster name | Pending `cemutlo -n`; intended name is `raccluster` |

## Evidence to preserve and redact

- Each VM's VBox.log covering the freeze and retry, using a redacted path such as `C:\Users\<user>\...`; remove usernames, MACs, VM UUIDs, machine-ids and boot IDs.
- Node 2 root logs under `/u01/app/grid/crsdata/racnode2/crsconfig/rootcrs_racnode2_*.log`, plus the matching node 1 logs; remove credentials and disk serials.
- Installer and pre/post-install cluvfy logs, including the SCAN PRVH-1558 / PRVG-1101 findings.
- Timestamped `crsctl check cluster -all`, resource table, VIP/SCAN configuration and relocation output from both nodes.
- Fresh post-correction VBox.log from each VM, needed before declaring the hypervisor issue fixed.

These are evidence sources to archive, not a claim that sanitized files are already in the repository. Preserve installer/cluvfy logs out of `/tmp` before reboot. Review response files and screenshots separately for secrets and desktop details.

## Outcome and lessons

The root-script retry succeeded and Clusterware membership, VIP recovery and SCAN resource relocation were tested. SCAN relocation does not establish database/application failover: no RAC database exists yet. Grid installation completed with the documented hosts-file SCAN/DNS exception; use DNS/GNS for a properly resolved SCAN configuration.

The next host task is to prove native hardware virtualization in fresh logs before more long-running steps. Keep the runbook Draft until the remaining phases and acceptance tests are complete.

## Portfolio / LinkedIn context

This is independent lab troubleshooting, not production incident ownership. The [26ai build runbook](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/blob/docs/rac26-build-updates/docs/runbooks/oracle-rac/oracle26ai-2node-rac-build-runbook.md) records the implementation steps; the [controlling roadmap](../ROADMAP.md) separates completed work from planned automation.
