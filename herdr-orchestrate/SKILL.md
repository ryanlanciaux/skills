---
name: herdr-orchestrate
description: >
  Orchestrate coding agents in Herdr tabs using profiles.json.
  Use when the user asks to run work via Herdr, or invokes
  /skill:herdr-orchestrate [profile] [task]. Simple orchestration
  (parent opens workers by lane), not a DAG. Requires HERDR_ENV=1.
---

# Herdr orchestration

Simple orchestration, not a DAG. No stage graph: split work, open workers, wait, review, integrate. Deliver a working result, not idle tabs.

## 1. Profile

Read **profiles.json beside this SKILL.md** from this skill's directory — not the project. If `~/.config/herdr-orchestrate/profiles.json` exists, merge its `agents` and `profiles` on top (local wins).

- Profile arg → `profiles.<name>`. Rest is the task. Else `defaultProfile`.
- Unknown name → list and ask. Do not substitute.
- `roles` maps lanes to `agents` aliases. Alias `command` must be a nonempty string array. Invalid config → stop.
- Lanes: `orchestrator` (parent), `simple`, `complex`, `reviewer`. Extra keys are more lanes.
- Launch `agents[roles.<lane>].command`. Workers do not pick a model.
- If this pane is not the orchestrator, start that command, submit the same profile+task, stop.
- Never swap a fast model or another provider.

```sh
test "${HERDR_ENV:-}" = 1
```

If false, stop. Do not control Herdr from outside. Use the installed CLI (`herdr --help`); do not reuse remembered syntax.

## 2. Launch

Read the task and code before splitting. Fan out ≤ `maxWorkers` on non-overlapping files, same cwd as the orchestrator. One trivial task → one worker. Default: no worktrees. Use a worktree only when same-cwd would collide (overlapping dirty edits, can't serialize). `worktrees: true` isolates independent changes; `worktrees: false` never uses them. Never switch a dirty checkout.

Start the lane command in a pane (`--no-focus`). Do not pass the task as argv. Wait for idle, then submit: outcome, owned files, report path, local commits only (no push unless authorized).

**Send ≠ submitted.** Read the transcript until work actually started.

Every worker, on done/blocked: update the report and notify — never send keys/text to the parent pane.

```sh
herdr notification show "Task ready" --body "Report: <path>; commit: <hash>"
```

## 3. Finish

Don't end the turn with silent workers. Bounded waits (`waitSeconds`). Inspect idle/done/blocked. Handle routine approvals; ask only for product/authority calls.

`maxHeavyJobs` caps installs/tests/builds/browsers. Exclusive ownership of shared runtime.

Review stable commits with `roles.reviewer` in a separate context. Integrate only if authorized. Close worker tabs you created. Ship the first usable slice; report blockers with an owner.
