---
name: agent-kanban
description: "Start and maintain a live, read-only kanban of agent work when the user explicitly asks to use Agent Kanban, watch a goal, or enable its task board. Agents own task creation, assignment, status, review evidence, and updates; viewers only inspect and filter."
---

# Agent Kanban

Use this skill only when explicitly activated by the user or an enabled local handoff from an earlier activation. It is an observability tool, not authorization to expand a goal, spawn agents, resume paused work, or spend additional budget.

## Activate

1. Resolve this skill directory as `SKILL_DIR`. Choose an absolute state directory **outside versioned source**, unique to this workspace/goal. Default conventions: `${XDG_STATE_HOME:-$HOME/.local/state}/agent-kanban/<workspace>-<goal>`. Do not put task data, machine names, private network configuration, or credentials in this skill folder.
2. Run `sh "$SKILL_DIR/scripts/kanban.sh" doctor` first. It checks Python 3.10+, SQLite read/write support and the supported OS without touching board state. If it fails, present its error and setup instructions; read [runtime setup and recovery](references/setup.md) for missing modules, custom interpreters or startup failures. The launcher does not install dependencies. Do not initialize or claim a running viewer until this succeeds. Set `AGENT_KANBAN_STATE` to the state directory and `AGENT_KANBAN_ACTOR` to the actual orchestrator identity. Commands below use these variables; pass `--state` and `--actor` before the subcommand when overriding them.
3. Read any existing board with `sh "$SKILL_DIR/scripts/kanban.sh" list`. For a new state directory, run `init --title "Goal name" --goal "User's intended outcome"`. Never reinitialize or discard an existing board to hide unfinished work.
4. Break the authorized scope into reviewable outcome cards. Include descriptions, acceptance criteria, planned assignee, priority, and dependencies. Represent remaining work honestly; completed historical work needs a reference to existing evidence. Card counts are not time, cost, or effort estimates.
5. Start the viewer with `start --port 4317`. The distributed default is localhost (`127.0.0.1`). For authorized network access set `AGENT_KANBAN_HOST` in the CLI process environment, e.g. `0.0.0.0`, a specific interface IP, or `::`. An explicit `--host` overrides the environment; unset/blank environment values use localhost. Optional `--public-url` records a reachable URL; it does not configure DNS or networking. These are runtime settings, never shareable source edits. The viewer has no authentication: bind to trusted interfaces/networks. Do not change firewall, VPN, or port-forwarding settings automatically.
6. Confirm `status` and `/health` respond, then give the user the reachable link. `start` detaches the process; it persists beyond the tool call, not across machine restarts. Reuse the same board with `start` after a restart. Use `stop` to stop this board only. A changed bind requires stop/start.

## Keep orchestration and cards synchronized

- **Backlog:** planned work, with an intended agent/role. A planned assignee is not a running agent. Include runner, model and worker identity in assignments when known (for example, `Runner · Model · worker-01`). Update the identity on real handoff or fallback; never leave a stopped model labeled as the active worker. Add dependencies in creation order with `--depends-on ID...`.
- **In progress:** the actual agent atomically `claim`s its card immediately before starting. Starting via `move` also requires an assignee; prefer `claim` to prevent competing ownership. Dependencies must be done.
- **In review:** the worker records implementation/test evidence, names the real reviewer, and moves the card before handing off. This is agent review, not a request for human approval.
- **Done:** the reviewer verifies the acceptance criteria and records concrete review/check evidence before moving the card. Do not equate generated code, a successful tool call, or one partial check with the full acceptance contract.
- **Blocked:** record the specific blocker and next resolving action. On interruption, cancellation, or pause, reconcile active cards to backlog/blocked/review according to reality; do not leave fictional running agents. Set `board --mode paused --summary "Reason and next step"` when the goal is paused. Set complete only when the whole authorized goal is complete.
- Update at claim, material milestone, blocker, review, completion, and scope change. `note` records progress without changing status. The orchestrator must still supervise already-authorized jobs; the browser's refresh is not agent supervision. Do not create agents, repeated tests, or model calls merely to refresh the board.
- For edit/move/note, first `show ID`, then pass its `--expected-revision N`. A conflict requires rereading/reconciling; never blindly retry with a new revision. `claim` is atomic even without this flag. Do not overwrite another agent's scope or ownership without a coordinated handoff.
- `--criterion` replaces the criteria list on edit; `--depends-on` replaces dependencies (no values clears them); `--evidence` appends. If completed work is reopened, review downstream cards and revoke obsolete completion claims.
- Preserve actual failures and incomplete validation in evidence/notes. Never store secrets or raw sensitive logs; anyone reaching the viewer can read the board. HTTP supports viewing only; task mutations go through the CLI with workspace filesystem access.

## Agent handoff and resumption

Before delegation, include the exact skill script, state path, card ID, current revision, actor identity, owner scope, acceptance criteria, and status-update requirement in the delegate's prompt. Use [references/agent-handoff.md](references/agent-handoff.md). The lead reconciles cards after agent results or interrupts. Model/provider rules come from the workspace, not this skill. The board does not itself spawn or monitor agent processes.

For detached agents or background commands, follow [background work and recovery](references/background-work.md). Before ending supervision, reconcile every owned active card or hand off to a confirmed supervisor.

Persist activation in a **local, untracked** pointer. In Git, use `git rev-parse --git-path info/agent-kanban.json` (resolve the returned path against the workspace). Example:

```json
{"enabled":true,"skill_dir":"<absolute installed skill directory>","state_dir":"<absolute private state directory>"}
```

The local pointer may also contain `"environment":{"AGENT_KANBAN_HOST":"<authorized bind address>"}`. Apply that host setting to this board's CLI process environment when resuming; do not modify global shell configuration or package defaults. Explicit command-line host selection still takes precedence.

Add a brief workspace agent instruction to read that pointer when it exists, load this skill, and include its handoff when delegating. For non-Git workspaces use an explicitly ignored local pointer and document its location. Never activate a board merely because this skill is installed. Resuming agents must read the board and current user instructions; a paused board stays paused until work is authorized. To disable tracking, set `enabled` false and stop the server if requested.

## Command examples

```sh
sh "$SKILL_DIR/scripts/kanban.sh" add task-01 --title "Implement the agreed behavior" --assignee "implementation agent" --reviewer "lead" --priority high --criterion "Observable acceptance condition"
sh "$SKILL_DIR/scripts/kanban.sh" claim task-01 --note "Starting the assigned scope"
sh "$SKILL_DIR/scripts/kanban.sh" show task-01
sh "$SKILL_DIR/scripts/kanban.sh" move task-01 --expected-revision 2 --status in_review --reviewer "lead" --evidence "Changed files and focused check results" --note "Ready for lead review"
```

Use the shell launcher for commands so missing dependencies get setup guidance. Existing `python3 scripts/kanban.py` calls remain supported when the runtime is available. Use `--help` or `<command> --help` for exact options. `list`/`show` return JSON; database transactions protect concurrent changes. `server.log`, `server.json`, and SQLite/WAL files stay in the private state directory. Back up the database with SQLite's backup API or stop writers first; copying only a live database file can omit WAL data.
