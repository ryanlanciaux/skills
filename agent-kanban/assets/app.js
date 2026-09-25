"use strict";
const $ = (id) => document.getElementById(id);
const labels = {backlog:"Backlog", in_progress:"In progress", in_review:"In review", blocked:"Blocked", done:"Done"};
const priorityOrder = {high:0, normal:1, low:2};
const columns = new Map();
const cards = new Map();
let data, etag, selected, connectedAt, timer, returnFocus;
let completedLimit = 4;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function setText(node, value) {
  if (node.textContent !== value) node.textContent = value;
}
// Small inline line icons keep the viewer dependency-free and usable offline.
function icon(name, className = "") {
  const paths = {
    board:"M4 3h16a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1ZM3 9h18M9 9v12",
    lock:"M7 10V7a5 5 0 0 1 10 0v3M5 10h14v11H5ZM12 14v3",
    radio:"M5 5a10 10 0 0 0 0 14M19 5a10 10 0 0 1 0 14M8 8a6 6 0 0 0 0 8M16 8a6 6 0 0 1 0 8M12 11v2",
    search:"M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
    chevron:"m8 10 4 4 4-4", activity:"M2 12h4l3-8 6 16 3-8h4",
    link:"M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-2 2M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l2-2",
    close:"m6 6 12 12M6 18 18 6", high:"M5 20v-3M10 20v-7M15 20V9M20 20V4",
    check:"M22 12a10 10 0 1 1-6-9M8 11l4 4L22 4",
    alert:"M12 8v5M12 16v.1M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
    document:"M14 2H5v20h14V7ZM14 2v6h5M8 12h8M8 16h6",
    external:"M7 17 17 7M7 7h10v10"
  };
  const node = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  for (const [key,value] of Object.entries({viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":"1.5","stroke-linecap":"round","stroke-linejoin":"round","aria-hidden":"true",focusable:"false",class:`icon ${className}`})) node.setAttribute(key,value);
  const path = document.createElementNS(node.namespaceURI,"path");
  path.setAttribute("d", paths[name]);
  node.append(path);
  return node;
}
function age(date, compact = false) {
  const parsed = Date.parse(date);
  if (!Number.isFinite(parsed)) return "Unknown";
  const minutes = Math.max(0, Math.floor((Date.now() - parsed) / 60000));
  const value = minutes < 60 ? `${minutes}m` : minutes < 1440 ? `${Math.floor(minutes/60)}h` : `${Math.floor(minutes/1440)}d`;
  return minutes < 1 ? (compact ? "Now" : "just now") : value + (compact ? "" : " ago");
}
function timestamp(date, compact = false) {
  const node = el("time", "", age(date, compact));
  if (Number.isFinite(Date.parse(date))) {
    node.dateTime = date;
    node.title = new Date(date).toLocaleString();
  }
  node.dataset.relative = compact ? "compact" : "full";
  return node;
}
function avatar(name) {
  const initials = (name || "?").trim().split(/\s+/).slice(0,2).map(s => s[0]).join("").toUpperCase();
  const node = el("span", "avatar", initials);
  node.setAttribute("aria-hidden", "true");
  return node;
}
function eventNode(event) {
  const node = el("div", "event");
  const content = el("div", "event-content");
  const header = el("div", "event-header");
  const time = timestamp(event.at);
  time.removeAttribute("data-relative");
  time.textContent = Number.isFinite(Date.parse(event.at)) ? new Date(event.at).toLocaleString() : "Unknown time";
  header.append(el("span", "event-author", `${event.actor}${event.task_id ? ` · ${event.task_id}` : ""}`), time);
  content.append(header, el("p", "", event.message));
  node.append(avatar(event.actor), content);
  return node;
}
// Reconcile stable nodes: unchanged links/cards keep keyboard focus during polling.
function reconcile(parent, nodes) {
  const wanted = new Set(nodes);
  for (const child of [...parent.children]) if (!wanted.has(child)) child.remove();
  nodes.forEach((node, index) => {
    if (parent.children[index] !== node) parent.insertBefore(node, parent.children[index] || null);
  });
}
function renderList(parent, items, create, key = (item,index) => `${index}:${JSON.stringify(item)}`) {
  const previous = new Map([...parent.children].map(node => [node.dataset.key,node]));
  const nodes = items.map((item,index) => {
    const id = String(key(item,index));
    const node = previous.get(id) || create(item);
    node.dataset.key = id;
    return node;
  });
  reconcile(parent,nodes);
}
function fillCard(card, task) {
  const top = el("span", "card-top");
  top.append(el("span", "task-id", task.id));
  if (task.priority === "high") {
    const priority = el("span", "priority");
    priority.append(icon("high"), "High");
    top.append(priority);
  } else if (task.status === "done") top.append(icon("check","complete-icon"));
  card.replaceChildren(top, el("span", "card-title", task.title));
  if (task.description && task.status !== "done") card.append(el("span", "card-description preview", task.description));
  if (task.depends_on?.length) {
    const context = el("span", "context");
    context.append(icon("link"),`${task.depends_on.length} ${task.depends_on.length === 1 ? "dependency" : "dependencies"}`);
    card.append(context);
  }
  if (task.blocker) {
    const context = el("span", "context blocker");
    context.append(icon("alert"),el("span","preview",task.blocker));
    card.append(context);
  }
  const owner = el("span", "owner");
  const scope = task.scope || (task.status === "backlog" ? "Planned" : "");
  owner.append(avatar(task.assignee), el("span", "owner-name", `${task.assignee || "Unassigned"}${scope ? ` · ${scope}` : ""}`), timestamp(task.updated_at,true));
  card.append(owner);
  if (task.status === "in_review" && task.reviewer) card.append(el("span", "reviewer", `Reviewing · ${task.reviewer}`));
  if (task.status === "in_progress") {
    const warning = el("span", "warning", "No update in 15+ minutes · activity unconfirmed");
    warning.dataset.staleAt = task.updated_at;
    card.append(warning);
  }
  card.setAttribute("aria-label", `${task.id}: ${task.title}`);
}
function initializeColumns() {
  $("board").replaceChildren();
  for (const [status,label] of Object.entries(labels)) {
    const column = el("section",`column ${status}`);
    column.setAttribute("aria-label",label);
    const header = el("div","column-header");
    const count = el("span","count");
    const list = el("div","cards");
    const empty = el("p","empty");
    header.append(el("span","dot"),el("h2","",label),count);
    column.append(header,list);
    const more = el("button","more-completed");
    more.type = "button";
    more.addEventListener("click",() => {
      const firstNew = columns.get("done").group[completedLimit]?.id;
      completedLimit = Infinity;
      render();
      cards.get(firstNew)?.node.focus({preventScroll:true});
      cards.get(firstNew)?.node.scrollIntoView({block:"nearest",inline:"nearest"});
    });
    columns.set(status,{column,count,list,empty,more});
    $("board").append(column);
  }
}
function render() {
  if (!data) return;
  const {board,tasks,events} = data;
  const active = document.activeElement;
  const pageScroll = {left:window.scrollX,top:window.scrollY};
  const boardScroll = $("board").scrollLeft;
  const columnScroll = new Map([...columns].map(([status,column]) => [status,column.list.scrollTop]));
  const activityScroll = $("activity").scrollTop;
  document.title = `${board.title} · Agent Kanban`;
  setText($("title"),board.title);
  setText($("goal"),board.goal || "");
  const done = tasks.filter(t => t.status === "done").length;
  setText($("completion-label"),`${done} / ${tasks.length}`);
  $("completion-label").setAttribute("aria-label",`${done} of ${tasks.length} tasks done`);
  setText($("completion-percent"),`${tasks.length ? Math.round(done / tasks.length * 100) : 0}% complete`);
  $("progress").max = tasks.length || 1;
  $("progress").value = done;
  $("summary").className = `summary ${board.mode}`;
  setText($("summary-label"),board.mode === "paused" ? "Paused" : board.mode === "complete" ? "Complete" : "Latest update");
  setText($("summary-text"),board.summary || events[0]?.message || "No updates recorded yet.");
  $("summary-time").dateTime = board.updated_at || "";
  $("summary-time").dataset.relative = "full";
  $("summary-time").title = new Date(board.updated_at).toLocaleString();
  const currentAgent = $("agent").value;
  // Retain the selected agent even if that agent's last task disappears.
  const owners = [...new Set([...tasks.map(t => t.assignee),currentAgent].filter(Boolean))].sort();
  if (JSON.stringify([...$("agent").options].slice(1).map(o => o.value)) !== JSON.stringify(owners)) {
    $("agent").replaceChildren(new Option("All agents",""),...owners.map(o => new Option(o,o)));
    $("agent").value = currentAgent;
  }
  const query = $("search").value.toLowerCase().trim();
  const visible = tasks.filter(t => (!currentAgent || t.assignee === currentAgent) &&
    [t.id,t.title,t.description,t.assignee,t.reviewer,t.scope,t.blocker,...(t.criteria || []),...(t.depends_on || [])].join(" ").toLowerCase().includes(query));
  setText($("showing"),query || currentAgent ? `${visible.length} of ${tasks.length} tasks` : `${tasks.length} tasks`);
  if (!columns.size) initializeColumns();
  for (const [status,column] of columns) {
    const group = visible.filter(t => t.status === status).sort((a,b) => ((priorityOrder[a.priority] ?? 1) - (priorityOrder[b.priority] ?? 1)) || a.id.localeCompare(b.id));
    column.group = group;
    setText(column.count,String(group.length));
    const shown = status === "done" ? group.slice(0,completedLimit) : group;
    const nodes = shown.map(task => {
      let cached = cards.get(task.id);
      if (!cached) {
        const node = el("button","card");
        node.type = "button";
        node.dataset.taskId = task.id;
        node.addEventListener("click",() => openDetail(task.id));
        cached = {node};
        cards.set(task.id,cached);
      }
      const signature = JSON.stringify(task);
      if (cached.signature !== signature) {
        fillCard(cached.node,task);
        cached.signature = signature;
      }
      cached.node.setAttribute("aria-current",String(selected === task.id));
      return cached.node;
    });
    if (!group.length) {
      setText(column.empty,query || currentAgent ? "No matching tasks" : "No tasks here");
      nodes.push(column.empty);
    }
    if (shown.length < group.length) {
      setText(column.more,`View ${group.length - shown.length} more completed`);
      nodes.push(column.more);
    }
    reconcile(column.list,nodes);
    column.list.scrollTop = columnScroll.get(status) || 0;
  }
  for (const id of cards.keys()) if (!tasks.some(t => t.id === id)) cards.delete(id);
  renderList($("activity"),events,eventNode,e => e.seq);
  $("activity").scrollTop = activityScroll;
  $("activity").setAttribute("aria-label",`Recent activity, latest ${data.history_limit} events at most`);
  if (active?.isConnected && active !== document.activeElement && !$("detail").open) active.focus({preventScroll:true});
  updateTimes();
  $("board").scrollLeft = boardScroll;
  window.scrollTo(pageScroll);
}
function evidenceNode(value) {
  // Only an explicit HTTP(S) reference supplies a browser-resolvable target.
  // File paths and narrative evidence remain plain text; never invent a route.
  const text = String(value);
  let url;
  try { const parsed = new URL(text); if (/^https?:$/.test(parsed.protocol)) url = parsed.href; } catch { /* Plain reference. */ }
  const node = el(url ? "a" : "div","evidence");
  const content = el("span","evidence-text",text);
  if (url) { node.href = url; node.target = "_blank"; node.rel = "noopener noreferrer"; }
  else content.append(el("span","evidence-note","Recorded reference"));
  node.append(icon("document"),content);
  if (url) node.append(icon("external"));
  return node;
}
function renderDetail() {
  const task = data.tasks.find(t => t.id === selected);
  const focused = document.activeElement;
  const scrollTop = $("detail-body").scrollTop;
  setText($("detail-workspace"),data.board.title);
  $("detail-workspace").title = data.board.title;
  setText($("detail-id"),selected);
  $("detail-meta").hidden = !task;
  $("detail-sections").hidden = !task;
  $("detail-properties").hidden = !task;
  if (!task) {
    setText($("detail-title"),"Task unavailable");
    setText($("detail-description"),`${selected} is no longer available in this workspace. Close this view to inspect another task.`);
    if (focused !== $("close-detail")) $("close-detail").focus({preventScroll:true});
    return;
  }
  setText($("detail-title"),task.title);
  setText($("detail-description"),task.description || "No additional description.");
  setText($("detail-status"),labels[task.status] || task.status);
  $("detail-status").className = `status-badge ${task.status}`;
  setText($("detail-revision"),`Revision ${task.revision}`);
  $("blocker-section").hidden = !task.blocker;
  setText($("detail-blocker"),task.blocker || "");
  const criteria = task.criteria || [], evidence = task.evidence || [];
  const events = data.events.filter(e => e.task_id === task.id);
  renderList($("detail-criteria"),criteria,item => {
    const node = el("li"); node.append(el("span","criterion-text",item)); return node;
  });
  renderList($("detail-evidence"),evidence,evidenceNode);
  renderList($("detail-activity"),events,eventNode,e => e.seq);
  $("criteria-empty").hidden = !!criteria.length;
  $("evidence-empty").hidden = !!evidence.length;
  $("activity-empty").hidden = !!events.length;
  const properties = [
    ["Priority",task.priority ? task.priority[0].toUpperCase() + task.priority.slice(1) : "Not recorded"],
    ["Agent",task.assignee || "Unassigned"], ["Scope",task.scope || "Not recorded"],
    ["Reviewer",task.reviewer || "None recorded"],
    ["Dependencies",(task.depends_on || []).map(id => `${id} — ${labels[data.tasks.find(t => t.id === id)?.status] || "Unavailable"}`).join("\n") || "None recorded"],
    ["Last updated",Number.isFinite(Date.parse(task.updated_at)) ? `${age(task.updated_at)}\n${new Date(task.updated_at).toLocaleString()}` : "Not recorded"]
  ];
  renderList($("detail-properties"),properties,([label,value]) => {
    const node = el("div","property");
    node.append(el("dt","",label),el("dd",label === "Priority" && task.priority === "high" ? "priority" : "",value));
    return node;
  });
  $("detail-body").scrollTop = scrollTop;
  if (focused && !focused.isConnected) $("close-detail").focus({preventScroll:true});
}
function openDetail(id) {
  selected = id;
  returnFocus = document.activeElement;
  renderDetail();
  cards.get(id)?.node.setAttribute("aria-current","true");
  document.body.classList.add("modal-open");
  $("detail").showModal();
  $("detail-body").scrollTop = 0;
}
function updateTimes() {
  for (const node of document.querySelectorAll("time[data-relative]")) setText(node,age(node.dateTime,node.dataset.relative === "compact"));
  for (const node of document.querySelectorAll("[data-stale-at]")) node.hidden = Date.now() - Date.parse(node.dataset.staleAt) <= 15 * 60000;
  setText($("updated"),connectedAt ? `Last synced ${age(connectedAt.toISOString())}` : "Not yet synced");
  if ($("detail").open) renderDetail();
}
async function refresh() {
  clearTimeout(timer);
  try {
    const response = await fetch("/api/board",{headers:etag ? {"If-None-Match":etag} : {},signal:AbortSignal.timeout(5000)});
    const changed = response.status !== 304;
    if (changed) {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const next = await response.json();
      if (!next.board || !Array.isArray(next.tasks) || !Array.isArray(next.events)) throw new Error("Invalid board");
      data = next;
      etag = response.headers.get("ETag");
    }
    connectedAt = new Date();
    setText($("connection"),"Live · refreshes every 2s");
    $("connection").className = "connection live";
    if (changed) render();
    else updateTimes();
  } catch {
    setText($("connection"),`Disconnected · ${connectedAt ? "showing last received board" : "retrying"}`);
    $("connection").className = "connection offline";
    if (!data) {
      setText($("title"),"Board unavailable");
      setText($("summary-text"),"Cannot reach the board. Retrying automatically…");
      $("board").replaceChildren(el("p","empty","Cannot reach the board. Retrying automatically…"));
    }
    updateTimes();
  } finally { timer = setTimeout(refresh,2000); }
}
for (const node of document.querySelectorAll("[data-icon]")) node.append(icon(node.dataset.icon));
$("search").addEventListener("input",render);
$("agent").addEventListener("change",render);
$("activity-toggle").addEventListener("click",() => {
  $("activity").hidden = !$("activity").hidden;
  $("activity-toggle").setAttribute("aria-expanded",String(!$("activity").hidden));
});
$("close-detail").addEventListener("click",() => $("detail").close());
$("detail").addEventListener("close",() => {
  document.body.classList.remove("modal-open");
  const target = cards.get(selected)?.node;
  target?.setAttribute("aria-current","false");
  selected = undefined;
  (target?.isConnected ? target : returnFocus?.isConnected ? returnFocus : $("search")).focus({preventScroll:true});
});
// Native dialog supplies modal semantics and Escape; explicitly wrap Tab within it.
$("detail").addEventListener("keydown",event => {
  if (event.key !== "Tab") return;
  const focusable = [...$("detail").querySelectorAll('button,a[href],[tabindex="0"]')].filter(n => n.getClientRects().length);
  const first = focusable[0], last = focusable.at(-1);
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
});
let backdropPress = false;
function outsideDialog(event) {
  const r = $("detail").getBoundingClientRect();
  return event.target === $("detail") && (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom);
}
$("detail").addEventListener("pointerdown",event => { backdropPress = outsideDialog(event); });
$("detail").addEventListener("click",event => { if (backdropPress && outsideDialog(event)) $("detail").close(); backdropPress = false; });
window.addEventListener("online",() => { setText($("connection"),"Reconnecting…"); });
refresh();
