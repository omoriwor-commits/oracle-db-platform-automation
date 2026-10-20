# 10 — Security and Interoperability

> **Reference scope:** Oracle-documented security procedures and illustrative configurations; executed tests are tracked separately.

## Scope and security requirements

Distinguish operating-system, GoldenGate service, database and transport identities; implement least privilege, TLS/WSS and credential aliases; understand trail encryption and secret recovery; compare Classic↔Microservices mixed topologies; plan a supported phased migration.

## 1. Identity and trust boundaries

| Identity | Purpose | Security boundary |
|---|---|---|
| Linux installation user | Owns software and deployment files | OS file access |
| Service Manager / Administration Service user | Manages deployments, Extract and Replicat | GoldenGate RBAC |
| Source DB capture account | Integrated Extract and source capture | Source Oracle database |
| Target DB apply account | Replicat writes mapped target data | Target Oracle database |
| Transport user or client certificate | Authorizes Distribution → Receiver | Between GoldenGate deployments |
| Monitoring identity | Inspects service/lag metrics | Read-only monitoring |

Do not conflate these identities, grant blanket DBA privileges, or place passwords into a published command or shell transcript.

### Database-version-specific privileges

**GoldenGate 26ai software does not imply Oracle Database 26ai.** Oracle AI Database 26ai introduces database roles **OGG_CAPTURE** and **OGG_APPLY**. Oracle says DBMS_GOLDENGATE_AUTH.GRANT_ADMIN_PRIVILEGE is disabled in the 26ai database and raises a warning rather than granting privileges. Older Oracle database versions use their own privilege-granting mechanism. A command valid against Oracle Database 19c is not necessarily valid against Oracle AI Database 26ai.

Vendor: https://docs.oracle.com/en/database/goldengate/core/26/coredoc/prepare-database-user-and-privileges-oracle.html

## 2. Database credential aliases

In Administration Service open **DB Connections**, create a domain/alias and enter the appropriate database user, supported connection configuration, password and database service via the approved UI. Test that the alias connects to the intended CDB/PDB, not merely that network connectivity succeeds.

Example Admin Client database connection using a configured alias:

~~~text
DBLOGIN USERIDALIAS gg_source
~~~

Example Extract parameter reference:

~~~text
EXTRACT EXTLAB
USERIDALIAS gg_source DOMAIN OracleGoldenGate
~~~

Use a separately scoped target database alias for Replicat. These identifiers are placeholders, not recovered credentials or executed configuration. A **transport USERIDALIAS** generally points to a GoldenGate target deployment user and is unrelated to the **database USERIDALIAS**.

Vendor: https://docs.oracle.com/en/database/goldengate/core/26/coredoc/extract-add-and-alter-database-connections.html

## 3. Never copy or directly modify a GoldenGate credential store

The an unsafe wallet-copy workaround proposes restoring Service Manager access by replacing wallet files from a dummy deployment. **Reject this as an operational procedure.** Oracle's 26ai authentication documentation explicitly says the credential store is read-only for direct manipulation, including copying it from one deployment to another. Manage credentials through supported Admin Client, REST or WebUI actions. Forgotten-admin-password recovery must follow a vendor-supported process specific to the actual installation.

Protect credential wallets, TLS private keys, database passwords, populated response files and backups from general access. Rotate credentials promptly when leakage is suspected; deleting a password from the current repository commit does not remove prior Git history.

Vendor: https://docs.oracle.com/en/database/goldengate/core/26/coredoc/secure-an.html

## 4. Secure administration and trail transport

Oracle recommends secure GoldenGate deployments using strong passwords, RBAC, TLS-backed administrative REST APIs, and secure WebSocket **wss** Distribution Paths. Allowed transport authentication choices include **USERIDALIAS**, trusted client certificates/mTLS and external OAuth/OIDC in applicable releases.

~~~text
GoldenGate source Distribution Service
      -- WSS / TLS + scoped transport identity -->
GoldenGate target Receiver Service
~~~

Certificate design must address trusted CA, hostname/SAN matching, private-key permissions, renewal, target authorization and firewall exposure. A successful TCP/TLS handshake does not independently prove GoldenGate authentication or trail continuity.

**Trail encryption at rest** protects files stored on disk and is distinct from network TLS. Document GoldenGate master-key or supported external key management, rotation and recovery policy before enabling encryption.

Read-only network inspection on approved hosts:

~~~bash
ss -lntp
~~~

Vendor: https://docs.oracle.com/en/database/goldengate/core/26/coredoc/security-feature-implementation.html

## 5. Four architecture interoperability combinations

| Direction | Delivery | Important limitation |
|---|---|---|
| Classic → Classic | Pump to Classic Manager/Collector | Legacy network security model |
| MA → MA | Distribution Path to Receiver, preferably WSS | Validate TLS, identity and path checkpoints |
| MA → Classic | Distribution Path with legacy ogg protocol to Classic Manager/Collector | Mixed-mode TCP encryption limits |
| Classic → MA | Classic data pump to Receiver Service | Oracle documents direct connectivity only to **unsecured** MA deployments |

