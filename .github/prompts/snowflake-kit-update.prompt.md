---
name: snowflake-kit-update
description: "Safely refresh the Snowflake AI Data Developer assets in the current project from an approved kit source checkout, showing upstream changes and preserving local customizations."
argument-hint: "Optional: approved local kit checkout path and --yes after reviewing the preview"
agent: "agent"
---

# /snowflake-kit-update — Refresh Snowflake kit assets

Update the project-local Snowflake Copilot kit from an approved source checkout.
Unlike a global kit updater, this workflow updates only the current project's
Copilot assets by invoking that source checkout's documented installer.
It never changes Snowflake account state.

## Usage

```text
/snowflake-kit-update                 Interactive: inspect source and target, preview, ask consent
/snowflake-kit-update <kit-path>      Use an explicitly selected local kit checkout
/snowflake-kit-update --yes           Non-interactive consent only after the exact preview was reviewed
```

`--yes` is not permission to update an unknown source, discard local edits,
overwrite conflicting project files, or alter Snowflake. If no source path is
provided, ask the user to select the trusted kit checkout. Do not guess a path.

## What it does

1. Confirms the target is the current project root and the source is a separate,
   trusted Snowflake kit Git checkout with `install.sh` and
   `scripts/install_kit.py`.
2. Checks Git state and determines whether an update is available on the
   source checkout's configured upstream/default branch.
3. Shows incoming commits and kit-asset changes before obtaining consent.
4. If approved, fast-forwards the source checkout only when it is clean and
   not diverged.
5. Runs the kit's documented installer in dry-run mode targeting the current
   project, reviews the exact file actions/conflicts, then asks before applying.
6. Reports updated/equal/conflicting assets and required VS Code reload steps.

The installer is additive and intentionally refuses to overwrite differing
installed prompt/skill/documentation files. A conflict is evidence that local
content differs; stop and offer a manual diff/merge. Do not bypass the
installer's conflict checks or replace files directly.

## Safety requirements

- Read repository instructions and inspect the current project's Git status.
  If there are uncommitted user changes, report them and stop before updating
  project assets. Do not stage, stash, reset, commit, or discard them.
- The source kit checkout must also be clean, including untracked files. If it
  is dirty, stop; do not pull or overwrite a contributor's work.
- Confirm the source remote and branch with the user if they are ambiguous or
  unexpected. Never switch remotes, branches, or change Git configuration.
- Require the source checkout to be separate from the target project. Do not
  install the kit into its own source checkout.
- Fetching updates requires network access. Explain the configured remote and
  branch before fetching. Fetch is read-only to the source worktree but does
  update its remote-tracking refs.
- Use fast-forward-only updates. If the source branch has diverged, stop and
  ask the user to resolve it manually; do not merge or rebase.
- Never download or execute an unreviewed script. Run only the `install.sh`
  and `scripts/install_kit.py` from the selected, trusted kit checkout, after
  reviewing their current contents and behavior.
- First run `bash <kit-path>/install.sh --target <project-root> --dry-run
  --no-install`. This must not write project files or install tools. If the
  current installer does not support these flags, stop and report the local
  help/documentation; do not guess alternate commands.
- Review every planned file action and conflict. The installer may also
  activate the staged secret-scanning hook and verify `.venv`. If either could
  change or perform work, explain it and ask for approval; use `--skip-hooks`
  or `--skip-venv` only when the user chooses those options. Do not request
  MCP setup or provide credentials as part of a kit refresh.
- Apply only after explicit confirmation of the source commit, target project,
  file plan, hook behavior, and environment behavior. Use the installer
  without `--dry-run` and with `--yes` only after that complete plan is
  approved. If a conflict appears or the plan changes, stop and re-preview.
- Do not connect to Snowflake, run SQL/dbt, create or alter account objects,
  change MCP endpoints/authentication, or deploy workloads.
- Do not commit or push either repository. The user must review and commit
  project asset changes using their normal workflow.

## Procedure

### 1. Confirm target and source

Resolve and display the current project root. Confirm the selected source path
is a Git checkout distinct from the target. Check for the expected installer
files using read-only filesystem inspection.

Inspect safe Git metadata:

```bash
git -C "<kit-path>" status --short --untracked-files=all
git -C "<kit-path>" remote -v
git -C "<kit-path>" branch --show-current
git -C "<kit-path>" symbolic-ref --short refs/remotes/origin/HEAD
```

If there is no configured upstream/default branch, ask which configured
remote branch to use. Do not assume `main`, `master`, or `origin` when the
checkout indicates otherwise.

### 2. Refuse dirty or unsafe states

Require clean target and source worktrees. If the source is not on its
configured default branch, report the branch and ask whether that branch is
intentionally the update source. Do not switch branches automatically.

If the target contains uncommitted project work, stop before running the
installer. Tell the user to commit or otherwise safely preserve their work;
never offer an automatic stash/reset shortcut.

### 3. Fetch and preview source update

Explain that fetch contacts the configured Git remote and obtain approval
before network access. Fetch only the selected remote/default branch:

```bash
git -C "<kit-path>" fetch --quiet "<remote>" "<default-branch>"
```

Compare local `HEAD` to the fetched tracking ref. If no commits are incoming,
report that the source checkout is current, then continue only if the user
asked to reconcile project assets from that current source.

If commits are incoming, show a bounded commit log and changed kit paths
(skills, prompts, docs, installer scripts and hooks). Do not dump secret or
large content. If the source checkout is behind and clean, show the exact
fast-forward plan and ask for consent before:

```bash
git -C "<kit-path>" merge --ff-only "<remote>/<default-branch>"
```

If the fast-forward fails or is not possible, stop without attempting another
update strategy.

### 4. Preview project asset refresh

Review the selected checkout's installer and entrypoint, then run:

```bash
bash "<kit-path>/install.sh" --target "<project-root>" --dry-run --no-install
```

Capture the output and report:

- Source commit being installed.
- Target root.
- Files to create, append, or merge, and files already identical.
- Any conflict or path that the installer refuses to overwrite.
- Whether hook activation, `.venv` verification/creation, or other side
  effects require an explicit flag/choice.

If the installer fails, reports conflicts, or unexpectedly plans a write
outside the project (except a separately approved hook location), stop. Do
not bypass conflicts with `cp`, `rsync`, force flags, or manual edits.

### 5. Get consent and apply

Ask the user to confirm the exact source commit, target directory, file plan,
and hook/environment behavior. If declined, stop without changes to the target.

After approval, apply through the selected checkout's installer. Use only the
options needed to match the approved plan, for example:

```bash
bash "<kit-path>/install.sh" --target "<project-root>" --yes --no-install
```

Use `--skip-hooks` or `--skip-venv` only if those options are supported by the
reviewed installer and the user explicitly chose to skip those actions. Do not
run `--setup-mcp` during refresh.

If the installer encounters a differing installed file, report the exact
relative path and stop. Do not overwrite or modify that file. Offer to compare
the source and project versions for a manual, user-directed merge.

### 6. Verify and report

Inspect Git status and diff in the target after installation. Confirm only
approved project-local kit assets changed; report hook or environment changes
separately. Verify prompt/skill counts against the refreshed source, but do not
claim Copilot has loaded them.

Finish with a concise report:

- Source remote/branch and resulting source commit.
- Target project path.
- Created/updated/equal/conflicting asset counts and notable paths.
- Hook and `.venv` outcome.
- Whether Snowflake was untouched (it must remain untouched).
- Reminder to review and commit the project changes and reload/reopen the
  workspace so Copilot can discover refreshed assets.

Never claim an update succeeded unless the installer completed and the
resulting changes were inspected.
