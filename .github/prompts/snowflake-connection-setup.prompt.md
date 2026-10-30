---
name: snowflake-connection-setup
description: "Interactive wizard that cleans conflicting environment overrides, creates or reuses a named Snowflake CLI connection per project target, validates it, and wires the project selection without storing credentials in project files."
argument-hint: "Optional existing Snowflake CLI connection name"
agent: "agent"
---

# Configure this project's Snowflake CLI connection (wizard)

Walk the user end to end through setting up a named Snowflake CLI connection
for the current project and one of its targets (for example `dev`, `staging`,
`prod`), then wire the project to select that connection automatically.
Credentials and authentication live only in the user's Snowflake CLI
configuration (`~/.snowflake/connections.toml` or `$SNOWFLAKE_HOME`); the
project stores only the connection name. Do not create or alter any Snowflake
objects, roles, grants, or account settings.

Read repository instructions first. Do not infer the account, environment,
role, warehouse, database, schema, authentication method, or connection name.
Ask at each decision point; never choose silently.

## Procedure

0a. **Sanitize the shell environment** (explicit consent). List the *names*
    (never the values) of exported `SNOWFLAKE_*` variables in the active
    environment (for example `env | grep -o '^SNOWFLAKE_[A-Z_]*'`). Variables
    such as `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`,
    `SNOWFLAKE_AUTHENTICATOR`, and `SNOWFLAKE_CONNECTIONS` override
    `connections.toml`, so a profile selection is wasted while they are
    globally exported. A `SNOWFLAKE_DEFAULT_CONNECTION_NAME` set by this kit's
    project `.envrc` block is expected and not a conflict. If global overrides
    exist, explain this and ask whether to comment them out of the user's
    shell startup files. On no, abort the wizard. On yes, locate the exact
    export lines in the user's shell profiles (`~/.zshenv`, `~/.zprofile`,
    `~/.zshrc`, `~/.bash_profile`, `~/.bashrc`, `~/.profile`, fish config),
    show the exact diff (comment out, never delete), create a timestamped
    backup of each file, and apply only after confirmation. Never use `sudo`;
    if a file is not writable, report it and let the user fix permissions.
    Remind the user that already-running shells keep old exports until
    restarted.
0b. **Check prerequisites**: `snow --version` and `direnv version`. If
    Snowflake CLI is missing, ask for explicit consent to install it with
    Snowflake's official installer (macOS/Linux: download
    `https://sfc-repo.snowflakecomputing.com/snowflake-cli/install.sh` over
    HTTPS and run it with `NON_INTERACTIVE=1 SKIP_PATH_PROMPT=1`, installing
    under `~/.local/share/snowflake-cli` without editing shell profiles), or
    point to the kit installer (`install.sh`) which offers the same step. On
    no, abort with the
    [official instructions](https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation).
    Missing `direnv` is not fatal; note it and see the fallback at the end.
1. **Locate the project and target.** Identify the project root. If project
   configuration declares environments or targets (for example dbt
   `profiles.yml` targets or project documentation), list them and ask which
   one to configure. Otherwise ask for the account identifier and environment
   name directly. Never read files that may contain credentials.
2. **Suggest the connection name** `<project>-<target>` (for example
   `sales-pipeline-dev`); let the user edit it. If the user passed a
   connection name as the argument, offer it as the default.
3. **Check for collisions** with `snow connection list`. Show only connection
   names and non-secret parameters; never print passwords or tokens.
   - Same name exists: warn, then offer to reuse it as-is or replace it
     (rewrite only that section of `connections.toml` after a previewed
     diff and approval).
   - Different name but same account and user: warn and offer reuse before
     creating a near-duplicate. Avoid leaving two interchangeable profiles
     for the same account/user — that reintroduces the ambiguity this wizard
     exists to fix.
