---
name: snowflake-connection-setup
description: "Select a user-level Snowflake CLI connection for this project without storing credentials in project files."
argument-hint: "Optional existing Snowflake CLI connection name"
agent: "agent"
---

# Configure this project's Snowflake CLI connection

Help the user select a named Snowflake CLI connection for the current project.
The actual connection and authentication remain in the user's Snowflake CLI
configuration; project configuration may contain only the connection name.
Use Snowflake CLI's documented `SNOWFLAKE_DEFAULT_CONNECTION_NAME` environment
variable, scoped to this project with `direnv`. Do not create or alter any
Snowflake objects, roles, grants, or account settings.

Read repository instructions first. Do not infer the account, environment,
role, warehouse, database, schema, authentication method, or connection name.

## Procedure

1. Identify the project root and ask which existing Snowflake CLI connection
   name this project should use. Do not inspect or print credential-bearing
   `config.toml` or `connections.toml` files.
2. Check local prerequisites with `snow --version` and `direnv version`. Do not
   install either tool automatically. If the user has not created a connection,
   ask them to run `snow connection add --connection-name "<name>"` in their
   own terminal and complete its interactive prompts there. Never collect
   passwords, tokens, private keys, or other secrets in chat or run a command
   that includes them. Explain that Snowflake CLI stores the connection in the
   user's configuration directory.
3. If the user wants a live connection test, state the selected connection
   name and ask for explicit confirmation before running
   `snow connection test --connection "<name>"`. Do not run SQL. Otherwise,
   skip the test and say that the profile was not verified.
4. Explain the project-local selection before editing:
   - Add a managed block to the project's `.envrc` setting
     `SNOWFLAKE_DEFAULT_CONNECTION_NAME` to the chosen profile name.
   - `direnv` must already be hooked into the user's shell. The user must run
     `direnv allow` in the project and may need to reload the shell or re-enter
     the directory. Do not run `direnv allow` for them.
   - This environment variable selects a profile; it does not contain
     credentials. It is scoped to the project by `direnv`.
5. Inspect `.envrc` and `.gitignore` before changing either. Preserve all
   unrelated content. Preview the exact diff and ask the user to confirm
   before writing. If `.envrc` is a symlink, contains a conflicting
   `SNOWFLAKE_DEFAULT_CONNECTION_NAME` assignment outside a kit-managed block,
   or cannot be safely updated, stop and provide the single export line for a
   manual merge instead. Do not overwrite or execute `.envrc`.
6. Quote the connection name as a shell literal (for example with Python's
   `shlex.quote`) when writing the export. Use these markers exactly:

   ```sh
   # snowflake-ai-data-developer:start
   export SNOWFLAKE_DEFAULT_CONNECTION_NAME='connection-name'
   # snowflake-ai-data-developer:end
   ```

   If `.envrc` already contains one valid kit-managed block, replace only that
   block after approval. Refuse duplicate or malformed kit markers.
7. Treat `.envrc` as developer-specific by default. After inspecting
   `.gitignore`, offer to add `.envrc` there to avoid committing a
   user-specific profile selection. Do not alter `.gitignore` without separate
   approval. If the user instead wants a team-shared setup, explain that
   profile names and `direnv` conventions must be agreed by the project team
   and that every developer still configures their own credentials.
8. Report whether the profile was tested, which project files changed, and
   that credentials remain user-level. Do not claim that `direnv` is active
   until the user has allowed the file and verified it in their shell.

If `direnv` is unavailable or the user declines `.envrc`, do not write a
selection file that Snowflake CLI will not automatically read. Explain that
they can select the connection explicitly with `--connection "<name>"` for
Snowflake CLI commands, or install and initialize `direnv` separately.

## Safety

- Never read credential file contents, request secrets, or put credentials in
  `.envrc`, `.env`, project settings, logs, or shell history.
- Do not assume a successful CLI command means the selected profile has access
  to a particular database or object.
- Treat connection testing as a network access check and require explicit
  approval. Do not retry using another profile.
- Make no changes until the user approves the exact project-file diff.

Snowflake CLI documentation:
https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/configure-cli
