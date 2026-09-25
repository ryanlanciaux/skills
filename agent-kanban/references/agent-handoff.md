# Delegated task handoff

Include this block alongside the actual implementation scope. Replace every placeholder. The parent must already have created the card.

```text
Agent Kanban is active for this task.
Skill: <absolute installed SKILL.md>
CLI: <absolute installed scripts/kanban.sh>
State directory: <absolute private state directory>
Card: <task ID>, last observed revision <N>
Actor: <runner · model · actual worker identity>
Reviewer: <actual lead identity>
Owned scope: <specific files/outcome; avoid conflicting edits>
Acceptance criteria: <observable requirements>

Read the card; claim it atomically before starting. Use your actor identity.
If claim fails, stop work on this card and report the conflict to the lead.
Keep the card current at milestones and blockers, then move to in_review with
evidence and the named reviewer before sending your final result. Do not mark
your implementation done before lead review. On interruption, record the last
verified state; the lead reconciles the card. Do not start other cards or agents
just because they appear on the board. Use show + expected revision for updates.
```

Commands (set variables to the provided absolute paths/identity):

```sh
export AGENT_KANBAN_STATE="<state directory>"
export AGENT_KANBAN_ACTOR="<actual agent identity>"
KANBAN_CLI="<absolute scripts/kanban.sh>"
sh "$KANBAN_CLI" doctor
sh "$KANBAN_CLI" show task-01
sh "$KANBAN_CLI" claim task-01 --note "Beginning assigned work"
sh "$KANBAN_CLI" show task-01
# Substitute the revision just read; do not assume these numbers on an existing card.
sh "$KANBAN_CLI" note task-01 --expected-revision 2 --note "Implementation saved; focused verification started"
sh "$KANBAN_CLI" move task-01 --expected-revision 3 --status in_review --reviewer "<lead identity>" --evidence "<test command, result, report path and limitations>" --note "Ready for review"
```

Reviewer: inspect the diff and evidence against the card criteria, then `show`
and `move --status done --expected-revision N --evidence "<review findings>"`.
Return corrections to backlog with the intended assignee and an actionable note.
For a blocker, use `move --status blocked --blocker "<cause and resolving action>"`.

This protocol is cooperative. The CLI validates atomic claims, revisions,
dependencies and required evidence; it cannot independently prove that an agent
is running or that a test passed. An old update is shown as unconfirmed activity.
