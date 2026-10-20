# 02 — Windows SSH Key Management and OCI Compute Access

**Scope:** Windows SSH key management, OCI Compute public-key authorization, Linux instance access and incident diagnostics.

## 1. Access design

A Windows workstation maintains the **private** SSH key. OCI Compute receives only the matching **public** key during instance creation. The Linux OS image and authorized_keys configuration determine the actual login account. For Oracle Linux images the typical account is `opc`; verify the selected image rather than trying arbitrary users.

Recommended flow:

~~~text
Windows workstation (private key)
       |
       | SSH TCP/22 from trusted source
       v
OCI instance public IP (if public subnet + approved access)
       |
       v
Authorized Linux account / ~/.ssh/authorized_keys
~~~

Private instances have no public IP and should be reached through an approved bastion or private network route, as described in [01 — VCN, Subnets and Gateways](01-vcn-public-private-subnets-internet-nat-gateways.md).

## 2. Generate a new key pair in Windows

Windows Terminal / PowerShell with OpenSSH installed:

~~~powershell
ssh -V
ssh-keygen -t ed25519 -a 100 -C "oci-lab-windows" -f "$env:USERPROFILE\.ssh\id_ed25519_oci_lab"
~~~

Use a strong passphrase and store the private key only in a protected local directory. Upload or paste **only** the contents of the `.pub` file into the OCI instance provisioning form:

~~~powershell
Get-Content "$env:USERPROFILE\.ssh\id_ed25519_oci_lab.pub"
~~~

Do not share the output of `Get-Content` for the file **without** `.pub`. If the image or tool requires RSA, generate a release-appropriate RSA key instead; never reuse a previously exposed key pair.

## 3. Provision the OCI Linux instance

In the OCI Console:

1. Select the approved compartment and home/target region.
2. Create or choose a VCN, subnet and appropriately scoped network security group (NSG).
3. Select a supported Oracle Linux image and suitable shape within approved quota/cost limits.
4. Under SSH keys, upload or paste the newly generated **public** key.
5. If direct SSH is required for the disposable lab, assign a public IPv4 address **only** to an instance in the public subnet.
6. Record the instance OCID privately, public/private IP, VNIC, network security group and route table; sanitize screenshots.

A public subnet, public IP, Internet Gateway route and security rule are separate requirements. Merely assigning a public address does not prove inbound SSH is reachable.

## 4. Restrict SSH ingress

Use a network security group or correctly scoped security list. For direct SSH to a public lab VM, allow **TCP destination port 22 only from your current trusted public IP address /32** (or a defined corporate/VPN CIDR). Avoid unrestricted `0.0.0.0/0` SSH ingress.

Confirm the instance OS firewall also allows authorized access. Close or remove temporary SSH access after testing.

## 5. Connect with Windows OpenSSH

~~~powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_oci_lab" opc@<INSTANCE_PUBLIC_IP>
~~~

Replace `<INSTANCE_PUBLIC_IP>` with the instance's actual public IP. On first connection, verify the server host-key fingerprint through an independent trusted channel before accepting it.

If the Windows private-key ACL is too permissive, remove unnecessary access for other users; marking a file *read-only* alone does not secure its ACL.

## 6. PuTTY alternative

For a PuTTY workflow:

1. Install the supported PuTTY suite from its official site.
2. Use PuTTYgen to generate a secure new key pair or import a compatible private key under your control.
3. Save the PuTTY private key locally as `.ppk`; protect it and use a passphrase.
4. Configure the target as `opc@<INSTANCE_PUBLIC_IP>` or specify the username separately.
5. Under SSH authentication, select the corresponding private key.
6. Verify the server host-key fingerprint before accepting it.

Do not upload a `.ppk` or other private key to GitHub.

## 7. SSH troubleshooting

| Symptom | Check |
|---|---|
| Connection timeout | Instance running, public/private IP, IGW route, subnet type, NSG/security list, host firewall |
| Permission denied (publickey) | Correct user, correct private key matching provisioned public key, authorized_keys and key ACL |
| Host-key mismatch | Possible reimage or security issue; independently verify before trusting a replacement key |
| Public instance works, private instance fails | Bastion/private routing, target NSG source, authorized account |
| PuTTY key not accepted | Imported key format, PPK selection, matching public key and SSH version |

Use `ssh -vvv` locally for controlled debugging, but redact user/host identifiers and avoid posting complete sensitive logs.

## Oracle references

- Compute key provisioning: https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/creatinginstance.htm
- OCI Networking security: https://docs.oracle.com/en-us/iaas/Content/Security/Reference/networking_security.htm
- OCI Bastion: https://docs.oracle.com/en-us/iaas/Content/Bastion/Concepts/bastionoverview.htm