4. **Choose the authentication method** (ask explicitly):
   - **Browser SSO/OAuth (preferred for human accounts).** Run
     `snow connection add --connection-name "<name>" --account "<account>"
     --user "<user>" --authenticator externalbrowser --no-interactive`.
     No secret is involved; the browser opens on first use or test.
   - **Programmatic access token (PAT) / password.** Print the Snowsight
     path for generating a PAT (Profile → Settings → Authentication →
     Programmatic access tokens) and guide generation. Then either:
     - *Transcript-free (offer first):* the user runs
       `snow connection add --connection-name "<name>"` in their own
       terminal and completes its interactive prompts there; or
     - *Chat paste (explicit opt-in):* warn that a pasted secret lands in
       the chat transcript, then let the user paste the token as a normal
       reply. Write it only to the user-level `connections.toml` under the
       chosen connection name with owner-only permissions (0600). Never
       echo or re-print it, never log it, never place it on a command line
       (shell history/process lists), and never write it under the project
       tree.
   - **Key pair.** Point to the official key-pair documentation; the user
     configures `private_key_file` in their own terminal.
5. **Validate** (network access; explicit consent). State the selected
   connection name and ask before running
   `snow connection test --connection "<name>"`. Report the resolved
   account, user, and role. Do not run SQL. Do not retry with another
   profile on failure. If the user declines, say the profile was not
   verified.
6. **Wire the project-local selection** before editing:
   - Add a managed block to the project's `.envrc` setting
     `SNOWFLAKE_DEFAULT_CONNECTION_NAME` to the chosen connection name.
   - `direnv` must already be hooked into the user's shell. The user must run
     `direnv allow` in the project and may need to reload the shell or
     re-enter the directory. Do not run `direnv allow` for them.
   - This environment variable selects a profile; it does not contain
     credentials. It is scoped to the project by `direnv`.
   Inspect `.envrc` and `.gitignore` before changing either. Preserve all
   unrelated content. Preview the exact diff and ask the user to confirm
   before writing. If `.envrc` is a symlink, contains a conflicting
   `SNOWFLAKE_DEFAULT_CONNECTION_NAME` assignment outside a kit-managed
   block, or cannot be safely updated, stop and provide the single export
   line for a manual merge instead. Do not overwrite or execute `.envrc`.
   Quote the connection name as a shell literal (for example with Python's
   `shlex.quote`) and use these markers exactly:

   ```sh
   # snowflake-ai-data-developer:start
   export SNOWFLAKE_DEFAULT_CONNECTION_NAME='connection-name'
   # snowflake-ai-data-developer:end
   ```

   If `.envrc` already contains one valid kit-managed block, replace only
   that block after approval. Refuse duplicate or malformed kit markers.
   Treat `.envrc` as developer-specific by default: after inspecting
   `.gitignore`, offer to add `.envrc` there; do not alter `.gitignore`
   without separate approval. For team-shared setups, profile names and
   `direnv` conventions must be agreed by the team and every developer still
   configures their own credentials.
7. **Offer another target.** If the user wants a second environment (for
   example `prod`), loop from step 2. The `.envrc` block selects exactly one
   default connection; additional profiles are used explicitly with
   `--connection "<name>"`. Ask which one should be the project default.
8. **Report**: whether the profile was tested, which project files changed,
   and that credentials remain user-level. Do not claim `direnv` is active
   until the user has allowed the file and verified it in their shell.
   MCP configuration stays separate; point to `/snowflake-mcp-setup`.

If `direnv` is unavailable or the user declines `.envrc`, do not write a
selection file that Snowflake CLI will not automatically read. Explain that
they can select the connection explicitly with `--connection "<name>"` for
Snowflake CLI commands, or install and initialize `direnv` separately.

## Safety

- Never commit, print back, or log a secret. A token pasted in chat remains
  in the transcript: say so before accepting one and always offer the
  transcript-free alternative first.
- Write secrets only to the user-level Snowflake CLI configuration, never to
  `.envrc`, `.env`, project settings, logs, or shell history.
- Never read or display existing credential values from `config.toml` or
  `connections.toml`; edit only the sections the user approved, preserving
  all other content byte for byte.
- Do not assume a successful CLI command means the selected profile has
  access to a particular database or object.
- Treat connection testing and CLI installation as network access and
  require explicit approval for each. Do not retry using another profile.
- Make no changes until the user approves the exact diff or command.

Snowflake CLI documentation:
https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/configure-cli
