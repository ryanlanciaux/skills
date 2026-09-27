# diagram-walkthrough

"Show me how this works" as a stepped diagram. It covers a screen as data → helpers → components, a request through a backend, a pipeline, a deployment, or a plain concept. Views build up one layer at a time. Asides overlay the ideas that aren't boxes: re-render boundaries, transactions, retries, staleness.

Built on [reladraw](https://github.com/reladraw/reladraw), where you say where things go and it works out the distances.

```text
show me how the checkout screen works
walk me through what happens on POST /orders, with an overlay for the transaction
explain eventual consistency with a diagram
```

One layered `.reladraw` file in, per-view SVGs and an HTML stepper out:

```sh
python3 scripts/walkthrough.py demos/screen-composition.reladraw --png --open
```

Needs Python 3.9+ and `reladraw` (`npm i -g reladraw`; npx works as a fallback). `rsvg-convert` or ImageMagick is optional, for `--png`.

Demos in `demos/`: screen composition, API request lifecycle, caching concept.
