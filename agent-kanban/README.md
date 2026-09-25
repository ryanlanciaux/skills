# Agent Kanban

A lightweight skill for watching agent work. A dark, compact kanban shows planned
owners, active work, review, blockers, completion evidence, and recent activity.
The browser is read-only: search, filter, and inspect. Agents update through a
transactional CLI. No MCP, external service, package installation, or model calls
are needed to serve or refresh the board.

Requires Python 3.10+ with SQLite support on Linux/macOS. The shell launcher checks dependencies and prints setup instructions if Python or SQLite support is missing; it installs nothing. See [setup and recovery](references/setup.md). Copy this folder to your agent's skill
directory (for Codex, `${CODEX_HOME:-$HOME/.codex}/skills/agent-kanban`), then ask:

> Use $agent-kanban for this goal. Start its viewer and keep task assignments and status current.

The skill is explicitly activated. It describes orchestration handoffs and
resumption in [SKILL.md](SKILL.md); runtime state stays outside this folder.

Manual example:

```sh
export AGENT_KANBAN_STATE="$HOME/.local/state/agent-kanban/example"
export AGENT_KANBAN_ACTOR="lead"
sh scripts/kanban.sh doctor
sh scripts/kanban.sh init --title "Example goal"
sh scripts/kanban.sh add task-01 --title "Deliver the first outcome" --assignee "worker" --criterion "The agreed behavior works"
sh scripts/kanban.sh start --port 4317
sh scripts/kanban.sh status
sh scripts/kanban.sh stop
```

The default bind is localhost (`127.0.0.1`). For a trusted private network, set
the bind address in the process environment:

```sh
AGENT_KANBAN_HOST=0.0.0.0 sh scripts/kanban.sh start --port 4317
```

You can use a specific interface IP instead. Precedence is explicit `--host`,
then `AGENT_KANBAN_HOST`, then `127.0.0.1`; unset or blank environment values use
localhost. Changing the address of a running board requires stop/start. Keep
machine-specific settings outside the distributed skill folder.

Use `--public-url` to record the address viewers should open. The server has no
authentication; network access controls are external. No HTTP endpoint can modify
tasks. The skill does not launch agents itself, configure networking, or survive a
reboot automatically; `start` resumes the persisted board.

Run checks with `python3 -m unittest discover -s tests -v`. The optional browser
check requires Playwright and Chromium already installed; run
`node tests/browser.mjs <output-directory>`. All test boards use temporary state.
