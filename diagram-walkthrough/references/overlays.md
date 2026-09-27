# Overlays

What goes in the views and asides that explain, as opposed to the base view that only shows structure.

## Palette

Copy this into the preamble and delete the roles you don't use. Colors carry meaning through style names, so an overlay is always yellow and a write is always red. Colors are tuned for the default dark theme. For `--theme light`, lighten the fills or drop them (`fill: none`).

```
// structure
style band     fill: none  border: #33343d  text: (color: muted)
style ext      fill: none  border: #6b7280
style data     fill: #10243a  border: #3b6ea5
style logic    fill: #241d38  border: #7a5fb5
style ui       fill: #12301f  border: #3f8a5a
style store    fill: #142814  border: #486544  badge: database
style async    fill: #2a1a24  border: #a0527a
style edgeinfra  fill: #2b2412  border: #a3812f
style proposed fill: none  border: #5d6a7a  text: (color: muted)
style dim      text: (color: muted)
// overlays
style step     fill: #e0b35a  border: #e0b35a  text: (color: #111111, size: small)
style tag      shape: none  text: (color: #e0b35a, size: small)
style callout  shape: none  text: (color: #e0b35a, size: small)
style leader   line: (color: #e0b35a, pattern: dashed)
style later    line: (color: #a0527a, pattern: dashed)
style write    line: #d0605e  text: (color: #d0605e)
default edge   text: (size: small)
```

`[dim]…[/dim]` inside any text quiets part of a line: `"apiClient / [dim]auth, retries[/dim]"`.

## Vocabulary

**Step markers.** Show order. Stamp a number on a corner. Stamps overlap on purpose and never move anything:
```
node s1 "1"  on logic.hook top-left  style: step
```
Keep the numbers small and use at most about 8 in a view. Explain the sequence in the caption, or in one callout that uses the same numbers.

**Tags.** A short state label on a node: `● re-renders`, `● stale until TTL`, `● changed`. Declare the tag as a *child* beside the node's text, so the box grows to make room instead of the tag covering the label:
```
node screen.bar.rr "● re-renders"  right of screen.bar text  style: tag
```
This works on leaves too; the leaf becomes a container, which is fine. Keep tags to two or three words. Anything longer is a callout.

**Callouts.** A sentence or two in the margin. Always `(wrap: 22–34)`. Put it beside the outermost thing near the subject, not in the middle of the layout, and add a dashed leader when the subject isn't obvious:
```
node why "filter change → new key → refetch" (wrap: 26)  style: callout  right of screen (gap: wide)  level with screen.bar
edge why -> screen.bar  from: left  to: right  style: leader
```
To keep several callouts on one row: `below logic  top level with first_callout`.

**Region notes.** One note for several nodes: `right of a and c` places it against the box that bounds them all.

**Alternate paths.** Extra edges in their own style: writes (`write`), async or eventual (`later`), retries, error paths. Name the sides (`from:`/`to:`) so they don't cut through the base picture.

**Proposed / ghost nodes.** Things that don't exist yet, or were removed: `style: proposed` plus `[dim](proposed)` in the text.

**Multiples.** Several identical things (replicas, list rows, workers): `deck: "" ""` on a box.

**Emphasis without restyling.** reladraw can't restyle a node declared earlier, and a node can be declared only once. To highlight existing nodes, use a tag, a step marker, or a callout with a leader. Don't redeclare the node.

## Keep overlays from moving the base

Views are rendered separately, so anything that takes up space shifts the layout between views. Minimize that:

- Put callouts on the outside edges of the diagram (right of the rightmost band, below the bottom row, above the top row), never between bands.
- Stamps (`on`, `inside`) take no space. Tags grow their box a little. Callouts in the margin only extend the canvas.
- If an aside needs a node inside the layout, accept the shift or make it a `@view`.
