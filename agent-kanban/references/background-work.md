# Background work and recovery

Read when a tracked task uses detached agents or asynchronous commands, or has
stopped reporting progress. The board records what agents report; it cannot
check liveness, approve commands, or resume anyone.

## Own the wait

- Keep a private record of card, agent, runner session/job ID, result location
  and supervisor. Keep machine paths, raw logs and launch settings out of the
  skill and the board.
- Verify the job started, then check it at bounded checkpoints using the runner's
  own status/wait tools. It may be running, idle, done, failed or waiting for
  permission; a PID, open tab or recent card update proves none of these.
- Use the original job handle and result file, not an extra watcher. Check
  whether the job already finished before waiting again.
- Notifications are hints, not supervision. Consume results and reconcile the
  card even if one was missed. Don't end a turn "waiting" unless a verified
  continuation or a named supervisor owns the next checkpoint.
- Handle approval waits promptly within existing authorization. If blocked,
  record the pending action and report it; never broaden permissions or disable
  security checks to keep work moving.

## Trust real results only

- Record the command's own exit status and output. A pipe through `tail`, `grep`
  or `tee` can hide failure; redirect instead:

  ```sh
  if command-to-check > "$CHECK_LOG" 2>&1; then rc=0; else rc=$?; fi
  cat "$CHECK_LOG"; exit "$rc"
  ```

- Confirm a focused test run selected only the intended tests (argument
  forwarding after `--` varies). Stop a run that unexpectedly expands.
- Read output for failures, skips and missing prerequisites before calling
  anything evidence. Reuse results that still match the current files.

## Recover a stalled handoff

1. Inspect cards, runner state, results and changes before restarting anything;
   never duplicate a live owner.
2. With authorization, transfer ownership or stop only the task's own stalled
   session, keeping its edits and logs.
3. Re-file by evidence: unverified finished work → `in_review`; reviewed →
   `done`; unowned unfinished → `backlog` with a planned owner; real impediment →
   `blocked` with the next action. Staleness alone proves nothing.
4. Before yielding, account for every owned `in_progress` card, and pause the
   board if nothing authorized is running. Keep branch/worktree work distinct
   from integrated changes.
