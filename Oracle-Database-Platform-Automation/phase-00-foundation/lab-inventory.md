# Lab Inventory

Every server, VM and cloud account this project uses or has used. No IP addresses, OCIDs or account IDs are recorded here (see [security-rules.md](security-rules.md)). Items marked **TODO** still need to be confirmed from the machines or consoles.

Last reviewed: 2026-10-19

## Local lab (VirtualBox)

| Host | Role | OS | Database / software | Status |
|---|---|---|---|---|
| Physical host | Runs all local VMs | TODO | VirtualBox version TODO; CPU / RAM / disk TODO | Active |
| `racnode1` | Active 26ai RAC node 1 (`rac26node1` VM) | Oracle Linux 9.8; UEK 6.12.0-207.111.5.4.el9uek.x86_64 | Grid/DB 23.26.1, +ASM1, RAC1, RACPDB1 | OPEN; PDB READ WRITE; validated 2026-10-19 |
| `racnode2` | Active 26ai RAC node 2 (`rac26node2` VM) | Oracle Linux 9.8; UEK 6.12.0-207.111.5.4.el9uek.x86_64 | Grid/DB 23.26.1, +ASM2, RAC2, RACPDB1 | OPEN; PDB READ WRITE; validated 2026-10-19 |
| 19c primary (hostname TODO) | Migration 1 source | Oracle Linux 7.9 | Oracle 19c, PDB `PRODBHR` | TODO |
| 19c standby (hostname TODO) | Physical standby | Oracle Linux 7.9 | Oracle 19c Data Guard | TODO |
| 26ai host (hostname TODO) | Migration 1 target, Migration 2 source | Oracle Linux 9.8 | Oracle AI Database 26ai (`PDB23AI`), GoldenGate 26ai | TODO |

The former 19c RAC VMs were deleted; these rows describe the new 26ai VMs using the same OS hostnames. Each has 10 GB configured RAM, 2 vCPUs and a 100 GB OS disk. RAC shared storage: OCR 20 GB, DATA 40 GB and FRA 30 GB, mounted on both ASM instances in the supplied October 19 output.

Outstanding: HugePages are unconfigured. The running UEK8/23.26.1 combination is below Oracle's documented 23.26.2 minimum for OL9 UEK8. The completed lab build does not resolve that compatibility gap. See the [26ai incident](../incident-reports/2026-10-18-rac26-node2-root-script-vm-freeze.md); the earlier [19c incident](../incident-reports/2026-10-rac-node2-startup-investigation.md) keeps its separate historical status.

## Cloud accounts

| Cloud | Used for | Region | Resources | Status | Budget alert |
|---|---|---|---|---|---|
| OCI | Migration 2 target, Migration 3 source | us-chicago-1 | Compute VM (Oracle 26ai), VCN, DRG, Site-to-Site VPN | Shut down; TODO confirm terminated or stopped | TODO; not yet evidenced |
| Azure | Migration 3 GoldenGate hub and SQL Server target | East US | Resource group with SQL Server VM, GoldenGate VM, VPN gateway, NSGs | Shut down; TODO confirm resource group deleted | $50/month, alerts at 50/75/90/100% (Aug 2026); TODO confirm still active |
| AWS | Not used by this project yet (planned extension) | n/a | None | Not in use | Set before first use |

## Cost note

An Azure VPN gateway bills by the hour whether or not the VMs run. If "shut down" meant only deallocating the VMs, check that the VPN gateway and its public IP were deleted too.
