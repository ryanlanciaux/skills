---
name: herdr-orchestrate
description: >
  Orchestrate coding agents in Herdr tabs with named profiles from profiles.json.
  Use when the user asks to run work via Herdr tabs/panes, delegate through Herdr,
  or invokes /skill:herdr-orchestrate [profile] [task]. Profiles such as difficult
  are JSON entries, not separate skills. Covers routing, verified submission,
  active monitoring, handoffs, review, integration, and delivery. Requires HERDR_ENV=1.
---

# Herdr orchestration

Deliver a working outcome, not idle agent tabs.

## 1. Profile and context

Read **profiles.json beside this SKILL.md** from this skill's absolute directory — never the edited project.

- Explicit profile arg → that entry (`difficult` → `profiles.difficult`). Remaining text is the task, else the established conversation task.
- No named profile → `defaultProfile`.
- Unknown name → list names and ask; do not substitute.
- Resolve roles via `agents`. Aliases must exist; commands nonempty string arrays; concurrency/wait positive integers. Invalid config → stop.
- Never silently swap a fast model or another provider.
- This file is the workflow; commands and roles live in JSON.

```sh
test "${HERDR_ENV:-}" = 1
```

If false, stop Herdr control. Do not attach to the user's focused session from outside Herdr.

Read the Herdr skill if available, else `herdr --skill`. Inspect `herdr --help` and relevant groups. **Installed CLI wins**; do not reuse remembered syntax. Record parent pane/workspace IDs from the environment/current-pane response.

## 2. Delivery and ownership

Read the task and real code before splitting. Do not delegate a feature name without a flow and acceptance.

Ledger in the project's existing handoff dir, else ignored/local `.data/herdr-orchestrate/<run-id>/`: outcome + first deliverable; protected branches/data/services/ports/forbidden ops; parent identity, profile, launched commands; per task: role/agent, branch/worktree, tab/pane IDs, owned files, deps, acceptance, report path, state, commit; heavy-lane owner, runtime ownership, next handoff.

≤ `maxWorkers`. One simple task → one worker. Non-overlapping file ownership; settle shared route/API contracts first. Independent implementation may proceed while another lane runs acceptance.

Isolated worktrees for independent code changes; never switch a dirty checkout under an agent. Inspect repo state first. Tabs when requested, `--no-focus`, IDs from Herdr — not guessed numbers.

## 3. Launch and verify submission

Start the configured command interactively in its pane; shell-quote each command-array argument. Do not pass the task as an argv prompt. Prefer agent-aware commands; else documented pane commands.

Wait for the agent prompt, then submit. Each assignment includes:

1. Outcome and acceptance.
2. Owned files/worktree and prohibited edits.
3. Existing contracts/deps and required reading.
4. Whether installs/tests/builds/browser runs are authorized now.
5. Report path, checkpoints, and the §5 handoff rule.
6. Local commits only; no main merge/push unless authorized.

**Send ≠ submitted.** Read the transcript: task consumed and relevant work started. Status is insufficient — the agent may still be on an older prompt. Unsent input in an agent pane → CLI submit, then inspect again. Cursor may need Enter; steering may need a separate confirm. Do not blindly repeat prompts/keys, interrupt active tools for routine follow-ups, or launch duplicates. A queued follow-up is not yet acted on.

## 4. Keep monitoring

Do not end the turn with workers silently running. After each bounded wait and after your own work, inspect every worker. On `idle`/`done`/`blocked`, read reports/transcripts: idle can mean finished, awaiting approval, or an unsent prompt.

Use native waits when the CLI supports them, e.g. `herdr agent wait <pane> --until idle --until blocked --timeout <waitSeconds*1000>` and `herdr pane read <pane> --source recent-unwrapped --lines 80`. Inspect all workers between waits. Timeout = checkpoint, not a duplicate job. No long blind sleeps.

Handle routine operational approvals already in scope. Ask the user only for a product decision, missing authority, or destructive action. When a worker finishes, start the next review/check/integration step immediately.

A skill is **not a daemon**. If paused or you must stop: save the ledger and state what resumes orchestration. Never claim background monitoring without a verified non-editor wake-up.

## 5. Worker handoffs — never type into the parent

Give every worker:

> On completion or blockage, update your report and post a Herdr notification (task ID, COMPLETE/BLOCKED/READY-FOR-REVIEW, commit, checks run, report path, lane held/released, action needed). Never `pane run`, `agent prompt`, send-text, or send-keys to the parent or a user-controlled pane — that can submit the user's draft.

```sh
herdr notification show "Task ready for review" --body "Report: <abs-path>; commit: <hash>; heavy lane released"
```

Reports + notifications are the handoff. Use documented non-editor IPC only if verified safe. No invented messaging API, editor injection, or background watcher.

Parent input only into assigned agent panes. If the user has taken a pane over, coordinate first.

## 6. Resource lanes

`maxHeavyJobs` is a ceiling. Shared DB/runtime still needs exclusive ownership. Heavy: installs, large suites, builds, browser runs, exports. Code read/write may proceed in other worktrees.

Grant a lane only when the previous owner released it **and** its command finished (inspect processes if unsure). Check orphans after timeouts. Stop only positively identified owned processes — never broad kill. Grant concrete commands/scope. Start focused checks; confirm the selector did not run the whole suite.

Isolated runtimes: new DB/data dir, free ports, owned processes; check uniqueness first. Never drop/reseed existing data or restart unrelated services. A prior acceptance DB is not fresh proof. Failed-test mutations leave artifacts; cleanup uses recorded ownership, not name sweeps.

## 7. Review and integrate

Review stable commits/checkpoints, not half-written diffs. Use the configured reviewer in a separate context, within `maxWorkers`. Author checks are not independent review.

Read the changed flow and callers. Return concrete correctness/data-loss/security/a11y/acceptance defects with a repro and a small fix. Retract wrong findings. Don't reopen settled work for speculative abstractions. Fixes go to the owner; require one small runnable regression for non-trivial logic; rerun focused checks before broader gates. Do not weaken assertions/timeouts, hide failures, or fake green.

Integrate in a worktree if needed. Check shared interfaces and navigation — two working views can still be one inconsistent app. Parent reviews the combined result and integrates only per user authorization. Do not push by default.

After commits/reports are preserved and owned processes are finished, close worker tabs you created. Keep worktrees, evidence, and user data unless cleanup is authorized. Keep a worker only for a concrete next assignment.

## 8. Deliver something usable

Track **implemented → checked → integrated → running** separately. For app work, a commit or server start is not delivery: verify the browser journey, inspect runtime errors, compare requested visuals to screenshots. Don't advertise a URL before it listens and the journey works. Label local-only URLs as such.

Report the next checkpoint and any blocker (owner + action). Ship the first safe usable slice; keep remaining scope in the ledger. Never leave the user to discover that an agent is waiting for your approval.
