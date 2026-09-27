# Lenses

A lens decides three things: which way the diagram reads, what to trace in the code, and which views and asides usually earn their place. Pick one per walkthrough. When a question spans two lenses, make two walkthroughs or make the second lens an aside.

Names below are generic. Use the codebase's own names every time.

## Screen / UI composition

"Show me how this screen works."

- **Reads** left → right: outside sources → data layer → hooks/helpers/selectors → the screen as a container holding its component tree. Bands are containers styled as quiet frames. Components nest by dotted name.
- **Trace**: start at the route or screen file. List the child components it renders, one or two levels deep; stop where components become generic design-system pieces. For each prop that carries data, follow it back through hooks, stores or selectors, then formatters, then the fetch or client call, then the endpoint or storage key. Note where state lives (local, context, global store, URL, cache).
- **Views**: layers → data flow (numbered steps on first load) → interactions (what a click or input triggers).
- **Asides**: re-render boundary (tag what re-renders when X changes), loading/empty/error states, where would I add…, server vs client boundary, what is memoized or cached.
- Repeated children (rows, cards) get `deck: "" ""` rather than three boxes.

## Request lifecycle / API backend

"Walk me through what happens on POST /x." "How is the API structured?"

- **Reads** left → right along the request: client → edge (gateway, CDN, load balancer) → service (middleware chain stacked inside it, then the handler) → domain/services → stores and external providers on the right. The async side goes in a column to the right of, or under, the store that feeds it.
- **Trace**: route registration → middleware order (auth, validation, rate limit, tenancy) → handler → the service calls it makes → queries, transactions, outbound HTTP → events, jobs or queues published. Find the consumers of those queues too. Framework-agnostic: look for the router table, DI container, or handler naming convention the project actually uses.
- **Views**: sync path → async side → the read path, if it differs.
- **Asides**: transaction boundary, retries and idempotency, auth and permissions (tag each hop with what it checks), failure modes (timeout here means…), where data is validated vs trusted.
- For an unfamiliar backend (an odd framework, generated code, several services), a first **service map** view is fine: one box per deployable with protocols on the edges. Then zoom into one service per later view.

## Event / data pipeline

- **Reads** left → right, or top → bottom when stages are many: sources → ingest → transform stages → sinks. Queues and topics are nodes, not edges, because they have state.
- **Trace**: producers (publish/emit/send calls), topic and queue names, consumers, schedulers and cron entries, schemas.
- **Asides**: ordering guarantees, at-least-once and dedupe, backpressure, dead-letter path, replay.

## Deployment / infrastructure

- **Reads** outside-in: users → edge → network boundaries (VPC, cluster, region) as containers → workloads → managed services. `deck:` for replicas.
- **Trace**: IaC, compose, k8s manifests, CI deploy steps, env var names (never their values).
- **Asides**: blast radius of X failing, where secrets come from, scaling unit, what's single-region.

## Module / package map

"How is this repo organized?"

- **Reads** top → bottom by dependency: apps on top, shared libraries in the middle, leaf utilities at the bottom. Edges point along import direction.
- **Trace**: workspace config, package manifests, top-level imports between packages. Aggregate: an edge means "imports something from", not every import.
- **Asides**: a dependency that points the wrong way (a cycle, a leaf importing an app), ownership, what's public API vs internal.

## Lifecycle / state machine

- States as nodes, transitions as labeled edges. Lay out the happy path in a straight line and branch the failure states below it.
- **Trace**: enums, status columns, reducer cases, transition guards.
- **Asides**: who triggers each transition, what's persisted at each state, timeouts.

## Concept (no code)

"Explain caching / eventual consistency / OAuth."

- Use the standard shape of the idea, and say in the first caption that it's generic.
- Build from the smallest true picture outward. The overlays are the lesson: numbered sequences, what goes stale, what breaks.
- Keep to what's widely accepted. Don't dress up an opinion as architecture.

## Change / PR impact

"Show me what this branch changes."

- Base view: the affected slice of the system as it was. Next view: tag changed nodes (`● changed`) and add new nodes in the proposed style. Aside: what callers must now do differently.
- **Trace**: `git diff --stat` against the base branch, then the touched symbols and their callers.
