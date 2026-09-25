"use strict";
const $ = (id) => document.getElementById(id);
const labels = {backlog:"Backlog", in_progress:"In progress", in_review:"In review", blocked:"Blocked", done:"Done"};
let data, etag, selected, connectedAt, timer;
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function age(date) {
  const minutes = Math.max(0, Math.floor((Date.now() - Date.parse(date)) / 60000));
  return minutes < 1 ? "just now" : minutes < 60 ? `${minutes}m ago` : minutes < 1440 ? `${Math.floor(minutes/60)}h ago` : `${Math.floor(minutes/1440)}d ago`;
}
function eventNode(event) {
  const node = el("div", "event", `${event.actor}${event.task_id ? ` · ${event.task_id}` : ""} — ${event.message}`);
  const timestamp = el("time", "", new Date(event.at).toLocaleString());
  timestamp.dateTime = event.at;
  node.append(timestamp);
  return node;
}
function render() {
  if (!data) return;
  const {board, tasks} = data;
  document.title = `${board.title} · Agent Kanban`;
  $("title").textContent = board.title;
  $("goal").textContent = board.goal;
  const done = tasks.filter(t => t.status === "done").length;
  $("completion-label").textContent = `${done} of ${tasks.length} tasks done`;
  $("progress").max = tasks.length || 1;
  $("progress").value = done;
  $("summary").hidden = !board.summary && board.mode === "active";
  $("summary").className = `summary ${board.mode}`;
  $("summary").textContent = `${board.mode === "paused" ? "Paused · " : board.mode === "complete" ? "Complete · " : ""}${board.summary}`;
  $("updated").textContent = `Board updated ${age(board.updated_at)}`;
  const currentAgent = $("agent").value;
  const owners = [...new Set(tasks.map(t => t.assignee).filter(Boolean))].sort();
  const oldOwners = [...$("agent").options].slice(1).map(o => o.value);
  if (JSON.stringify(oldOwners) !== JSON.stringify(owners)) {
    $("agent").replaceChildren(new Option("All agents", ""), ...owners.map(o => new Option(o, o)));
    $("agent").value = owners.includes(currentAgent) ? currentAgent : "";
  }
  const query = $("search").value.toLowerCase().trim();
  const visible = tasks.filter(t => (!$("agent").value || t.assignee === $("agent").value) &&
    [t.id,t.title,t.description,t.assignee,t.reviewer,...t.criteria].join(" ").toLowerCase().includes(query));
  $("showing").textContent = `${visible.length} tasks shown`;
  const focused = document.activeElement?.dataset.taskId;
  const scrolls = [...document.querySelectorAll(".cards")].map(n => n.scrollTop);
  const columns = Object.entries(labels).map(([status, label], index) => {
    const column = el("section", `column ${status}`);
    column.setAttribute("aria-label", label);
    const header = el("div", "column-header");
    const group = visible.filter(t => t.status === status).sort((a,b) => ({high:0,normal:1,low:2}[a.priority]-{high:0,normal:1,low:2}[b.priority]) || a.id.localeCompare(b.id));
    header.append(el("span", "dot"), el("h2", "", label), el("span", "count", String(group.length)));
    const cards = el("div", "cards");
    for (const task of group) {
      const card = el("button", "card");
      card.type = "button";
      card.dataset.taskId = task.id;
      card.setAttribute("aria-label", `${task.id}: ${task.title}`);
      const top = el("span", "card-top");
      top.append(el("span", "task-id", task.id), el("span", "priority", task.priority === "high" ? "↑ High" : ""));
      card.append(top, el("span", "card-title", task.title));
      if (task.description) card.append(el("span", "card-description", task.description));
      const owner = el("span", "owner");
      const initials = (task.assignee || "?").split(/\s+/).slice(0,2).map(s => s[0]).join("").toUpperCase();
      owner.append(el("span", "avatar", initials), el("span", "", `${status === "backlog" ? "Planned: " : ""}${task.assignee || "Unassigned"}`));
      card.append(owner);
      const meta = el("span", "card-meta");
      meta.append(el("span", "", age(task.updated_at)), el("span", "", task.depends_on.length ? `${task.depends_on.length} dependencies` : `rev ${task.revision}`));
      card.append(meta);
      if (status === "blocked") card.append(el("span", "warning", task.blocker));
      if (status === "in_review") card.append(el("span", "warning", `Review: ${task.reviewer}`));
      if (status === "in_progress" && Date.now()-Date.parse(task.updated_at)>15*60000) card.append(el("span", "warning", "No update in 15+ minutes · activity unconfirmed"));
      card.addEventListener("click", () => { selected = task.id; renderDetail(); $("detail").showModal(); });
      cards.append(card);
    }
    if (!group.length) cards.append(el("p", "empty", visible.length !== tasks.length ? "No matching tasks" : status === "in_progress" ? "No agent working here" : "No tasks here"));
    column.append(header, cards);
    column.dataset.scroll = String(scrolls[index] || 0);
    return column;
  });
  $("board").replaceChildren(...columns);
  for (const column of columns) column.querySelector(".cards").scrollTop = Number(column.dataset.scroll);
  if (focused && !$("detail").open) [...document.querySelectorAll(".card")].find(n => n.dataset.taskId === focused)?.focus({preventScroll:true});
  $("activity").replaceChildren(el("div", "eyebrow", `Latest ${data.history_limit} events at most`), ...data.events.map(eventNode));
  if ($("detail").open) renderDetail();
}
function renderDetail() {
  const task = data.tasks.find(t => t.id === selected);
  if (!task) { $("detail").close(); return; }
  $("detail-id").textContent = `${task.id} · revision ${task.revision}`;
  const title = el("h2", "", task.title);
  title.id = "detail-title";
  const meta = el("div", "detail-meta");
  meta.append(el("span", "", labels[task.status]), el("span", "", `${task.status === "backlog" ? "Planned agent" : "Agent"}: ${task.assignee || "Unassigned"}`));
  if (task.reviewer) meta.append(el("span", "", `Reviewer: ${task.reviewer}`));
  const nodes = [title,meta,el("p", "", task.description || "No additional description.")];
  if (task.blocker) nodes.push(el("h3", "", "Blocker"),el("p", "", task.blocker));
  for (const [title, items] of [["Acceptance criteria",task.criteria],["Depends on",task.depends_on.map(id => `${id} — ${labels[data.tasks.find(t=>t.id===id)?.status] || "Unknown"}`)],["Evidence",task.evidence]]) {
    nodes.push(el("h3", "", title));
    const list = el("ul");
    items.forEach(item => list.append(el("li", "", item)));
    nodes.push(items.length ? list : el("p", "small", "None recorded."));
  }
  nodes.push(el("h3", "", "Recent task activity"), ...data.events.filter(e=>e.task_id===task.id).map(eventNode));
  $("detail-body").replaceChildren(...nodes);
}
async function refresh() {
  clearTimeout(timer);
  try {
    const response = await fetch("/api/board", {headers:etag ? {"If-None-Match":etag} : {}, signal:AbortSignal.timeout(5000)});
    if (response.status !== 304) {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      data = await response.json();
      etag = response.headers.get("ETag");
    }
    connectedAt = new Date();
    $("connection").textContent = "Live · refreshes every 2s";
    $("connection").className = "connection live";
    render();
  } catch {
    $("connection").textContent = `Disconnected · ${connectedAt ? "showing last received board" : "retrying"}`;
    $("connection").className = "connection offline";
    if (!data) $("board").replaceChildren(el("p", "empty", "Cannot reach the board. Retrying automatically…"));
  } finally { timer = setTimeout(refresh, 2000); }
}
$("search").addEventListener("input", render);
$("agent").addEventListener("change", render);
$("activity-toggle").addEventListener("click", () => {
  $("activity").hidden = !$("activity").hidden;
  $("activity-toggle").setAttribute("aria-expanded", String(!$("activity").hidden));
});
$("close-detail").addEventListener("click", () => $("detail").close());
$("detail").addEventListener("click", event => { if (event.target === $("detail")) { const r=$("detail").getBoundingClientRect(); if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom) $("detail").close(); }});
window.addEventListener("online", () => { $("connection").textContent = "Reconnecting…"; });
refresh();
