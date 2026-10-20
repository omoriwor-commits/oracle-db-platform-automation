# Security Rules

These rules apply to every file, commit, screenshot and pull request in this project and in the two related lab repositories. A public portfolio is permanent: deleting a secret from the latest commit does not remove it from Git history.

## Never commit

- Passwords, including lab passwords and examples that were once real
- Private SSH keys, `.ppk` files, TLS private keys
- Oracle wallets and GoldenGate credential stores (`cwallet.sso`, `ewallet.p12`)
- VPN pre-shared keys, API keys, cloud access keys, auth tokens
- OCIDs, OCI tenancy IDs, Azure subscription and tenant IDs, AWS account IDs
- Public IP addresses of my own resources, and my home or admin public IP
- Terraform state (`*.tfstate`) and saved plans, which can hold secrets in plain text
- Response files that contain passwords
- Real or production data of any kind

Private RFC1918 addresses (10.x, 172.16-31.x, 192.168.x) used only inside the lab are fine to publish.

## Placeholders

Use the same placeholders everywhere so a reader knows a value was removed on purpose:

```text
<STRONG-LAB-PASSWORD>
<CURRENT-ADMIN-IP>/32
<redacted>
<SECRET-NOT-STORED>
<OCID-NOT-PUBLISHED>
```

## Screenshots

Before committing a screenshot, crop or blur public IPs, OCIDs, subscription and tenant IDs, account names, email addresses and browser bookmarks. Check the tab titles, the console header bar and any saved-session lists too.

## Network rules for the lab

- No `0.0.0.0/0` ingress to TCP 22, 1521, 1433, 3389 or GoldenGate admin ports.
- Administrative access comes from a single trusted `/32` or through a bastion or tunnel.
- Databases sit in private subnets; only what must be reachable gets a public address.
- Temporary access rules are removed when the session ends.

## Before every push

1. Run a secret scan on the working tree and history: `gitleaks detect --source . --verbose`
2. Read the staged diff: `git diff --staged`
3. Never push directly to `main`; open a pull request.

## If something sensitive is committed

1. Treat it as exposed. Rotate the password or key, or release the IP, first.
2. Remove it from the current files in a pull request.
3. If needed, rewrite history with `git filter-repo --replace-text`, then force-push.
4. Record what happened in the progress log without repeating the secret.

## Repository settings

- `main` is protected: pull request required, no force-push, no deletion.
- GitHub secret scanning and push protection are turned on.
