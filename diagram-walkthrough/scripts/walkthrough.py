#!/usr/bin/env python3
"""Render a layered .reladraw walkthrough into per-view SVGs and one HTML stepper.

A walkthrough is one ordinary .reladraw file with marker comments:

    // @title  Checkout screen
    <preamble: diagram/style/default lines, shared by every view>
    // @view   Overview :: The screen is a tree of components fed by two hooks.
    <statements>
    // @view   Data flow :: Numbered path from API to pixels.
    <statements added on top of everything before>
    // @aside  Why memoize? :: Shown in this view only, then dropped.
    <statements>

`@view` blocks accumulate. An `@aside` block is added to the views before it for
one view only. A file with no markers renders as one view. Excluded lines are
blanked rather than removed, so reladraw's line numbers always match the source.

Stdlib only. Needs `reladraw` on PATH, or npx.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

RELADRAW_VERSION = "0.8.0"
MARKER = re.compile(r"^\s*//\s*@(title|view|aside)\b\s*(.*)$")


def parse(source: str):
    """Return (title, preamble_line_idxs, blocks). Each block: kind, title, caption, line idxs."""
    lines = source.splitlines()
    title = None
    preamble: list[int] = []
    blocks: list[dict] = []
    for i, line in enumerate(lines):
        m = MARKER.match(line)
        if m:
            kind, rest = m.group(1), m.group(2).strip()
            if kind == "title":
                title = rest
                continue
            name, _, caption = rest.partition("::")
            blocks.append({"kind": kind, "title": name.strip() or f"View {len(blocks) + 1}",
                           "caption": caption.strip(), "lines": []})
            continue
        (blocks[-1]["lines"] if blocks else preamble).append(i)
    return lines, title, preamble, blocks


def compose(lines, preamble, blocks, upto: int) -> str:
    keep = set(preamble)
    for j, b in enumerate(blocks[: upto + 1]):
        if b["kind"] == "view" or j == upto:
            keep.update(b["lines"])
    return "\n".join(l if i in keep else "" for i, l in enumerate(lines)) + "\n"


def reladraw_cmd() -> list[str]:
    if shutil.which("reladraw"):
        return ["reladraw"]
    if shutil.which("npx"):
        return ["npx", "-y", f"reladraw@{RELADRAW_VERSION}"]
    sys.exit("reladraw not found. Install with `npm install -g reladraw` (needs Node), or put npx on PATH.")


def to_png(svg: Path) -> Path | None:
    png = svg.with_suffix(".png")
    for cmd in (["rsvg-convert", "-z", "1.5", "-o", str(png), str(svg)],
                ["magick", "-density", "144", str(svg), str(png)]):
        if shutil.which(cmd[0]) and subprocess.run(cmd, capture_output=True).returncode == 0:
            return png
    return None


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "view"


def scope_ids(svg: str, prefix: str) -> str:
    """Inline SVGs share one document id space; prefix ids so markers never collide."""
    svg = re.sub(r'\bid="([^"]+)"', rf'id="{prefix}-\1"', svg)
    svg = re.sub(r"url\(#([^)]+)\)", rf"url(#{prefix}-\1)", svg)
    return re.sub(r'href="#([^"]+)"', rf'href="#{prefix}-\1"', svg)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="layered .reladraw file")
    ap.add_argument("-o", "--out", type=Path, help="output dir (default: <source stem>.walkthrough/ beside it)")
    ap.add_argument("--theme", help="reladraw theme, overriding the file's own")
    ap.add_argument("--png", action="store_true", help="also rasterize each view to PNG (to look at the result)")
    ap.add_argument("--open", action="store_true", help="open the HTML stepper in a browser")
    args = ap.parse_args()

    src = args.source.resolve()
    lines, title, preamble, blocks = parse(src.read_text())
    if not blocks:
        blocks = [{"kind": "view", "title": title or src.stem, "caption": "", "lines": preamble}]
        preamble = []
    out = (args.out or src.with_name(src.stem + ".walkthrough")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("[0-9][0-9]-*.*"):
        stale.unlink()

    cmd = reladraw_cmd()
    views, failed = [], False
    for k, b in enumerate(blocks):
        stem = f"{k + 1:02d}-{slug(b['title'])}"
        composed = out / f"{stem}.reladraw"
        composed.write_text(compose(lines, preamble, blocks, k))
        svg = out / f"{stem}.svg"
        run = cmd + [str(composed), "-o", str(svg)] + (["--theme", args.theme] if args.theme else [])
        r = subprocess.run(run, capture_output=True, text=True)
        if r.returncode != 0:
            # Line numbers are preserved, so point the error at the file the author edits.
            msg = (r.stderr or r.stdout).strip().replace(str(composed), str(src))
            print(f"✗ view {k + 1} \"{b['title']}\" ({b['kind']}):\n{msg}", file=sys.stderr)
            failed = True
            continue
        png = to_png(svg) if args.png else None
        views.append({**b, "n": k + 1, "svg": svg, "png": png})
        print(f"✓ view {k + 1} {b['kind']:5} {svg}" + (f"\n        png   {png}" if png else ""))
    if failed:
        return 1

    page = out / "index.html"
    page.write_text(render_html(title or src.stem, views, src.name))
    print(f"→ {page}")
    if args.open:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        if shutil.which(opener):
            subprocess.Popen([opener, str(page)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 0


def render_html(title: str, views: list[dict], source_name: str) -> str:
    panes, tabs = [], []
    for v in views:
        body = v["svg"].read_text()
        body = scope_ids(body[body.index("<svg"):], f"v{v['n']}")
        kind = "aside" if v["kind"] == "aside" else "view"
        tabs.append(f'<button class="tab {kind}" data-i="{v["n"] - 1}"><span class="n">{v["n"]}</span>'
                    f'{html.escape(v["title"])}</button>')
        panes.append(f'<figure class="pane" data-i="{v["n"] - 1}" hidden>'
                     f'<div class="canvas">{body}</div></figure>')
    meta = json.dumps([{"title": v["title"], "caption": v["caption"], "kind": v["kind"]} for v in views])
    return TEMPLATE.format(title=html.escape(title), source=html.escape(source_name),
                           tabs="\n".join(tabs), panes="\n".join(panes), meta=meta)


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --bg:#0d0d0f; --panel:#16161a; --line:#2a2a31; --text:#e6e6e6; --muted:#9a9aa3; --accent:#8ab4f8; --aside:#e0b35a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font:15px/1.5 system-ui, sans-serif; display:grid; grid-template-rows:auto auto 1fr auto; min-height:100vh; }}
header {{ display:flex; gap:12px; align-items:baseline; padding:14px 20px; border-bottom:1px solid var(--line); }}
header h1 {{ font-size:16px; margin:0; font-weight:600; }}
header small {{ color:var(--muted); font-family:ui-monospace, monospace; }}
nav {{ display:flex; flex-wrap:wrap; gap:6px; padding:10px 20px; border-bottom:1px solid var(--line); }}
.tab {{ all:unset; cursor:pointer; padding:5px 10px; border-radius:6px; color:var(--muted); border:1px solid transparent; }}
.tab .n {{ font-family:ui-monospace, monospace; margin-right:6px; opacity:.7; }}
.tab.aside {{ font-style:italic; }}
.tab.aside .n::after {{ content:"◇"; margin-left:3px; color:var(--aside); }}
.tab[aria-current] {{ color:var(--text); border-color:var(--line); background:var(--panel); }}
.tab:focus-visible {{ outline:2px solid var(--accent); }}
main {{ overflow:auto; padding:20px; display:grid; place-items:start center; }}
.canvas {{ cursor:zoom-in; }}
.canvas svg {{ max-width:100%; height:auto; display:block; border-radius:8px; }}
body.actual .canvas {{ cursor:zoom-out; }}
body.actual .canvas svg {{ max-width:none; }}
footer {{ display:flex; gap:16px; align-items:center; padding:12px 20px; border-top:1px solid var(--line); background:var(--panel); }}
footer p {{ margin:0; flex:1; max-width:90ch; }}
footer .kind {{ font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }}
footer .kind.aside {{ color:var(--aside); }}
footer button {{ background:none; color:var(--text); border:1px solid var(--line); border-radius:6px; padding:6px 12px; cursor:pointer; font:inherit; }}
footer button:disabled {{ opacity:.35; cursor:default; }}
</style></head>
<body>
<header><h1>{title}</h1><small>{source} · ←/→ step · click diagram to zoom</small></header>
<nav>{tabs}</nav>
<main>{panes}</main>
<footer>
  <button id="prev" aria-label="Previous view">←</button>
  <span class="kind" id="kind"></span>
  <p id="caption"></p>
  <button id="next" aria-label="Next view">→</button>
</footer>
<script>
const META = {meta};
const tabs = [...document.querySelectorAll('.tab')], panes = [...document.querySelectorAll('.pane')];
const $ = id => document.getElementById(id);
let cur = 0;
function show(i) {{
  cur = Math.max(0, Math.min(META.length - 1, i));
  panes.forEach((p, j) => p.hidden = j !== cur);
  tabs.forEach((t, j) => j === cur ? t.setAttribute('aria-current', 'step') : t.removeAttribute('aria-current'));
  const m = META[cur];
  $('caption').textContent = m.caption || m.title;
  $('kind').textContent = m.kind === 'aside' ? 'aside' : `step ${{cur + 1}}/${{META.length}}`;
  $('kind').className = 'kind ' + m.kind;
  $('prev').disabled = cur === 0; $('next').disabled = cur === META.length - 1;
  try {{ history.replaceState(null, '', '#' + (cur + 1)); }} catch (e) {{}}
}}
tabs.forEach((t, j) => t.onclick = () => show(j));
document.querySelectorAll('.canvas').forEach(c => c.onclick = () => document.body.classList.toggle('actual'));
$('prev').onclick = () => show(cur - 1); $('next').onclick = () => show(cur + 1);
addEventListener('keydown', e => {{
  if (e.key === 'ArrowRight' || e.key === 'j') show(cur + 1);
  if (e.key === 'ArrowLeft' || e.key === 'k') show(cur - 1);
}});
show((parseInt(location.hash.slice(1)) || 1) - 1);
</script>
</body></html>
"""

if __name__ == "__main__":
    sys.exit(main())
