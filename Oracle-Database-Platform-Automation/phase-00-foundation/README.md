# Phase 0: Foundation

Phase 0 sets the ground rules before any automation work: where the project lives, how it is protected, what it runs on, what it may cost, and how it is written up. The criteria come from [ROADMAP.md](../ROADMAP.md#phase-0--foundation).

## Done-when checklist

| Criterion | Status | Evidence |
|---|---|---|
| Repository exists and `main` is protected | In progress | Repo renamed to `oracle-db-platform-automation` (Oct 2026). Branch protection evidence still to add |
| README describes the project goal and Architecture v1 | Done | [Project README](../README.md#architecture-v1) |
| Roadmap committed | Done | [ROADMAP.md](../ROADMAP.md) |
| Security rules committed | Done | [security-rules.md](security-rules.md) |
| Naming standards committed | Done | [naming-standards.md](naming-standards.md) |
| Documentation standards committed | Done | [documentation-standards.md](documentation-standards.md) |
| Lab inventory lists every server, VM and cloud tenancy | In progress | [lab-inventory.md](lab-inventory.md); hardware and OS details still to confirm |
| Budget alerts active on every cloud account used | In progress | Azure budget documented Aug 2026; OCI alert and current Azure status still to confirm |

Phase 0 moves to **Done** only when every row above is Done and the evidence is committed.

## Phase Completion Record

Status: In Progress
Started: October 2026
Completed:

### What I built
- One controlling roadmap, with the project README pointing to it instead of repeating it.
- Security rules, naming standards, documentation standards and a lab inventory.

### What failed
-

### Root cause
-

### How I fixed it
-

### Validation performed
- Scanned all three portfolio repositories for public IPs, keys, OCIDs and account IDs, and removed the public IPs found in `enterprise-multicloud-database-platform-lab`.

### Skills demonstrated
-

### Evidence
- Foundation record and inventory: [phase-00-foundation](./README.md) and [lab inventory](lab-inventory.md).
- RAC documentation/inventory update: [merged PR #11](https://github.com/omoriwor-commits/oracle-db-platform-automation/pull/11).
- Tested health script and evidence: [merged multicloud PR #7](https://github.com/omoriwor-commits/enterprise-multicloud-database-platform-lab/pull/7).
- Branch protection: evidence pending.
- Budget alerts: current OCI/Azure confirmation pending.
- Secret scan output: retained execution output still to publish; the earlier scan statement above is a reported action, not a complete history audit.

### Interview story
-
