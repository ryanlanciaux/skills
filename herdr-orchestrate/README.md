# Herdr orchestrate

One skill; named profiles select agents, role routing and resource limits.

## Load it in Pi

For one session:

```sh
pi --skill ~/projects/skills/herdr-orchestrate/SKILL.md
```

Or make it discoverable in future sessions with a symlink (not created automatically):

```sh
mkdir -p ~/.agents/skills
ln -s ~/projects/skills/herdr-orchestrate ~/.agents/skills/herdr-orchestrate
```

Then invoke:

```text
/skill:herdr-orchestrate balanced Implement the projects dashboard
/skill:herdr-orchestrate difficult Fix the restore/concurrency bugs
/skill:herdr-orchestrate grok Build the screen-first workspace
```

With an established task, `/skill:herdr-orchestrate difficult` is sufficient. Natural-language requests such as “run this through Herdr tabs using difficult” select the same configuration.

**Pi's native command is `/skill:herdr-orchestrate difficult`, not `/skill difficult`.** This package does not register a custom slash-command alias. `difficult` is a configurable profile, never a separate skill.

## Named configuration

Edit `profiles.json` beside the skill. No code changes or additional skill files are needed to add a profile.

| Profile | Implementation | Complex work | Review | Worker / heavy limits |
|---|---|---|---|---|
| `balanced` (default) | Cursor Grok | Pi OpenAI | Pi OpenAI | 3 / 1 |
| `difficult` | Pi OpenAI | Pi OpenAI | Pi OpenAI | 2 / 1 |
| `grok` | Cursor Grok | Cursor Grok | Cursor Grok | 3 / 1 |

Agent aliases contain a Herdr `kind` and a command **argument array**, not a task prompt. The included commands match the current user's requested non-fast Grok and OpenAI setup; model availability/authentication depend on the machine/account. Change executable/provider/model arguments as needed. Unknown profiles, aliases or unavailable commands/models must not silently fall back.

For example, add a profile under `profiles`:

```json
"my-team": {
  "description": "My preferred routing",
  "roles": {
    "implementer": "grok",
    "complex": "openai",
    "reviewer": "openai"
  },
  "maxWorkers": 4,
  "maxHeavyJobs": 1,
  "waitSeconds": 10
}
```

Then use `/skill:herdr-orchestrate my-team <task>`. Role aliases must exist under `agents`. Change `defaultProfile` to select a different default for natural-language requests without a named profile.

JSON syntax check:

```sh
python3 -m json.tool ~/projects/skills/herdr-orchestrate/profiles.json >/dev/null
```

## What this fixes

- A pasted prompt is not considered submitted until relevant work actually starts.
- The parent stays active with bounded waits and handles completion/approval promptly.
- Workers use reports and notifications—not keystrokes into the parent's draft.
- Heavy commands have explicit ownership; independent code work stays parallel.
- Stable commits are reviewed, fixed, checked and integrated before claiming delivery.
- Completion means the stated working result, not merely idle tabs or committed code.

This is a workflow skill, not a daemon or a guaranteed background wake-up service. It does not modify Herdr/Pi configuration, launch agents, create project worktrees, or install itself merely by existing on disk. The skill must be loaded and followed by the orchestrating agent.
