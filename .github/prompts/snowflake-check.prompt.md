---
name: snowflake-check
description: "Verify local Snowflake tooling and, with approval, test a configured Snowflake CLI connection without running SQL. Use for Snowflake access readiness checks."
argument-hint: "Optional configured Snowflake CLI connection name"
agent: "agent"
---

# Check Snowflake development access

Verify local Snowflake development prerequisites and, only with the user's
approval, test one explicitly selected Snowflake CLI connection. This is a
connectivity/authentication check, not a database, privilege, dbt, or project
validation. Do not assume Snowflake access or fabricate a successful result.

## 1. Establish scope and permission

- Read repository instructions and identify the project root.
- Ask which configured Snowflake CLI connection to test if the user has not
  named one. Do not inspect or print credential-bearing connection files.
- Before making a network connection, state the selected connection and ask
  the user to confirm the live access test. Local checks do not require this
  confirmation.
- Do not use, request, or expose passwords, private keys, OAuth tokens,
  connection strings, or other secrets. Do not change Snowflake CLI profiles
  or environment variables.

## 2. Check local readiness

Run only non-mutating local checks:

```bash
snow --version
```

Check whether the configured project environment exists when the project uses
one, and identify relevant installed skills under `.github/skills/` by their
directory names. Do not enumerate files under home-directory credential
locations or display their contents. Report missing CLI/environment
prerequisites without installing or updating anything.

If `snow` is not available, report that the Snowflake CLI is missing and link
the user to the official installation guidance:
https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation
Do not install it as part of this check.

## 3. Test the approved connection

After confirmation, test only the selected existing connection:

```bash
snow connection test --connection "<configured_connection_name>"
```

Use the name exactly as provided. If the user requests the configured default,
use the CLI's default connection behavior only after confirming that this is
the intended connection. Do not list or dump profiles to discover it. If this
Snowflake CLI version does not support the command or option, check its local
help (`snow connection test --help`) and report the supported equivalent
before running another command.

Do not run SQL, start dbt, invoke MCP tools, inspect tables, create objects,
change roles/warehouses, or perform writes as part of this check. Do not retry
with a different identity or connection after a failure unless the user
selects it. Treat output as potentially sensitive: summarize the failure
category and redact account, user, host, and credential details.

## 4. Report results

Show a concise table:

| Check | Result | Details |
|---|---|---|
| Snowflake CLI | Pass / Fail / Not checked | Version or missing prerequisite |
| Project environment | Pass / Fail / Not applicable | Local status only |
| Snowflake skills | Pass / Partial / Not found | Installed `snowflake-*` skill names |
| Configured connection | Pass / Fail / Not tested | Connection name and sanitized outcome |

If the connection test passes, say that the configured connection authenticated
at the time of the check. Do not claim database access, required role
privileges, warehouse availability, or readiness to deploy without separately
authorized evidence.

If a check fails, explain it in plain language and provide a safe next step:

- Missing CLI: install it using the official Snowflake instructions.
- Missing connection or authentication setup: ask the user to configure an
  approved Snowflake CLI connection using the CLI's interactive setup or
  consult their Snowflake administrator. Never provide a command containing
  credential values.
- Authentication, network, or policy error: report the sanitized error
  category and direct the user to their Snowflake administrator.
- Missing project skills: explain that the Snowflake kit is not installed in
  this workspace and refer to its documented installer; do not copy files
  automatically.

When ready, mention the available workspace commands:

- `/snowflake-init` — assess and initialize the agreed pipeline folders.
- `/snowflake-mcp-setup` — configure an existing, administrator-approved MCP server.
- `/snowflake-sql-check` — lint selected Snowflake SQL locally without connecting.

Do not claim that any command, connection, or check succeeded unless it was
actually run and its result inspected.
