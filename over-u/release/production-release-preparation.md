# OVER U production release preparation

This document is a plan for a separately authorized release. No production VM, database, users, files, DNS, or settings were accessed or changed while preparing it.

## Read-only production checks

Run from an approved, read-only IAP session. Record only version strings, booleans, counts, and opaque identifiers needed to reproduce checks. Do not print passwords, cookies, lesson text, assignment answers, or file contents.

1. Record VM state, deployed Git SHAs, container image digests, Frappe/LMS/over_u versions, site name, migration state, asset build timestamp, disk and memory summaries.
2. Read the effective `LMS Settings.make_attachments_public` value and confirm it is false. Inspect only the `File.is_private` flag and attachment relationship metadata for a known synthetic probe file. Do not enumerate or download learner submissions.
3. For a production HTTP privacy check, use an already-existing synthetic canary attachment only. Check its direct URL as Guest, as an unrelated synthetic learner, as the owner, and as an authorized course teacher. Require denial for the first two and authorized response for the latter two; compare a synthetic marker hash rather than displaying response bodies. If no synthetic canary exists, stop and request separate approval before creating one. Delete the canary only under that separate approval.
4. Keep this audit read-only: no login reset, user/role edits, setting changes, migrations, writes, restarts, backup creation, or file download.

## Backup and restore rehearsal

1. Pin the exact production code SHA and record current image digests and configuration versions.
2. Create a consistent MariaDB backup and separately archive the site's public files, private files, `site_config.json`, relevant `common_site_config.json`, custom app configuration, and deployment manifests. Restrict access to secrets; never place them in GitHub artifacts or ordinary logs.
3. Encrypt archives before transfer using a key held separately from the destination. Store encrypted copies outside the production VM, verify SHA-256 after transfer, apply least-privilege access, retention, and deletion controls. Keep the decryption key out of the backup destination.
4. Restore database and both file trees into an isolated, non-public Frappe environment with outbound mail disabled. Restore configuration with restrictive permissions, match the deployed app SHAs, run the candidate migration there, and verify site boot, assets, representative course/media metadata, private-file access matrix, login, and learner progress. Record hashes and test outcomes, not private content.
5. A backup is considered verified only after this isolated full-site restore succeeds. No such production backup or restore rehearsal has been performed for this change.

## Candidate release and rollback

1. Obtain explicit approval naming the exact PR commit and maintenance window. Keep PR #1 unmerged until that approval.
2. Before deployment, confirm a verified off-VM backup, restore evidence, green CI, and a reviewed exact diff. Deploy the approved SHA, build assets, run required migrations only after backup verification, restart only the necessary app services, and run synthetic smoke checks.
3. Validate /school, /lms, /desk, synthetic student and Course Creator access, draft persistence, quiz/assignment flow, and private attachment denial before inviting learners.
4. If smoke checks fail, stop learner access. Revert code and image references to the recorded release SHA. If a migration changed the schema or data incompatibly, restore the verified DB and public/private files together into a controlled recovery window; do not restore only SQL while leaving newer files.
5. Re-check HTTPS, application errors, login, and privacy after rollback. Keep the failed release artifacts and audit summary without learner data.

## Current release gates

- Production read-only audit: not performed in this phase.
- Production backup and full restore rehearsal: not performed in this phase.
- Deployment, migration, user/settings changes, and PR merge: not authorized.
- CI and isolated synthetic checks are evidence for the candidate only, not proof of production state.
