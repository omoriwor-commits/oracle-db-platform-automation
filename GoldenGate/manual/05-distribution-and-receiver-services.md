# 05 — Distribution and Receiver Services

> **Reference scope:** Vendor documentation and illustrative configurations. Executed changes require separately retained logs and validation evidence.
> **Prerequisite:** [04 — Integrated Extract and Source Trails](04-integrated-extract-and-source-trails.md).  

## Scope and verification

This page covers transport roles, identify trail endpoints, distinguish source-initiated and target-initiated paths, configure a controlled path using the Microservices GUI or Admin Client, interpret lag/checkpoints, identify networking and authentication faults, and collect transport evidence without claiming the target has applied the data.

## 1. Transport is separate from capture and apply

```text
SOURCE DEPLOYMENT                            TARGET DEPLOYMENT
Oracle redo -> Integrated Extract
                      |
                 source trail ea
                      |
              Distribution Service
                 [Path: src_to_tgt]
                      |
                authenticated TLS
                      |
                      v
                                           Receiver Service
                                                 |
                                           target trail eb
                                                 |
                                              Replicat
                                                 |
                                           Oracle target DB
```

Extract writes a trail; the Distribution Service **reads** a configured source trail and sends records across deployments; the Receiver Service **receives and persists** destination trail records; Replicat applies the target trail. In Microservices Architecture, a distribution path replaces many traditional Classic Architecture data-pump and Collector transport responsibilities, but there are architecture-specific differences.

**Critical distinction:** a healthy Distribution Path proves that a transport path exists and may be moving trail records. It does **not** by itself prove the target Replicat applied changes.

## 2. Two connection directions

| Path type | Who initiates connection? | Typical use |
|---|---|---|
| **Distribution Service Path** (source-initiated) | Source deployment connects to the target Receiver Service | Normal push model where source may reach target |
| **Receiver Service Path** (target-initiated) | Target Receiver Service contacts source Distribution Service and pulls the source trail | Firewall/DMZ/cloud designs where inbound target connectivity is restricted |

The target-initiated option is documented for cases where the source cannot open a connection to the target but the target can initiate the reverse connection. Transport direction changes; logical source-to-target data flow does not. Oracle documents limits of target-initiated paths (including ws/wss instead of legacy ogg transport). For a secured source, use WSS. Confirm deployment security, TLS trust and supported authentication before choosing a mode.

Vendor: [Distribution Path](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/distribute-distribution-path.html); [Receiver Service Paths](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/distribute-receiver-service-paths.html).

## 3. Prerequisites and source/target inventory

Before creating any path, establish these **actual values** for the selected deployment:

| Field | Example placeholder | Evidence to collect |
|---|---|---|
| Source deployment and Distribution Service endpoint | `src-ogg.example.invalid:9002` | Service URL, listener and TLS identity |
| Target deployment and Receiver Service endpoint | `tgt-ogg.example.invalid:9003` | Reachability, listener and TLS identity |
| Source trail | `ea` | Extract parameter, trail registration and on-disk sequence |
| Target trail | `eb` | Approved target prefix, filesystem capacity and permissions |
| Authentication | Service credential alias/certificate | Scope and trust; **no plaintext secret** |
| Path name | `src_to_tgt` | Unique per deployment |
| Start position | Resume checkpoint, specific log position or CSN | Alignment with initial load and continuity requirement |
| Network policy | Approved route, hostname resolution, firewall ports | Connectivity test from **initiating** side |
| Recovery policy | Retention, backlog monitoring, incident response | Required source and target trail availability |

**Do not substitute unverified host addresses or credentials** for verified current addresses or credentials.

### Safe Linux observations

Run on the relevant GoldenGate hosts:

```bash
getent hosts src-ogg.example.invalid
getent hosts tgt-ogg.example.invalid
ss -lntp
df -hT
```

An approved TLS connectivity test can use `openssl s_client -connect host:port -servername host` to examine the certificate chain, but service endpoints must be real, correctly routed and reachable; do not treat a TCP handshake as successful GoldenGate authentication.

## 4. Source-initiated path — Microservices GUI

**Impact:** creates a transport configuration and may move trail records. **Where:** source deployment's Distribution Service. **Account:** authorized Microservices administrative/operator account with permission to create paths.

1. Confirm source Extract's local trail prefix and that its sequence/position are valid.
2. Open the intended **Distribution Service** and choose to add a Distribution Service Path.
3. Enter a path name, source trail URI/prefix, target Receiver Service hostname/port and destination trail prefix.
4. Choose secure transport, trusted certificate or approved credential-alias authentication.
5. Set starting checkpoint only after reviewing previously delivered records and initial-load coordination.
6. Review path settings, save, start and inspect the actual status/statistics.
7. On the target Receiver Service, confirm the intended destination trail exists and progresses before configuring the corresponding Replicat.

