---
name: small-blocks
description: Work through a task in small, independently-reviewable blocks instead of one big change. Plan the work into ordered chunks, then implement → verify → stage → pause for review (via Hunk) → continue, one block at a time. Requires the Hunk CLI. Use when the user invokes small-blocks with a prompt, or asks to "break this up", "work in small blocks/chunks", "do this incrementally", "pair on this", or "let me review as you go".
---

# Small Blocks

Turn a single prompt into a **plan → work in small blocks → review → continue** loop. The user
stays in the driver's seat: they review each block (ideally in Hunk) and commit between blocks.

The user's task is whatever prompt they passed to this skill. If no prompt was given, ask what
they want to work on before planning.

Review happens in [Hunk](https://github.com/modem-dev/hunk), which must be installed. Hunk ships a
version-current guide to its own commands: run `hunk skill path` and read that file before driving a
session. It is the source of truth for session commands.

## Operating principles

- **Small and independently reviewable.** Each block is a coherent slice a human can review in one
  sitting and reason about on its own.
- **Verifiable per block.** Every block names how it's checked (typecheck, test, lint, run, or a
  Hunk read). Prefer an ordering where each block can be verified as it lands.
  - For interdependent refactors, sequence so verification is maximized: **add the new thing first →
    migrate consumers → delete the old thing last.** If a block genuinely can't compile until a
    later one lands, say so explicitly in the plan rather than pretending it's green.
- **The user reviews and commits.** By default you implement and stage; the user reviews and runs
  the commit. Confirm this split at the start — some users will want you to commit too.
- **One block at a time. Then stop.** After staging a block, hand off and wait. Do not run ahead.

## Configuration (confirm once, up front)

Ask or infer, then state your assumptions:

- **Who commits?** User (default) or agent.
- **Hunk session.** If a live session exists (`hunk session list`), drive it. If not, ask the user
  to open Hunk in their own terminal. If Hunk isn't installed, stop and ask them to install it.
- **Verify command(s):** the project's typecheck / test / lint (discover from package.json, Makefile,
  etc.). Run the relevant one after each block.

## Phase 1 — Plan

