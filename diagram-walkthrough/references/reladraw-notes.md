# reladraw notes (0.8.x)

The subset a walkthrough needs, plus the traps found building the demos. Full reference: [SYNTAX.md](https://github.com/reladraw/reladraw/blob/main/SYNTAX.md). If the upstream `reladraw` skill is installed, its `reference/syntax.md` is the same document.

## Shape

One statement per line. `//` comments. `#` starts a hex color, not a comment. After the head, attributes and placements can come in any order.

```
node <name> ["text" [(size: small, wrap: 24, color: muted, align: left, at: top-center)]] [placements] [attributes]
edge <a> -> <b> ["text"] [from: side] [to: side] [between x and y] [below|above|left of|right of z] [style: s] [line: (path: square, pattern: dashed)]
style <name> <attributes>
default node|leaf|container|edge <attributes>
diagram theme: light
```

- ` / ` (spaces on both sides) is a line break. `a/b` stays literal.
- A dotted name means containment: `node api.auth` sits inside `api`, and the parent must be declared first. Children stack top to bottom unless they're placed.
- `contents: (widths: match)` on a container makes its children equal width, so vertical edges between them run straight.
- Placement words: `above`, `below`, `left of`, `right of`, the four diagonals, `level with`, `top level with`, `bottom level with`, `left level with`, `right level with`. Targets can be several things joined with `and`.
- Parts: `inside X top-right`, `on X top-left`, `outside X bottom`, `right of X text`.
- Node attributes: `style`, `fill`, `border`, `shape` (`rectangle`, `document`, `circle`, `none`), `icon`, `badge` (`disk`, `desktop`, `laptop`, `package`, `cubes`, `cube`, `database`), `deck`, `gap`, `overlap: allow`, `contents`, `url: "…"`. An unknown attribute is an error.
- Themes: dark (the default), light, print, nord, dracula, and the solarized, gruvbox, catppuccin and high-contrast families.

## Pitfalls (each one hit while building the demos)

1. **`gap: wide` written as a node attribute applies to every relationship the node is in**, including placements other nodes make against it, and the larger gap wins. A callout `below screen gap: tight` ended up 100px away because `screen` carried `gap: wide`. Put spacing in the placement bracket instead: `right of logic (gap: wide)`.
2. **A placement that fixes only one axis leaves the node to drift.** `left of queue` on its own sent a node to the canvas edge. Pair it with `level with …`, or use `below …` / `right of …`, which center on the other axis.
3. **Containers grow.** When an aside or later view adds children to a leaf, it gets bigger and can collide with its neighbors. The error names the pair. Place one explicitly against the other (`below db`).
4. **Edges whose ends face away from each other** (for example `from: right` to a target's `top` when the target is to the lower right) loop over the whole row. Choose sides that face each other, or move the target.
5. **Stamps (`on`, `inside`) never make room.** They cover whatever is there, including centered labels. Use them only for small marks on corners. For words, use a child tag `right of X text`.
6. **No routing.** Nothing keeps an edge clear of unrelated nodes. Look at the PNG, then add `from:`/`to:`, `between a and b`, or `below x`.
7. **Two nodes hung off the same side of the same target** either stack as a list (if their placements are identical) or produce an overlap error. Chain them instead: `b below a`, not `a below x` plus `b below x` with extra words.
8. **Bare text without `(wrap: n)`** draws as one line across everything. Always wrap callouts.
9. **Nothing can be redeclared.** A node, style or `diagram` is stated once. Views accumulate statements; they never edit earlier ones.
10. **Colors are never quoted.** `url:` values are always quoted.
