# Oracle RAC Lab Incident Report — Node 2 Startup Failure

**Project:** Oracle Database Platform Automation  
**Environment:** Two-node Oracle RAC lab on Oracle Linux / VirtualBox  
**Incident period:** October 2026  
**Status:** Resolved — root cause confirmed  
**Type:** Independent lab incident, **not** an employer production outage

## Executive summary

In a previously functioning two-node Oracle RAC lab, node 2 failed to start or become available while node 1 remained running. Investigation covered VirtualBox/virtualization configuration, Linux boot behavior, service failures, network reachability and cluster-level symptoms. Node 2 subsequently returned to a healthy operating-system state while SELinux was disabled. The root cause is now confirmed by the owner: the active Windows Hyper-V hypervisor made VirtualBox run in snail mode, starving the RAC VMs of CPU, with memory pressure on top. The record does not establish that all Oracle Clusterware, ASM and database resources were restored to their intended state.

## Observed symptoms and evidence

- Node 2 was unavailable or stuck during boot; node 1 remained running.
- Troubleshooting considered virtualization settings, including the VirtualBox environment.
- On Oracle Linux, `systemctl --failed` showed:
  - `vboxadd-service.service` — failed
  - `vboxadd.service` — failed
- `systemctl status dbus --no-pager -l` was used to check the D-Bus service; it was active in the captured output.
- SELinux was subsequently set to disabled and node 2 was reported healthy.

**Evidence limitation:** These observations do not demonstrate that the failed VirtualBox Guest Additions units caused the RAC outage, nor that SELinux policy was the root cause. Earlier cluster and network errors should be preserved with timestamped outputs before assigning a definitive root cause.

## Investigation sequence

1. **Scope the failure:** Distinguish host boot/network availability from Oracle Clusterware, ASM and database instance health.
2. **Inspect the virtualization layer:** Review VirtualBox host/guest configuration and any host virtualization conflicts.
3. **Inspect Linux boot and services:** Check failed units, D-Bus and journal logs.
4. **Inspect security configuration:** Note SELinux mode and any relevant audit denials.
5. **Restore basic host availability:** Confirm node 2 can boot and be reached.
6. **Verify database platform recovery separately:** Check cluster membership, ASM, database resources and application connectivity before declaring RAC recovered.

## Commands captured in the investigation

```bash
systemctl --failed
systemctl status dbus --no-pager -l
```

## Suggested verification commands (not claimed as already executed)

Run as appropriate for the installed Grid Infrastructure/database versions and configured users:

```bash
hostnamectl
getenforce
systemctl --failed
journalctl -b -p warning --no-pager
# As Grid Infrastructure owner, if clusterware is running:
crsctl check cluster -all
crsctl stat res -t
olsnodes -n -s
# As database owner, with appropriate environment:
srvctl status database -d <db_unique_name>
```

Record output and timestamps from both nodes. Confirm listener/service accessibility and that the expected ASM disk groups and database instances are online.

## Security and root-cause follow-up

**Do not treat disabling SELinux as the recommended permanent production fix.** For a future controlled lab investigation:

- Preserve `/var/log/audit/audit.log` and `ausearch -m AVC -ts recent` output, if audit data exists.
- Determine whether an actual SELinux denial prevented a required process or file access.
- Check filesystem labels and supported Oracle/VirtualBox configurations.
- Develop and test a narrowly scoped correction, then validate with SELinux enforcing if the environment supports it.
- Keep Guest Additions failures separate from Clusterware failure until a causal connection is demonstrated.

## Root cause (confirmed)

The Windows Hyper-V hypervisor was active on the host, so VirtualBox ran in snail mode and the RAC VMs were starved of CPU, with memory pressure on top. Turning the hypervisor off (`bcdedit /set hypervisorlaunchtype off`, then reboot) stopped the starvation. The same cause was confirmed in the [October 18, 2026 Oracle 26ai RAC incident](2026-10-18-rac26-node2-root-script-vm-freeze.md). Confirmed by the owner; the original 19c VMs have since been deleted.

## Outcome and lessons

**Confirmed:** Node 2 was reported healthy after troubleshooting, with SELinux disabled.  
**Not confirmed:** Final cluster-wide RAC, ASM, database service health; specific SELinux denial; production-safe remediation.

Lessons:
- A RAC incident can span database, cluster, operating-system, networking, storage and virtualization layers.
- Host recovery is not equivalent to complete database service recovery.
- A recovery workaround and a verified root cause are different.
- Document observed evidence, corrective actions, follow-up tests and security trade-offs.

## Next evidence to add

- [ ] Redacted, timestamped node 1 and node 2 status outputs
- [ ] Clusterware resource table and node membership after recovery
- [ ] ASM disk group and database instance verification
- [ ] SELinux audit evidence or explicit finding that none was available
- [ ] Final root-cause conclusion, only if supported by logs
- [ ] Reproducible corrective procedure and rollback steps

## Portfolio / LinkedIn context

This is an **independent Oracle RAC troubleshooting lab case study**, part of the [Oracle Database Platform Automation roadmap](../ROADMAP.md). It demonstrates diagnostic process and evidence discipline, not production incident ownership.

**Principle:** Learn → Build → Prove.
