---
name: do-this
description: >
  Lead replies with a short "Do this" TLDR table of the next action(s). Use
  whenever answering the user, including coding, debugging, planning, and Q&A —
  unless they asked for a walkthrough or you are interviewing them one question at a time.
---

# Do this

When the user has a next action, start with a **Do this** table. Other text is
fine after it. Do not strip explanation, code, or context.

If they have nothing to do, **omit the table entirely.** Do not invent a check,
"look at X", or recap as a fake next step.

## Shape

Always a markdown table. Never a bare sentence or a numbered list.

Ordered (default when sequence matters):

```markdown
**Do this:**

| Step | Action |
|---|---|
| 1 | <one concrete action> |
| 2 | <next action> |
```

No inherent order (independent checks or alternatives):

```markdown
**Do this:**

| Action |
|---|
| <one concrete action> |
```

Max 5 rows. Each cell is one action (a command, a file + what to change, a decision).

## Rules

- If there is a next action: first visible text is **Do this:** then the table. No preamble before it.
- If there is no next action: no table, no "Do this" heading. Just answer.
- If there is an order, column 1 is **Step** (1, 2, 3…). Do not put order only in the prose.
- Be specific: command, path, or decision. Not "consider looking at auth."
- Keep cells short. Detail goes below.
- Multi-step work: say which step you are on in the first row (`2 of 4: …`) when continuing.
- Do not drop the rest of the answer to make the TLDR the whole message.

## Exceptions

- Pure Q&A, status, or "I already did it" with no user follow-up: skip the table.
- User asked to explain / walk through and they need to do something after: table
  first, then the walkthrough. If they only need to read your answer, skip it.
- One-question-at-a-time interviews: skip the block; ask the question.
- A clarifying question they must answer: that question is the table row.
