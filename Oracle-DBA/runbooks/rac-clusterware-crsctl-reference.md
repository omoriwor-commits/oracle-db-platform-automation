# Oracle Clusterware (crsctl) Reference for a Two-Node RAC

**Last updated:** 2026-10-19
**Status:** Verified on my two-node Oracle 26ai RAC lab (Grid 23.26.1, Oracle Linux 9.8, VirtualBox). Lab work, not production.

Many crsctl cheat sheets online mix cluster commands with Oracle Restart commands, which only apply to Grid on a single server. This page is the set I actually use on my cluster, with the mistakes I found in common lists.

## Who runs what

| Task | User |
| ---- | ---- |
| Status and check commands | grid (the Grid `bin` directory is on grid's PATH) |
| Stop, start, enable and disable the stack | root, with the full path `/u01/app/23.26/grid/bin/crsctl` |

## Status checks

| Task | Command |
| ---- | ------- |
| Full stack on the local node (High Availability Services, CRS, CSS, EVM) | `crsctl check crs` |
| Cluster stack on all nodes | `crsctl check cluster -all` |
| Cluster stack on one node | `crsctl check cluster -n racnode2` |
| All cluster resources | `crsctl stat res -t` |
| Low-level (init) resources on the local node | `crsctl stat res -t -init` |
| Server state | `crsctl stat server -f` |
| Nodes with number, status and pinning | `olsnodes -n -s -t` |
| Active Clusterware version | `crsctl query crs activeversion` |

## Stop and start

| Task | Command (root) |
| ---- | -------------- |
| Stop the cluster stack on all nodes | `crsctl stop cluster -all` |
| Stop everything on this node, including High Availability Services | `crsctl stop crs` |
| Start everything on this node | `crsctl start crs` |
| Start the cluster stack on all nodes (High Availability Services must already be running on each) | `crsctl start cluster -all` |
| Check, enable or disable auto-start at boot | `crsctl config crs`, `crsctl enable crs`, `crsctl disable crs` |

`stop cluster` stops the Clusterware stack and can act on other nodes, but leaves High Availability Services running. `stop crs` stops the whole stack, High Availability Services included, and only on the node where you run it.

## Common mistakes in online cheat sheets

| Seen online | Problem |
| ----------- | ------- |
| `crsctl stop has` / `start has` / `enable has` | Oracle Restart commands. On a cluster use the `crs` equivalents. |
| `crsctl stop has -n rac2` | `has` commands are local only; there is no `-n` option. Log in to the node and run `crsctl stop crs`. |
| "`stop cluster -n rac2` stops CRS and HAS" | It doesn't stop High Availability Services. |
| `–n`, `–all` copied from a web page | En dashes, not hyphens. Pasted, they fail. Type `-n` and `-all`. |
| `./crsctl` | Assumes you're in the Grid `bin` directory. Use the PATH (grid) or the full path (root). |

## What I saw on my cluster

- After node 2's root script failed during a VM freeze and was rerun, each node could only see itself. `crsctl check cluster -n racnode2` from node 1 returned `CRS-4405: The following nodes are unknown to Oracle High Availability Services`, and `crsctl stop cluster -all` failed with the same error.
- I stopped each node instead with `crsctl stop crs` as root. Each ended with `CRS-4133: Oracle High Availability Services has been stopped`, and `crsctl check crs` then returned `CRS-4639: Could not contact Oracle High Availability Services`.
- After a clean start of both nodes, `crsctl check cluster -all` listed both nodes again and `stop cluster -all` worked.
- When I stopped node 1 first, Clusterware moved its SCAN VIPs and SCAN listeners to node 2 before shutting down, which is SCAN failover working as designed.
- During the incident, `crsctl stat res -t -init` on node 2 showed which low-level resources (`ora.cssd`, `ora.gpnpd`, `ora.mdnsd`) had come up.

## Related

- [OCR and OLR administration](ocr-olr-administration.md)
- 26ai RAC build runbook and incident report: see the RAC section of the main README.