1. Explore just enough to scope the work (read the key files; don't boil the ocean).
2. Produce an **ordered list of blocks**. For each block give: a title, the files/areas it touches,
   what it does, and its **verify step**.
3. Create a task list (one task per block) so progress is trackable.
4. Present the plan and get a thumbs-up (or adjust) **before writing code**. If the request is
   ambiguous, ask rather than guess.

Keep blocks genuinely small — if a block touches a dozen files doing unrelated things, split it.

## Phase 2 — Execute (loop per block)

For the current block:

1. **Implement** only that block.
2. **Verify** it with the relevant command; report the result honestly. If it can't fully pass yet
   because of a later block, say which block clears it.
3. **Stage** the block's files:
   ```bash
   git add <files-for-this-block>
   ```
   File-level staging is enough when blocks are file-partitioned. For sub-file splits, tell the user
   to run `git add -p <file>` in their own terminal (interactive staging isn't available to you).
4. **Scope the review view.** If a Hunk session is live, reload it to show exactly what's staged:
   ```bash
   hunk session reload --repo . -- diff --cached
   ```
   (A freshly opened Hunk session shows the full working-tree diff — reloading to `--cached` narrows
   it to just this block. If the user reopens Hunk mid-run, re-run this — and see the note about
   notes not surviving a restart.)
5. **Annotate what they wouldn't spot.** Leave inline notes on the behavior changes, the deletions,
   and the judgment calls — not on every hunk. Always apply a batch with `--focus`:
   ```bash
   printf '%s' '{"comments":[{"filePath":"src/foo.ts","newLine":42,"summary":"...","rationale":"..."}]}' \
     | hunk session comment apply --repo . --stdin --focus
   ```
   **`--focus` is not optional.** Without it the notes attach to the session but Hunk's agent-note
   layer can stay hidden (`hunk session get --repo .` reports `Agent notes visible: no`), so the
   user sees a bare diff and assumes the notes were never written. Verify after applying:
   ```bash
   hunk session get --repo . | grep -i "agent notes"     # want: yes
   ```
   Review notes are the one place it's _right_ to reference the previous state of the code
   ("this used to be X") — that framing belongs in the note, not in a source comment.
6. **Hand off.** Briefly summarize what's in the block, show the exact `git commit` command (with a
   clear message), and — unless configured to commit yourself — **stop and wait**.

### On "continue" (or when the user leaves review notes)

1. Confirm the previous block landed: `git log --oneline -1` (and that its files aren't still
   pending).
2. Read any Hunk review notes:
   ```bash
   hunk session comment list --repo . --type user --json
   ```
   Answer every question. If a note asks for a change, make it; if the file was already staged,
   re-`git add` it so the fix is included. When notes are addressed, clear them:
   ```bash
   hunk session comment clear --repo . --yes                 # agent notes only
   hunk session comment clear --repo . --yes --include-user  # ...and the user's too
   ```
   Plain `--yes` clears only agent notes. Reach for `--include-user` (or `--all`) only once you've
   actually addressed the user's notes — it destroys them.
3. Mark the task done, move to the next block, repeat Phase 2.

## Phase 3 — Finalize

After the last block:

- Run the full verification (typecheck + tests) and report the end state.
- Summarize the commits/blocks.
- If you set up a safety stash, drop it (reference it explicitly, e.g. `git stash drop stash@{0}`).

## Optional safety net

If there's pre-existing uncommitted work, or the user wants a backstop, capture a restore point
before starting and record the base commit:

```bash
git rev-parse HEAD                       # base SHA — note it for rescue
git stash push -u -m <task>-wip && git stash apply   # backup + keep changes in the tree
```

Rescue to the pre-work state: `git reset --hard <base-sha> && git stash apply stash@{0}` (this also
undoes any commits already made — flag that before running it). Always reference `stash@{0}`
explicitly; stash stacks get deep.

## Hunk quick reference

Hunk ships its own version-current skill — `hunk skill path` prints it. **That file is the source
of truth**; the list below is a convenience subset and can age behind the installed Hunk. Read the
bundled skill before doing anything here that isn't on this list.

Inspect / scope:

- `hunk session list [--json]` — find the live session.
- `hunk session get --repo .` — path, repo, current focus, and `Agent notes visible`.
- `hunk session reload --repo . -- diff --cached` — scope the view to the staged block.
- `hunk session reload --repo . -- diff <base-sha>` — the whole changeset so far (stable across commits).

Notes — reading the user's:

- `hunk session comment list --repo . --type user --json` — read the user's review notes.
- `hunk session comment clear --repo . --yes` — clear **agent** notes once addressed.
- `hunk session comment clear --repo . --yes --include-user` — also destroy the user's notes. Only
  after you've actually answered them.

Notes — writing your own:

- `hunk session comment apply --repo . --stdin --focus` — apply a JSON batch (preferred).
- `hunk session comment add --repo . --file <p> --new-line <n> --summary "..."` — one-off.
- **Always pass `--focus` when writing notes.** It turns on Hunk's agent-note layer. Without it the
  notes attach but may never render, and the user sees a bare diff — confirm with
  `hunk session get --repo . | grep -i "agent notes"` (want `yes`).
- Notes are **per-session**: if the user restarts Hunk, the session ID changes and every note is
  gone. Re-`reload` and re-apply them.

Never run interactive Hunk commands (`hunk diff` / `hunk show`) — the TUI belongs to the user;
drive it via `hunk session *`.

## Guardrails

- Don't batch multiple blocks together to "save time" — the point is reviewable increments.
- Don't commit on the user's behalf unless they asked you to.
- Report verification faithfully: if a block's check fails or was deferred, say so plainly.