GoldenGate 26ai's FAQ identifies Classic Architecture as de-supported **in 26ai**. Mixed cases refer to *older Classic installations*, not a recommendation to install a new Classic 26ai deployment.

Oracle also states legacy Classic transport configured with RMTHOST ENCRYPT is not a supported way to encrypt the mixed Classic–MA Receiver connection. The insecure direct Classic→MA path may be unsuitable on public or regulated networks. Assess a staged architecture with adjacent MA deployment or supported reverse proxy and WSS between MA components.

Sources:
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/reference-connecting-classic-ma.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/reference-connecting-ma-classic.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/distribute-streaming-protocols.html

## 6. MA source to older Classic target — controlled lab procedure

1. Confirm source Extract and source trail, and document source checkpoint.
2. Confirm Classic Manager or static Collector is configured and its listener port accessible only on approved networks.
3. In the older Classic GGSCI, start Manager if authorized:

~~~text
START MANAGER
~~~

4. In source MA Distribution Service create a path; choose **ogg** target protocol and **Manager/Collector** target type.
5. Supply approved target host, port, target trail, security/retention policy and start sequence/RBA.
6. Start path and inspect source/target trails; validate target Replicat and target row data separately.

**Safety:** do not publish real ports/passwords, disable network controls or advance checkpoints to NOW to bypass missing sequences. Validate mixed-mode protocol support before execution.

Vendor: https://docs.oracle.com/en/database/goldengate/core/26/coredoc/reference-connecting-ma-classic.html

## 7. Classic to MA — plan around the security limitation

A legacy Classic data pump can target an MA Receiver only under Oracle's documented mixed-mode conditions. The 26ai interoperability guide identifies an unsecured MA deployment and Receiver ingress requirement; this arrangement requires explicit security review and is not a default production recommendation.

Oracle offers a **Classic-to-Microservices Migration Utility** for supported older Classic releases. Migration requires a prepared and running MA deployment, compatible source build, shutdown of Classic services, checkpoint/trail preservation and migration planning. Migration utility work is change-controlled; no example in this chapter constitutes evidence of an executed conversion.

Vendor: https://docs.oracle.com/en/database/goldengate/core/26/coredoc/migration-utility-migrate-classic-ma.html

## 8. Troubleshooting and response controls

| Symptom | Inspect first | Avoid |
|---|---|---|
| DBLOGIN fails | Alias/domain, PDB service, DB account state/privileges, SQL Net | Plaintext password fallback |
| WSS handshake fails | TLS trust, SAN/hostname, expiry, mutual TLS requirements | Switching to insecure ws to silence error |
| Distribution unauthorized | Target operator role, transport credential, cert/OAuth identity | Reusing full administrator permanently |
| Classic pump fails against secured MA | Documented mixed-mode protocol limitation | Exposing unsecured Receiver without review |
| Lost Service Manager password | Supported identity recovery and backups | Copying a different deployment wallet |
| Old trails not delivered | Checkpoints, source and target sequence/RBA, path/Collector logs | Reposition NOW or delete trails |
| Secret committed to Git | Revoke and rotate, investigate exposure and Git history | Deleting only the newest file version |

## 9. Security validation scenarios

**A — Identity boundaries:** List separate OS, GoldenGate administration, source capture, target apply and transport users; specify the minimum access each needs.

**B — Secure transport:** Design MA→MA WSS using a trusted CA, correctly named server certificates, a target Operator user and a scoped transport alias. Specify validation evidence.

**C — Mixed architecture choice:** A secured 26ai target must receive from a legacy Classic pump. Explain why direct Classic→secured MA is not supported in Oracle's cited guide, and propose a vendor-supported staged alternative.

**D — Credential recovery:** Investigate the supported recovery procedure for an unavailable administrator credential. Never transplant wallet files across deployments.

## 10. Security evidence worksheet

~~~text
Date / observer:
GoldenGate software source/target releases:
Oracle DB source/target releases (independently):
Identity and DB privilege matrix:
Source and target CDB/PDB connection aliases (NO SECRETS):
GoldenGate admin / operator role configuration:
Transport certificate/trust and WSS checks:
Network/firewall exposure and protocol:
Trail encryption and key recovery plan:
Classic/MA migration compatibility decision:
Extract, path and Replicat checkpoints:
Target validation and reconciliation:
Observed errors and remediation:
Status: Vendor reference / reference-derived / lab verified
~~~

**Verification:** Oracle 26ai documentation establishes documented support and restrictions. Example identifiers are placeholders; lab validation is not recorded here.

## Oracle references

- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/security-feature-implementation.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/secure-an.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/prepare-database-user-and-privileges-oracle.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/reference-connecting-ma-classic.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/reference-connecting-classic-ma.html
- https://docs.oracle.com/en/database/goldengate/core/26/coredoc/migration-utility-migrate-classic-ma.html

**Next:** [11 — Performance, High Availability and Automation](11-performance-high-availability-and-automation.md)
