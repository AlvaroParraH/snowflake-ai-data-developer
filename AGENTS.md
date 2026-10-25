# Repository guidance for coding agents

This file applies to agents contributing to the Snowflake AI Data Developer
kit repository. It does not replace the Snowflake development guidance that
the kit installs into application projects.

## Read the existing sources of truth

- Read [`.github/copilot-instructions.md`](.github/copilot-instructions.md)
  before changing Snowflake guidance or examples. It defines platform safety,
  project conventions, and local documentation validation.
- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the kit components,
  distribution boundary, and design decisions.
- Read the relevant skill, prompt, custom agent, script, and tests before
  editing them. Preserve established interfaces and fail-safe behavior.
- For installer and onboarding behavior, consult [README.md](README.md) and
  [Copilot setup](docs/copilot-setup.md).

## Contribution expectations

- Keep the kit Snowflake-focused and Copilot-native. Do not add Databricks,
  Qubika, Codex, or other platform material as implementation guidance. A
  clearly labeled comparison may be retained only when it prevents a concrete
  misconception.
- Treat examples as proposals, not corporate policy. Preserve project-specific
  conventions, least privilege, explicit approvals, bounded read-only
  exploration, secret hygiene, and review gates.
- Keep instructions, skills, custom agents, and prompts in their appropriate
  `.github/` locations. Keep installer and initializer behavior in
  `scripts/`; update tests and documentation for behavior changes.
- Root contributor documents (`AGENTS.md` and `ARCHITECTURE.md`) describe this
  kit repository and are not installed into consuming projects.
- Do not introduce automatic Snowflake connections, account changes, global
  assistant configuration, or overwriting update behavior without an explicit
  request and documented approval flow.
- Preserve unrelated user changes. Do not commit or push unless asked.

## Validation

For Python or installer changes, run the focused tests where practical and
then the complete standard-library suite:

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py' -q
```

For shell changes, run:

```bash
bash -n install.sh .githooks/pre-commit
```

For documentation or customization changes, verify local Markdown links,
fenced blocks, frontmatter, and any counts or paths affected by the change.
Run `git diff --check` before finishing. Do not execute illustrative Snowflake
SQL as a documentation check.