**Never assume:** creating a path necessarily transmits all past source changes. The configured start position and available trail sequences control what is eligible.

Vendor: [Distribution Service Path](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/distribute-distribution-path.html).

## 5. Admin Client configuration example

Oracle 26ai documents the following structure for a Distribution Path:

```text
ADD DISTPATH src_to_tgt
  SOURCE trail://src-ogg.example.invalid:9002/services/v2/sources?trail=ea
  TARGET wss://tgt-ogg.example.invalid:9003/services/v2/targets?trail=eb
  AUTHENTICATION USERIDALIAS tgt_transport DOMAIN OracleGoldenGate
```

**Configuration requirement:** Use approved deployment endpoints, valid credential aliases and the Oracle-documented URI format for the installed release. Restrict receiver authentication to an appropriately scoped operator identity.

| Clause | Purpose |
|---|---|
| `ADD DISTPATH src_to_tgt` | Create uniquely named outbound transport path |
| `SOURCE trail://...` | Identify the source Distribution Service and source trail |
| `TARGET wss://...` | Identify the secured target Receiver Service and target trail |
| `AUTHENTICATION USERIDALIAS ...` | Use a configured credential alias without including a password |

Oracle also documents alternative OAuth and certificate methods. Avoid URLs containing user:password, even though certain legacy examples show such syntax.

