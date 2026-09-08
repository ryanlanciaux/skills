# herdr-orchestrate

Simple orchestration, not a DAG.

A profile maps lanes to agents. You open workers; they run that command.

```text
/skill:herdr-orchestrate difficult {prompt}
```

Cursor: `/herdr-orchestrate difficult {prompt}`

`difficult` in `profiles.json`: orchestrator Astra, simple Grok, complex/review Astra. If this pane isn't the orchestrator, start it and hand off.

Edit `profiles.json` to add agents or profiles. Extra role keys are just more lanes.
