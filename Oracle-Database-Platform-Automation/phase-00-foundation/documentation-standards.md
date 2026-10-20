# Documentation Standards

Every document in this project should be something I can defend in an interview, line by line: say what I did, show the evidence, and be clear about what is still open.

## Voice

- First person, plain English: "I rebuilt the standby," not "The standby was rebuilt leveraging..."
- Use the shortest accurate word. Skip filler such as "robust," "seamless" and "leverage."
- This is self-directed lab work. Never imply employer or production ownership.

## Status words

| Status | Meaning |
|---|---|
| **Done** | Tested, and the evidence is committed |
| **In progress** | Being built; not fully verified |
| **Planned** | Not started or not validated |

"Completed in my earlier lab" is fine for past work, as long as the same paragraph says where the evidence is or that it will come from a rerun.

## Claims and evidence

- Nothing is described as working until there is dated output to show it.
- When evidence is missing, say so in the same paragraph as the claim.
- Planned work (AWS, GCP, bidirectional replication) is never written in the past tense.
- Resume and LinkedIn wording comes from these documents, never the other way around.

## Dated records

Checkpoints, incident reports and project history are snapshots. Each starts with its date. When one goes out of date, add a one-line banner pointing to the current status instead of rewriting it.

## Where things go

Each phase gets a `phase-NN-<topic>/` folder with a README holding its Done-when checklist and the Phase Completion Record from the roadmap. Incident write-ups go in `incident-reports/`; diagrams, runbooks and sanitized evidence go under `docs/architecture/`, `docs/runbooks/` and `docs/evidence/`.

## Runbooks

A runbook states its purpose, prerequisites, the exact commands in order, expected output, how to verify, and how to roll back. Anything I have not run myself is marked **Verify**.

## Before merging a documentation PR

- Links work, including links to the other two repositories.
- No secrets or public IPs (see [security-rules.md](security-rules.md)).
- Status words match the evidence.
- No other file now contradicts this one.