Vendor: [ADD DISTPATH — Oracle 26ai CLI](https://docs.oracle.com/en/database/goldengate/core/26/gclir/add-distpath.html).

## 6. Starting and inspecting a path

**Only start after approval and a validated boundary.** The documented operation is:

```text
START DISTPATH src_to_tgt
```

For read-only administration:

```text
INFO DISTPATH ALL
INFO DISTPATH src_to_tgt DETAIL
```

`INFO DISTPATH ... DETAIL` may include status, source/target identity, current/input/output checkpoints and lag. Oracle's `START DISTPATH` also accepts CSN-based start arguments; **do not choose ATCSN/AFTERCSN without initial-load and replay analysis** because those options may skip earlier changes.

Vendor: [INFO DISTPATH](https://docs.oracle.com/en/database/goldengate/core/26/gclir/info-distpath.html); [START DISTPATH](https://docs.oracle.com/en/database/goldengate/core/26/gclir/start-distpath.html).

## 7. Target-initiated Receiver Service Path

When network security permits target-to-source egress but not source-to-target ingress:

1. Open the **target Receiver Service** and choose to add a **Receiver Service Path**.
2. Specify the reachable source Distribution Service, source trail, and supported authentication.
3. Choose `wss` for a secured source, with valid certificate trust.
4. Supply the approved destination trail and start position; review encryption, filtering and checkpoint options.
5. Start the Receiver Service Path and monitor it from the target, checking the receiving trail.
6. Validate downstream Replicat separately.

Target-initiated mode changes which host opens the connection; it does not eliminate source-trail retention requirements. Oracle notes certain limitations for this mode. Vendor: [Add Receiver Service Paths](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/distribute-add-target-initiated-distribution-paths.html).

## 8. Filtering — an important 26ai correction

**Distribution Paths are not always unfiltered.** Oracle GoldenGate 26ai documents **filter rules on Distribution Service Paths and Receiver Service Paths**, including object-based, DML/DDL and some column-based criteria. Verify rules against the configured path and expected target operations.

Filtering is not automatically active; it must be explicitly configured, understood and tested. A change filtered at transport might never reach Replicat, despite normal path health. Before enabling any filter:

- Record whether filtering occurs in Extract, transport or Replicat.
- Explain inclusion/exclusion rules and their interaction with table mappings.
- Test INSERT, UPDATE and DELETE behavior and capture statistics.
- Mark intentionally filtered records separately from accidental loss.

Vendor: [Actions for Distribution Service Paths](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/distribute-using-path-actions.html).

## 9. Operational monitoring

| Signal | What it can establish | What it cannot establish |
|---|---|---|
| Path state | Running/stopped/failed transport process | End-to-end apply correctness |
| Source sequence/RBA | Which source trail checkpoint is being consumed | Whether target DB rows match |
| Target trail sequence/RBA | Whether receiver output progresses | Whether Replicat has caught up |
| LCR/DML/DDL path stats | Records read/sent or filtered | Full transactional reconciliation |
| Transport lag | Delay in the transport stage | Entire source-to-target latency |
| Network send/receive metrics | Link utilization, waits, transport symptom | Database constraint or apply error root cause |

Oracle 26ai path pages expose source/target URIs, encryption, checkpoints, LCR and network statistics. Compare time windows and process restart behavior before interpreting counters. Vendor: [Monitor Path Information and Statistics](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/distribute-monitor-distribution-paths.html).

## 10. Troubleshooting by failure boundary

| Symptom | Investigation | Safe next action |
|---|---|---|
| Cannot create path | Wrong deployment/role, invalid URI, missing source trail, unsupported authentication | Inspect exact service error and chosen URI |
| Connection refused | Receiver/Distribution service stopped, firewall route, wrong port/DNS | Inspect listener and logs on the initiating and receiving sides |
| TLS/authentication fails | Certificate hostname/trust, alias permissions, expired credential | Confirm identities and certificate chain; don't downgrade security to bypass |
| Path RUNNING, zero messages | Idle source, Extract not writing, wrong source trail prefix, explicitly configured filter | Commit controlled test transaction and inspect Extract/source trail |
| Target trail missing | Wrong destination prefix/path, permission/storage issue, Receiver errors | Inspect Receiver Service trail creation and log |
| Source trail deleted before delivery | Purge/retention configuration, long downstream lag | Preserve logs/checkpoints; follow supported trail recovery/restore |
| Gap between trail sequences | Missing file or mismatched position | Stop unsafe cleanup and determine recoverable source checkpoint |
| Trail reaches target, rows unchanged | Replicat not configured/running, wrong mapping, apply error | Continue at Replicat stage; path transport is not apply proof |

**Never** correct a lag or sequence gap by deleting trail files, starting at NOW, forcing a new CSN, or recreating a path without a continuity and instantiation plan.

## 11. Operational validation scenarios

### Scenario A — topology review

Draw source-initiated and target-initiated diagrams. Given a DMZ restriction permitting **target→source** but not **source→target**, explain which direction would work and which ports/authentication/trust must be tested.

### Scenario B — controlled lab validation

1. Produce at least one actual committed source DML transaction and confirm Extract writes source trail.
2. Record source and target service endpoints and negotiated TLS trust.
3. Create a correctly positioned outbound Distribution Path with test-only approved credentials.
4. Inspect `INFO DISTPATH ... DETAIL`, Receiver Service and actual destination trail sequences.
5. Pause/restart the approved transport path and verify continuous checkpoint progression without loss.
6. Save redacted logs/screenshots. **Do not claim target-row replication yet** until Replicat and reconciliation are tested.

### Scenario C — ambiguous transport outcomes

- **Case 1:** Extract counts grow while Distribution counts remain zero. Diagnose the source trail binding and path position.
- **Case 2:** Distribution counts grow and target trail advances, but target rows remain unchanged. Diagnose downstream Replicat/apply, not network transport.

**Questions:** What is the difference between target-initiated and source-initiated? What does `INFO DISTPATH DETAIL` add? Why is a trail prefix alignment essential? Can a transport filter intentionally suppress changes? What would prove the target actually applied them?

## 12. Evidence capture template

```text
Test date and GoldenGate release:
Source deployment / Distribution Service:
Target deployment / Receiver Service:
Source trail prefix and first/last sequence:
Target trail prefix and first/last sequence:
Transport direction: source-initiated / receiver-initiated
TLS trust and authentication method (NO secrets):
Distribution Path / Receiver Service Path name:
Path start position (CSN, sequence/RBA, approved snapshot relation):
Extract input and path output statistics:
Receiver trail progression:
Path lag and checkpoint snapshots:
Redacted error/report files:
Intentional filtering (if any):
Target Replicat apply: Covered in 06 — Integrated Replicat and Validation
Validation record: configured path, source/target checkpoints, receiver trail sequence and observed delivery results
```

## Status

- **Reference coverage:** transport paths, Receiver service, checkpoints, filtering and Classic interoperability; test results must be documented separately.
- **Oracle-documented:** ADD/START/INFO DISTPATH, target-initiated paths, transport filtering, monitoring controls.
- **Examples:** URI, path and alias identifiers are placeholders.
- **Not yet tested here:** any newly configured GoldenGate environment or transport path.



## Official references

- [Oracle 26ai ADD DISTPATH](https://docs.oracle.com/en/database/goldengate/core/26/gclir/add-distpath.html)
- [Oracle 26ai INFO DISTPATH](https://docs.oracle.com/en/database/goldengate/core/26/gclir/info-distpath.html)
- [Oracle 26ai START DISTPATH](https://docs.oracle.com/en/database/goldengate/core/26/gclir/start-distpath.html)
- [Distribution Service Path](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/distribute-distribution-path.html)
- [Receiver Service Paths](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/distribute-receiver-service-paths.html)
- [Monitor Path Information and Statistics](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/distribute-monitor-distribution-paths.html)
- [Distribution Service path filtering/actions](https://docs.oracle.com/en/database/goldengate/core/26/coredoc/distribute-using-path-actions.html)

**Next:** [06 — Integrated Replicat and Validation](06-integrated-replicat-and-validation.md)
