# Naming Standards

A name should tell me what something is, where it lives and whether it is disposable, without opening it. These standards apply to new resources. Resources built before October 2026 keep their recorded names so the existing evidence still matches.

## General rules

- Lowercase, hyphen-separated, no spaces: `vm-goldengate-lab-01`, not `GoldenGate VM`.
- Type prefix first, then purpose, then environment, then a two-digit number when there can be more than one.
- `lab` marks anything disposable. Nothing in this project is production.

## Cloud resources

| Resource | Pattern | Example |
|---|---|---|
| Azure resource group | `rg-<project>-<env>` | `rg-enterprise-data-platform-lab` |
| Azure VNet / OCI VCN | `vnet-<project>-<env>` / `vcn-<project>-<env>` | `vcn-oracle-platform-lab` |
| Subnet | `snet-<purpose>` | `snet-database`, `snet-goldengate` |
| Network security group | `nsg-<purpose>-<env>` | `nsg-goldengate-lab` |
| Virtual machine | `vm-<role>-<env>-NN` | `vm-sqlserver-lab-01` |
| VPN gateway / DRG | `vng-<purpose>-<env>` / `drg-<purpose>-<env>` | `drg-azure-hybrid-lab` |
| Object Storage bucket | `bkt-<purpose>-<env>` | `bkt-tfstate-lab` |

Required tags on every cloud resource: `Environment = Lab`, `Project = OracleDbPlatform`, `ManagedBy = Manual | Terraform | Ansible`.

## Address plan

Each cloud gets its own /16 so networks can be joined later without overlap.

```text
OCI    10.50.0.0/16
Azure  10.60.0.0/16
AWS    10.70.0.0/16
GCP    10.80.0.0/16
Local VirtualBox host-only: 192.168.56.0/24 (public), 192.168.57.0/24 (RAC interconnect)
```

## Oracle and GoldenGate

| Object | Pattern | Example |
|---|---|---|
| RAC nodes | `racnodeN` | `racnode1` |
| CDB / PDB | Short, uppercase, version in the name when several coexist | `CDB23AI` / `PDB23AI` |
| GoldenGate deployment | Purpose in capitals | `DEP1`, `MSSQLDEP` |
| Extract | `EXT` + source hint, 8 characters max | `EXT19C`, `EXTORA` |
| Replicat | `REP` + target hint, 8 characters max | `REP26AI`, `REPSQL` |
| Trail prefix | Two lowercase letters | `ea` |

## Git and files

| Item | Pattern | Example |
|---|---|---|
| Branch | `<type>/<short-description>` | `phase-1/tablespace-check`, `docs/fix-links` |
| Commit message | Imperative, one line, under 72 characters | `Add listener check to health script` |
| Phase folder | `phase-NN-<topic>` | `phase-01-linux-bash` |
| Markdown file | kebab-case | `lab-inventory.md` |
| Dated record | `YYYY-MM-DD-<topic>.md` | `2026-10-rac-node2-startup-investigation.md` |
| Evidence folder | `evidence/YYYY-MM-DD-<run>/` | `evidence/2026-11-02-oci-azure-rerun/` |
