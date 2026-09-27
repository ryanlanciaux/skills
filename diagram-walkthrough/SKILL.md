---
name: diagram-walkthrough
description: "Explain how something works with a stepped reladraw diagram: a screen as layers of data → helpers/hooks → components, a backend request from client to database, an event pipeline, a deployment, a module map, or an abstract concept. Use when the user asks to show, walk through, visualize or diagram how a screen, feature, flow, service, architecture or idea works (\"show me how this screen works\", \"walk me through the API\", \"draw how X fits together\"), or asks for overlays or annotations that explain things the boxes alone don't show. Produces a multi-view HTML stepper from one .reladraw file. Not for data charts."
---

# Diagram walkthrough

Answer "how does this work?" with a picture you build up one view at a time. Each view adds a layer, and asides overlay the concepts that aren't boxes: re-render boundaries, transactions, retries, staleness, ownership.

The tool is [reladraw](https://github.com/reladraw/reladraw): you say where things go (`right of api`, `below cache`) and it works out the distances. It never picks a layout for you, so re-reading your own source tells you where everything landed. On top of that, `scripts/walkthrough.py` splits one layered file into views and renders an HTML stepper.

## Setup

`reladraw --help`. If it's missing, the script falls back to `npx -y reladraw@0.8.0`. If there's no Node either, tell the user to run `npm install -g reladraw`. `rsvg-convert` or ImageMagick is optional; with one of them `--png` lets you look at your own output.

## Loop

1. **Pin the question.** Name the subject and the lens: screen, request, pipeline, deployment, modules, lifecycle, concept or change. [references/lenses.md](references/lenses.md) gives each lens its layout direction, what to trace in code, and its usual views and asides. If the request is broad ("show me the architecture"), pick the lens that answers the most useful question, say which one you chose, and offer the others at the end. Don't stop to ask.
2. **Trace the real thing.** For code, read it: follow imports, calls, props, routes, queries and queue names from the entry point outward. Every node must map to a real file, symbol, service or table, using the codebase's own names. Put a qualifier in a dim second line (`"useOrders / [dim]src/orders/hooks.ts[/dim]"`) when the location helps. Don't invent boxes to make a tidier picture. If a layer doesn't exist, the diagram should show that. For a concept, use the standard shape of the idea and say it's generic.
3. **Write one layered file** (format below). Keep it in the scratchpad or a temp dir unless the user asks to keep it in the repo. Base view: about 15 nodes at most. Split rather than cram.
4. **Render and look** (`SKILL_DIR` is the directory holding this file):
   ```
   python3 "$SKILL_DIR/scripts/walkthrough.py" walk.reladraw --png [-o outdir] [--theme light]
   ```
   Errors name the line in *your* file (excluded blocks are blanked, not removed, so line numbers hold). Read every PNG and go through the checklist below. Fix, re-render, repeat. A file that renders is only a file whose arrangement is fully stated. It is not yet a readable picture.
5. **Present.** Re-run with `--open`, or give the path to `index.html`. In chat, give one line per view saying what it shows, then the caveats: what you left out and anything inferred rather than read. Offer to go deeper on any box, which means a new walkthrough scoped to that box.

## The layered file

```
// @title  How checkout works
<preamble: style / default / diagram lines, shared by every view>
// @view   Layers :: caption shown under the diagram
<statements>
// @view   Data flow :: added on top of every view before it
<statements>
// @aside  Why memoize? :: overlaid on the views so far, for this view only
<statements>
```

- `@view` blocks **accumulate**. Use them for structure: the base, then flows, then the async side.
- `@aside` blocks show once and are dropped. Use them for explanations that would clutter later views. An aside may refer to anything declared before it. Later blocks must not refer to an aside's nodes.
- The caption carries the explanation, one to three sentences. The diagram shows *where*; the caption says *why*.
- No markers means a single-view render. That's fine for "just draw it".

## Overlays

[references/overlays.md](references/overlays.md) has the vocabulary and a palette to copy into the preamble:

- **step markers**: numbers stamped on a corner of each node, in order
- **tags**: a short colored note beside a node's text, which grows the box to make room
- **callouts**: a wrapped note in the margin, with a dashed leader edge to its subject
- **alternate paths**: extra edges in a distinct line style (writes, retries, async)
- **proposed/ghost nodes**, **multiples** (`deck:`), and **region notes** that sit beside several nodes at once

Overlays should explain, not restructure. If an aside needs new boxes in the middle of the layout, it's really another `@view`.

## Check every PNG

- Labels readable: no text covered by a stamp, edge or tag.
- No edge runs through an unrelated box. If one does, add `from:`/`to:`, `between a and b`, or `below x`, or move the node.
- Callouts sit next to their subject and have a leader when that isn't obvious.
- Nothing has drifted to the canvas edge (see pitfalls).
- Views read in order: each adds one idea, and its caption matches what's new.

[references/reladraw-notes.md](references/reladraw-notes.md) has the syntax you need and the pitfalls found while building the demos. Read it before writing your first file in a session.

## Demos

`demos/` has three complete walkthroughs to copy from. All are fictional and generic:

- `screen-composition.reladraw`: a UI screen as layers. Outside → data → hooks and helpers → a component tree. Numbered data flow, a re-render boundary aside, and a "where would I add…" aside.
- `api-request-lifecycle.reladraw`: a backend POST from client through gateway, middleware, handler and domain to the database, plus an outbox/queue/worker side. Asides for the transaction boundary and for retries/idempotency.
- `caching-concept.reladraw`: an idea with no code behind it. Caching tiers, a full miss with fills on the way back, and a write that invalidates some tiers and leaves others stale.

`python3 scripts/walkthrough.py demos/<name>.reladraw --open` renders one.
