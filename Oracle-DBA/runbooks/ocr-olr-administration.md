# OCR, OLR and Voting File Administration (Oracle 26ai RAC)

**Last updated:** 2026-10-19
**Status:** Draft. The commands below are planned for my two-node 26ai RAC lab; the ones marked **Verify** have not been run yet. Log locations are confirmed from my cluster.

The Oracle Cluster Registry (OCR) holds the cluster configuration: nodes, resources, VIPs, SCAN and database registrations. Each node also has an Oracle Local Registry (OLR) with the information it needs to start before the OCR is reachable. Voting files decide node membership.

Much of the material online is from 11g. The commands still work, but backup defaults, the OLR location and the log layout have changed.

## My cluster

| Item | Value |
| ---- | ----- |
| OCR and voting file | ASM disk group `+OCR`, external redundancy, one 20 GB disk |
| Grid home | `/u01/app/23.26/grid` |
| Grid base | `/u01/app/grid` |
| OLR location | Read from `/etc/oracle/olr.loc` (don't assume a path) |

## Checks (run as root)

As grid, `ocrcheck` skips the logical corruption check, and `ocrdump` needs root, so run these as root with the full path.

```bash
G=/u01/app/23.26/grid/bin
$G/ocrcheck                         # OCR integrity, including the logical check
$G/ocrcheck -local                  # this node's OLR
cat /etc/oracle/olr.loc             # OLR file location and crs_home
$G/crsctl query css votedisk        # voting files
```

**Verify** expected results: OCR in `+OCR`, integrity check succeeded, one voting file.

## Backups (run as root)

```bash
$G/ocrconfig -showbackup            # automatic and manual backups and their location
$G/ocrconfig -manualbackup          # take a manual backup before any cluster change
$G/ocrconfig -showbackup manual
$G/ocrconfig -local -manualbackup   # OLR backup for this node
```

Clusterware takes automatic OCR backups every four hours and keeps daily and weekly copies. On recent releases they are kept in ASM; `-showbackup` shows where. **Verify** on my cluster.

Restoring the OCR is not a one-line command. It means stopping Clusterware on all nodes, starting one node in exclusive mode and following Oracle's documented restore procedure. I don't run it on a working cluster.

## Logs

Since 12c, Clusterware logs are in the Automatic Diagnostic Repository, not under `$GRID_HOME/log/<hostname>` as older guides show.

```text
/u01/app/grid/diag/crs/<node>/crs/trace/alert.log           Clusterware alert log
/u01/app/grid/diag/crs/<node>/crs/trace/crsd.trc            CRS daemon
/u01/app/grid/diag/crs/<node>/crs/trace/ocssd.trc           cluster synchronization
/u01/app/grid/diag/crs/<node>/crs/trace/ohasd.trc           High Availability Services
/u01/app/grid/diag/crs/<node>/crs/trace/crsd_oraagent_grid.trc
/u01/app/grid/diag/crs/<node>/crs/trace/crsd_orarootagent_root.trc
```

Root script logs from the Grid install are under `/u01/app/grid/crsdata/<node>/crsconfig/`. I used both locations to trace node 2's `CLSRSC-117` failure during my build.

CTSS is desupported in 26ai (chrony keeps time), and diskmon only matters on Exadata, so older guides' logs for those don't apply.

## High availability gap in my lab, and the practice fix

My OCR and only voting file sit on one disk with no mirroring. Losing `ocr01.vdi` would mean rebuilding the cluster configuration. For practice, I can add a second OCR location in another disk group:

```bash
$G/ocrconfig -add +DATA
$G/ocrcheck                         # should list two OCR locations
```

**Verify** on my cluster. Voting files are different: they need a normal- or high-redundancy disk group (three or five disks), which this lab doesn't have. In production I'd use a normal-redundancy disk group with three failure groups.

## Related

- [Clusterware crsctl reference](rac-clusterware-crsctl-reference.md)
