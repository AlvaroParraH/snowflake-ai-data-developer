---
name: snowflake-scrape
description: "Use when working on a web-scraping collection job end to end - approve and collect, validate a snapshot, publish to object storage, and load a warehouse landing table. Use when asked to scrape, collect, refresh, or load data from websites in any project. Project-specific sources, paths, and credentials come from that project's docs."
---

# Scrape, collect, and load

A generic procedure for scraping jobs. Before running, read the target project's
README or operating docs for its commands, sources, paths, and credential names.
Do not assume them.

## Rules

- **Confirm before every live run.** Live scrapes send requests to external
  websites.
- Respect each site's rate limits. Keep the
  project's request pacing. Never bypass access controls, solve CAPTCHAs, rotate
  identities, or reuse sessions.
- If a site asks for human validation, let the user complete it in a visible
  browser. Do not automate it.
- Never print or commit secrets. Read them from the project's git-ignored env
  file, and check only that variables are set, not their values.
- Confirm the target environment, role, and database before any warehouse write.
  Do not create or alter objects, grants, or stages without approval.
- Do not truncate tables or force reloads as a retry. Repeated observations are
  normally kept on purpose; deduplicate downstream.

## Steps

Run from the target project's root, using its documented commands.

1. **Check prerequisites.** Install the project's dependencies from its lockfile.
   Install browsers if the scraper needs them. Confirm that the required variables
   exist in the git-ignored env file, and check only that they are set.

2. **Collect** (after approval). Run each source with its documented command and
   a timestamped output directory, so reruns never overwrite earlier data. Each
   run should produce a completion summary.
   - Check the summary's status before doing anything else.
   - Treat a failed or partial run as incomplete. Do not publish it.
   - If a source needs human validation, tell the user to watch the visible browser.

3. **Validate the snapshot.** Confirm the row count is plausible, required fields
   are present, and the file format matches the project's contract. Compare the
   count with the previous run when one exists, and flag large drops.

4. **Publish** completed snapshots to object storage (for example, S3, GCS, or
   a cloud file share). Use the layout the project's docs define, typically
   `<source>/<YYYYMMDD>/<file>`. Upload only completed files.

5. **Load** into the warehouse landing (raw) layer with the project's load
   procedure. Run it only on the approved target, and only for the files from the
   approved run. Choose between the project's orchestrator and a direct load only
   when the user has decided which one.

6. **Verify.** Check per-file load status, row counts, and errors. A successful
   load that loaded no new files is not proof of fresh data. Reconcile the
   uploaded files with the loaded files.

## Report

For each source, report the output directory, summary status, row count,
upload result, and load result. Also report any pauses for human validation,
retries, or skipped categories.
