"use strict";

const NAMES = {
  KOK: "Kokoomus", PS: "Perussuomalaiset", SDP: "SDP", KESK: "Keskusta", VAS: "Vasemmistoliitto",
  VIHR: "Vihreät", RKP: "RKP", KD: "Kristillisdemokraatit", LIIK: "Liike Nyt", Muut: "Muut / Ahvenanmaa",
  HALLITUS: "Hallituspuolueet", OPPOSITIO: "Oppositiopuolueet",
};
const PHASES = ["nousu", "hidastuminen", "lasku", "elpyminen"];
const PHASE_LABEL = { nousu: "Nousu", hidastuminen: "Hidastuminen", lasku: "Lasku", elpyminen: "Elpyminen" };
const SVGNS = "http://www.w3.org/2000/svg";

const $ = (id) => document.getElementById(id);
const pc = (p) => `var(--p-${p}, var(--ink-3))`;
const fmt = (n, d = 1) => (n == null || isNaN(n) ? "–" : n.toFixed(d).replace(".", ",").replace("-", "−"));
const sfmt = (n, d = 1) => (n > 0 ? "+" : "") + fmt(n, d);
const ml = (m) => `${+m.slice(5, 7)}/${m.slice(0, 4)}`;
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function svg(tag, attrs = {}, parent) {
  const e = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
function text(parent, x, y, s, attrs = {}) {
  const t = svg("text", { x, y, ...attrs }, parent);
  t.textContent = s;
  return t;
}
function scale(d0, d1, r0, r1) {
  const f = (v) => r0 + ((v - d0) / (d1 - d0 || 1)) * (r1 - r0);
  f.inv = (p) => d0 + ((p - r0) / (r1 - r0 || 1)) * (d1 - d0);
  return f;
}
function niceStep(range, target) {
  const raw = range / target, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const n = raw / mag;
  return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * mag;
}

/* ---------- tooltip ---------- */
const tip = $("tip");
function showTip(ev, html) {
  tip.innerHTML = html;
  tip.style.display = "block";
  const w = tip.offsetWidth, h = tip.offsetHeight;
  let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + w > innerWidth - 8) x = ev.clientX - w - 14;
  if (y + h > innerHeight - 8) y = ev.clientY - h - 14;
  tip.style.left = Math.max(8, x) + "px";
  tip.style.top = Math.max(8, y) + "px";
}
let tipCleanup = null; // e.g. hides a chart's crosshair together with the tooltip
function hideTip() {
  tip.style.display = "none";
  if (tipCleanup) { tipCleanup(); tipCleanup = null; }
}
// Chart elements with a tooltip: shown on hover (mouse) and on tap (touch, pointerdown).
function onTip(el, handler) {
  el.classList.add("hit");
  el.addEventListener("mousemove", handler);
  el.addEventListener("pointerdown", handler);
}
// Touch screens never send "mouseleave": a tap/click anywhere outside a chart element, or a scroll,
// closes the tooltip.
addEventListener("pointerdown", (ev) => { if (!ev.target.closest?.(".hit")) hideTip(); }, { passive: true });
addEventListener("scroll", hideTip, { passive: true });

/* ---------- theme ---------- */
(function theme() {
  let saved = null;
  try { saved = localStorage.getItem("theme"); } catch (e) {}
  if (saved) document.documentElement.dataset.theme = saved;
  $("themeBtn").addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) {}
  });
})();

/* ---------- generic line chart ---------- */
function lineChart(el, { xs, xLabel, series, yFmt = (v) => fmt(v, 0), height = 300, yMin, endLabels = true, unit = "%",
                         pos, bands = [], ticks, dashLast = false, tipExtra }) {
  // pos: numeric x position per point (default: index). bands: [{from, to, label, color, title}] in pos units.
  // dashLast: draw each series' final segment dashed (e.g. "polls now" after the last election).
  el.innerHTML = "";
  const W = el.clientWidth || 600, H = height;
  const P = pos || xs.map((_, i) => i);
  const m = { l: 34, r: endLabels ? 46 : 12, t: bands.length ? 34 : 10, b: 24 };
  const vals = series.flatMap((s) => s.values).filter((v) => v != null);
  if (!vals.length) return;
  let lo = yMin != null ? yMin : Math.min(...vals), hi = Math.max(...vals);
  const step = niceStep(hi - lo || 1, 5);
  lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
  const x0 = Math.min(P[0], ...bands.map((b) => b.from)), x1 = Math.max(P[P.length - 1], ...bands.map((b) => b.to));
  const x = scale(x0, x1, m.l, W - m.r), y = scale(lo, hi, H - m.b, m.t);
  const root = svg("svg", { width: W, height: H, role: "img" }, el);
  // background bands (e.g. governments)
  bands.forEach((b, i) => {
    const bx = x(Math.max(b.from, x0)), bw = Math.max(0, x(Math.min(b.to, x1)) - bx);
    if (i % 2 === 0) svg("rect", { x: bx, y: m.t, width: bw, height: H - m.t - m.b, fill: "var(--rule-2)", opacity: 0.6 }, root);
    svg("rect", { x: bx + 0.5, y: m.t - 6, width: Math.max(0, bw - 1), height: 4, fill: b.color, rx: 1 }, root);
    if (bw > 18) {
      const t = text(root, bx + bw / 2, m.t - 10, b.label, { "text-anchor": "middle", "font-size": bw < 44 ? 9 : 10 });
      if (bw < 44) { t.setAttribute("transform", `rotate(-35 ${bx + bw / 2} ${m.t - 10})`); t.setAttribute("text-anchor", "start"); }
    }
  });
  const g = svg("g", { class: "grid" }, root);
  for (let v = lo; v <= hi + 1e-9; v += step) {
    svg("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v) }, g);
    text(root, m.l - 6, y(v) + 4, yFmt(v), { "text-anchor": "end" });
  }
  if (ticks) {
    const minGap = 34; let last = -1e9;
    for (const t of ticks) { const tx = x(t.pos); if (Math.abs(tx - last) >= minGap) { text(root, tx, H - 6, t.label, { "text-anchor": "middle" }); last = tx; } }
  } else {
    const every = Math.max(1, Math.ceil(xs.length / Math.max(2, Math.floor((W - m.l - m.r) / 70))));
    xs.forEach((d, i) => { if (i % every === 0 || i === xs.length - 1 && xs.length < 20) text(root, x(P[i]), H - 6, xLabel(d), { "text-anchor": "middle" }); });
  }
  for (const s of series) {
    const idx = s.values.map((v, i) => (v == null ? -1 : i)).filter((i) => i >= 0);
    let d = "", pen = false;
    s.values.forEach((v, i) => {
      if (v == null) { pen = false; return; }
      if (dashLast && i === idx[idx.length - 1] && idx.length > 1) return;
      d += (pen ? "L" : "M") + x(P[i]).toFixed(1) + "," + y(v).toFixed(1);
      pen = true;
    });
    svg("path", { d, fill: "none", stroke: s.color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, root);
    if (dashLast && idx.length > 1) {
      const a = idx[idx.length - 2], b = idx[idx.length - 1];
      svg("path", { d: `M${x(P[a])},${y(s.values[a])}L${x(P[b])},${y(s.values[b])}`, fill: "none", stroke: s.color, "stroke-width": 2, "stroke-dasharray": "3 4", "stroke-linecap": "round" }, root);
    }
    if (s.dots) idx.forEach((i, k) => svg("circle", { cx: x(P[i]), cy: y(s.values[i]), r: 3, fill: dashLast && k === idx.length - 1 ? "var(--bg)" : s.color, stroke: dashLast && k === idx.length - 1 ? s.color : "var(--bg)", "stroke-width": 1.5 }, root));
  }
  if (endLabels) {
    const labs = series.map((s) => {
      let i = s.values.length - 1;
      while (i >= 0 && s.values[i] == null) i--;
      return i < 0 ? null : { s, y: y(s.values[i]), x: x(P[i]) };
    }).filter(Boolean).sort((a, b) => a.y - b.y);
    for (let i = 1; i < labs.length; i++) if (labs[i].y - labs[i - 1].y < 12) labs[i].y = labs[i - 1].y + 12;
    for (const l of labs) text(root, l.x + 6, l.y + 4, l.s.short || l.s.key, { class: "lab" });
  }
  // hover layer
  const cross = svg("line", { y1: m.t, y2: H - m.b, stroke: "var(--ink-3)", "stroke-width": 1, visibility: "hidden" }, root);
  const hit = svg("rect", { x: m.l, y: 0, width: W - m.l - m.r, height: H, fill: "transparent" }, root);
  onTip(hit, (ev) => {
    const r = root.getBoundingClientRect(), px = x.inv(ev.clientX - r.left);
    let i = 0;
    P.forEach((p, k) => { if (Math.abs(p - px) < Math.abs(P[i] - px)) i = k; });
    cross.setAttribute("x1", x(P[i])); cross.setAttribute("x2", x(P[i])); cross.setAttribute("visibility", "visible");
    const rows = series.filter((s) => s.values[i] != null).sort((a, b) => b.values[i] - a.values[i])
      .map((s) => `<div class="row"><span><span class="pdot" style="background:${s.color}"></span>${esc(s.name)}</span><b>${fmt(s.values[i])} ${unit}</b></div>`).join("");
    showTip(ev, `<b>${esc(xLabel(xs[i]))}</b>${tipExtra ? tipExtra(i) : ""}${rows}`);
    tipCleanup = () => cross.setAttribute("visibility", "hidden");
  });
  hit.addEventListener("mouseleave", () => { cross.setAttribute("visibility", "hidden"); hideTip(); });
}

function legend(el, items, onToggle) {
  el.innerHTML = "";
  for (const it of items) {
    const b = document.createElement("button");
    b.innerHTML = `<span class="pdot" style="background:${it.color}"></span>${esc(it.name)}`;
    if (it.off) b.classList.add("off");
    if (onToggle) b.addEventListener("click", () => onToggle(it.key));
    else b.style.cursor = "default";
    el.appendChild(b);
  }
}

/* ---------- state & render ---------- */
let D;
const state = { mapIdx: 0, lineMode: "parties", hidden: new Set(), compassIdx: -1, agreeMode: "agreement", playing: null };

fetch("data/site.json", { cache: "no-cache" })
  .then((r) => r.json())
  .then((d) => { D = d; renderAll(); })
  .catch((e) => { $("heroWord").textContent = "Tietoja ei saatu"; console.error(e); });

function renderAll() {
  renderHero();
  setupMap();
  renderPartyList();
  setupLine();
  renderPollTable();
  renderSeats();
  renderParliament();
  setupCompass();
  renderInitiatives();
  renderHistory();
  $("updated").textContent = "Päivitetty " + D.updated;
  $("footUpdated").textContent = "päivitetty " + D.updated;
  $("pollSrc").href = D.polls.source;
  setupNav();
  let t;
  addEventListener("resize", () => { clearTimeout(t); t = setTimeout(rerenderCharts, 150); });
}
function rerenderCharts() { drawMap(); drawLine(); drawCompass(); renderHistory(); renderParliament(); }

/* ---------- hero ---------- */
function runStart(series) {
  const last = series[series.length - 1].phase;
  let i = series.length - 1;
  while (i > 0 && series[i - 1].phase === last) i--;
  return series[i].m;
}
function renderHero() {
  const S = D.polls.series, gov = S.HALLITUS, last = gov[gov.length - 1];
  $("heroWord").textContent = PHASE_LABEL[last.phase];
  $("heroWord").style.color = `var(--${last.phase === "hidastuminen" ? "ink" : last.phase})`;
  $("heroSince").textContent = ml(runStart(gov)) + " alkaen";
  $("heroSub").innerHTML = `Hallituspuolueet ${fmt(last.avg)} % (vaalit ${fmt(D.polls.election2023.HALLITUS)} %, ${sfmt(last.level)} %-yks.) · 3 kk muutos ${sfmt(last.change)} %-yks.`;
  const latest = Object.fromEntries(D.parties.map((p) => [p, S[p][S[p].length - 1]]));
  $("phaseRows").innerHTML = PHASES.map((ph) => {
    const ps = D.parties.filter((p) => latest[p].phase === ph);
    return `<span class="lbl ${ph === last.phase ? "on" : ""}">${PHASE_LABEL[ph]}</span>
      <span class="chips">${ps.map((p) => `<span class="chip ${ph}" title="${NAMES[p]}: ${fmt(latest[p].avg)} %">${p}</span>`).join("")}</span>
      <span class="num">${ps.length}</span>`;
  }).join("");

  const days = Math.ceil((new Date(D.nextElection) - new Date()) / 864e5);
  const sorted = [...D.parties].sort((a, b) => D.polls.latest[b] - D.polls.latest[a]);
  const seats = D.seats.government;
  const tiles = [
    { t: "Eduskuntavaaleihin", v: `${days} <small>päivää</small>`, s: new Date(D.nextElection).toLocaleDateString("fi-FI") },
    { t: "Suurin puolue mittauksissa", v: `${sorted[0]} <small>${fmt(D.polls.latest[sorted[0]])} %</small>`, s: `2. ${sorted[1]} ${fmt(D.polls.latest[sorted[1]])} % · 3. ${sorted[2]} ${fmt(D.polls.latest[sorted[2]])} %` },
    { t: "Hallituksen paikkaennuste", v: `${seats} <small>/ 200</small>`, s: seats >= 101 ? "enemmistö säilyisi" : `enemmistöstä puuttuu ${101 - seats}` },
  ];
  if (D.parliament) {
    const defeats = D.parliament.monthly.reduce((a, m) => a + m.defeats, 0);
    tiles.push({ t: "Täysistuntoäänestyksiä 2023–", v: D.parliament.totalVotes.toLocaleString("fi-FI"), s: `hallitus hävinnyt ${defeats}` });
  } else {
    tiles.push({ t: "Kansalaisaloitteita käynnissä", v: D.initiatives.running, s: `${D.initiatives.runningOver50k} yli 50 000 kannattajaa` });
  }
  $("heroTiles").innerHTML = tiles.map((x) => `<div class="tile"><div class="t">${x.t}</div><div class="v">${x.v}</div><div class="s">${x.s}</div></div>`).join("");
}

/* ---------- support map ---------- */
function setupMap() {
  const months = D.polls.months;
  const sl = $("mapSlider");
  sl.max = months.length - 1; sl.value = months.length - 1; state.mapIdx = months.length - 1;
  sl.addEventListener("input", () => { state.mapIdx = +sl.value; drawMap(); });
  $("mapPlay").addEventListener("click", () => {
    if (state.playing) { clearInterval(state.playing); state.playing = null; $("mapPlay").textContent = "▶"; return; }
    if (state.mapIdx >= months.length - 1) state.mapIdx = 3;
    $("mapPlay").textContent = "❚❚";
    state.playing = setInterval(() => {
      state.mapIdx++;
      sl.value = state.mapIdx; drawMap();
      if (state.mapIdx >= months.length - 1) { clearInterval(state.playing); state.playing = null; $("mapPlay").textContent = "▶"; }
    }, 450);
  });
  const lp = D.polls.latestPolls.map((p) => `${p.firm} ${new Date(p.date).toLocaleDateString("fi-FI")}`).join(", ");
  $("pollMeta").textContent = "Viimeisimmät: " + lp;
  drawMap();
}
function drawMap() {
  const el = $("mapChart"), S = D.polls.series, idx = state.mapIdx, months = D.polls.months;
  el.innerHTML = "";
  $("mapWhen").textContent = ml(months[idx]);
  const W = el.clientWidth || 600, H = Math.min(460, Math.max(320, W * 0.72));
  const m = { l: 34, r: 14, t: 14, b: 26 };
  let mx = 1, my = 1;
  for (const p of D.parties) for (const r of S[p].slice(3)) { mx = Math.max(mx, Math.abs(r.change)); my = Math.max(my, Math.abs(r.level)); }
  mx = Math.ceil(mx); my = Math.ceil(my);
  const x = scale(-mx, mx, m.l, W - m.r), y = scale(-my, my, H - m.b, m.t);
  const root = svg("svg", { width: W, height: H, role: "img", "aria-label": "Kannatuskartta" }, el);
  const g = svg("g", { class: "grid" }, root);
  const sx = niceStep(2 * mx, 6), sy = niceStep(2 * my, 6);
  for (let v = -Math.floor(mx / sx) * sx; v <= mx; v += sx) { svg("line", { x1: x(v), x2: x(v), y1: m.t, y2: H - m.b }, g); text(root, x(v), H - 8, sfmt(v, 0), { "text-anchor": "middle" }); }
  for (let v = -Math.floor(my / sy) * sy; v <= my; v += sy) { svg("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v) }, g); text(root, m.l - 6, y(v) + 4, sfmt(v, 0), { "text-anchor": "end" }); }
  svg("line", { class: "zero", x1: x(0), x2: x(0), y1: m.t, y2: H - m.b, "stroke-width": 1.5 }, root);
  svg("line", { class: "zero", x1: m.l, x2: W - m.r, y1: y(0), y2: y(0), "stroke-width": 1.5 }, root);
  const ql = [["Hidastuminen", m.l + 6, m.t + 14, "start"], ["Nousu", W - m.r - 6, m.t + 14, "end"],
              ["Lasku", m.l + 6, H - m.b - 8, "start"], ["Elpyminen", W - m.r - 6, H - m.b - 8, "end"]];
  for (const [s, qx, qy, a] of ql) text(root, qx, qy, s, { class: "q-label", "text-anchor": a });

  const pts = [];
  for (const p of D.parties) {
    const ser = S[p], cur = ser[idx];
    const trail = ser.slice(Math.max(3, idx - 6), idx + 1);
    if (trail.length > 1) {
      svg("polyline", { points: trail.map((r) => `${x(r.change)},${y(r.level)}`).join(" "), fill: "none", stroke: pc(p), "stroke-width": 1.5, opacity: 0.45, "stroke-linejoin": "round" }, root);
    }
    pts.push({ p, cur, cx: x(cur.change), cy: y(cur.level) });
  }
  // labels with simple vertical de-collision
  const labs = pts.map((o) => ({ ...o, ly: o.cy - 10 })).sort((a, b) => a.ly - b.ly);
  for (let i = 1; i < labs.length; i++) {
    const prev = labs[i - 1];
    if (Math.abs(labs[i].cx - prev.cx) < 34 && labs[i].ly - prev.ly < 12) labs[i].ly = prev.ly + 12;
  }
  for (const o of pts) {
    const c = svg("circle", { cx: o.cx, cy: o.cy, r: 6.5, fill: pc(o.p), stroke: "var(--bg)", "stroke-width": 2 }, root);
    const hit = svg("circle", { cx: o.cx, cy: o.cy, r: 14, fill: "transparent" }, root);
    onTip(hit, (ev) => showTip(ev, `<b>${NAMES[o.p]}</b> · ${ml(o.cur.m)}
      <div class="row"><span>Kannatus (3 kk ka.)</span><b>${fmt(o.cur.avg)} %</b></div>
      <div class="row"><span>Ero vaaleihin</span><b>${sfmt(o.cur.level)}</b></div>
      <div class="row"><span>Muutos 3 kk</span><b>${sfmt(o.cur.change)}</b></div>
      <div class="row"><span>Vaihe</span><b>${PHASE_LABEL[o.cur.phase]}</b></div>`));
    hit.addEventListener("mouseleave", hideTip);
  }
  for (const l of labs) text(root, l.cx, l.ly, l.p, { class: "lab", "text-anchor": "middle" });
}

function renderPartyList() {
  const S = D.polls.series;
  const rows = [...D.parties].sort((a, b) => S[b][S[b].length - 1].avg - S[a][S[a].length - 1].avg).map((p) => {
    const ser = S[p], cur = ser[ser.length - 1], last12 = ser.slice(-12);
    const strip = last12.map((r, i) => `<i class="${r.phase}${i === last12.length - 1 ? " last" : ""}" title="${ml(r.m)}: ${PHASE_LABEL[r.phase]}"></i>`).join("");
    const gov = D.government.includes(p) ? "hallitus" : "oppositio";
    return `<tr><td><div class="pn"><span class="pdot" style="background:${pc(p)}"></span><div>${NAMES[p]}<div class="dl">${gov}</div></div></div></td>
      <td class="num">${fmt(cur.avg)} %</td>
      <td class="num ${cur.level >= 0 ? "pos" : "neg"}">${sfmt(cur.level)}</td>
      <td><div class="strip">${strip}</div></td></tr>`;
  });
  $("partyList").innerHTML = rows.join("");
}

/* ---------- monthly support lines ---------- */
function setupLine() {
  $("lineMode").addEventListener("click", (ev) => {
    const b = ev.target.closest("button"); if (!b) return;
    state.lineMode = b.dataset.m;
    for (const x of $("lineMode").children) x.classList.toggle("on", x === b);
    drawLine();
  });
  drawLine();
}
function drawLine() {
  const S = D.polls.series;
  const keys = state.lineMode === "parties" ? D.parties : ["HALLITUS", "OPPOSITIO"];
  const color = (k) => (k === "HALLITUS" ? "var(--gov)" : k === "OPPOSITIO" ? "var(--opp)" : pc(k));
  legend($("lineLegend"), keys.map((k) => ({ key: k, name: NAMES[k], color: color(k), off: state.hidden.has(k) })),
    (k) => { state.hidden.has(k) ? state.hidden.delete(k) : state.hidden.add(k); drawLine(); });
  const series = keys.filter((k) => !state.hidden.has(k)).map((k) => ({
    key: k, short: k === "HALLITUS" ? "Hall." : k === "OPPOSITIO" ? "Opp." : k, name: NAMES[k], color: color(k),
    values: S[k].map((r) => r.raw),
  }));
  lineChart($("lineChart"), { xs: D.polls.months, xLabel: ml, series, yMin: 0, height: 320 });
}
function renderPollTable() {
  const rows = D.polls.polls.slice(0, 20);
  $("pollTable").innerHTML = `<table class="data"><thead><tr><th>Päivä</th><th>Laitos</th><th class="num">n</th>${D.parties.map((p) => `<th class="num">${p}</th>`).join("")}</tr></thead><tbody>${
    rows.map((r) => `<tr><td>${new Date(r.date).toLocaleDateString("fi-FI")}</td><td>${esc(r.firm)}</td><td class="num">${r.n ? r.n.toLocaleString("fi-FI") : "–"}</td>${D.parties.map((p) => `<td class="num">${fmt(r[p])}</td>`).join("")}</tr>`).join("")
  }</tbody></table>`;
}

/* ---------- seats ---------- */
function renderSeats() {
  const T = D.seats.total, prev = D.seats.seats2023;
  const order = [...D.government, ...D.opposition, "Muut"];
  $("seatBar").innerHTML = order.filter((p) => T[p]).map((p) =>
    `<div style="flex:${T[p]};background:${pc(p)}" title="${NAMES[p]}: ${T[p]}">${T[p] >= 8 ? p + " " + T[p] : ""}</div>`).join("");
  legend($("seatLegend"), order.filter((p) => T[p] || prev[p]).map((p) => ({ key: p, color: pc(p), name: `${p} ${T[p] || 0} (${sfmt((T[p] || 0) - (prev[p] || 0), 0)})` })));
  $("seatMeta").textContent = `Hallitus ${D.seats.government} · oppositio ${200 - D.seats.government - (T.Muut || 0)} · suluissa muutos vuoden 2023 vaaleista`;
  const ps = [...D.parties];
  $("seatTable").innerHTML = `<thead><tr><th>Vaalipiiri</th><th class="num">Paikat</th>${ps.map((p) => `<th class="num">${p}</th>`).join("")}</tr></thead><tbody>${
    D.seats.districts.filter((d) => d.vp !== "VP05").map((d) => `<tr><td>${esc(d.name)}</td><td class="num">${Object.values(d.seats).reduce((a, b) => a + b, 0)}</td>${ps.map((p) => `<td class="num">${d.seats[p] || ""}</td>`).join("")}</tr>`).join("")
  }</tbody>`;
}

/* ---------- parliament ---------- */
function mean(a) { const v = a.filter((x) => x != null); return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null; }
function renderParliament() {
  const P = D.parliament, el = $("parlBody");
  if (!P) { el.innerHTML = `<div class="empty">Äänestysdataa ei ole vielä haettu.</div>`; return; }
  const tot = P.monthly.reduce((a, m) => ({ defeats: a.defeats + m.defeats, close: a.close + m.close, rebel: a.rebel + m.rebel }), { defeats: 0, close: 0, rebel: 0 });
  $("parlMeta").textContent = `${new Date(P.firstVote).toLocaleDateString("fi-FI")}–${new Date(P.lastVote).toLocaleDateString("fi-FI")}`;
  const parties = D.parties.map((p) => {
    const ms = P.mps.filter((r) => r.party === p);
    const present = ms.reduce((a, r) => a + (r.votes * r.attendance) / 100, 0), reb = ms.reduce((a, r) => a + r.rebel, 0);
    return { p, att: mean(P.parties[p].map((r) => r.attendance)), coh: mean(P.parties[p].map((r) => r.cohesion)), per1000: present ? (1000 * reb) / present : null };
  }).sort((a, b) => a.per1000 - b.per1000);
  el.innerHTML = `
    <div class="tiles" style="grid-template-columns:repeat(auto-fit,minmax(170px,1fr));margin-bottom:28px">
      <div class="tile"><div class="t">Äänestyksiä</div><div class="v">${P.totalVotes.toLocaleString("fi-FI")}</div><div class="s">vaalikausi 2023–</div></div>
      <div class="tile"><div class="t">Hallituksen tappiot</div><div class="v">${tot.defeats}</div><div class="s">hallitusryhmien enemmistö hävisi</div></div>
      <div class="tile"><div class="t">Tiukat äänestykset</div><div class="v">${tot.close}</div><div class="s">jaa–ei-ero enintään 10</div></div>
      <div class="tile"><div class="t">Poikkeavia ääniä</div><div class="v">${tot.rebel.toLocaleString("fi-FI")}</div><div class="s">oman ryhmän linjaa vastaan</div></div>
    </div>
    <div class="grid2">
      <div>
        <div class="panel-title"><span>Ryhmien yhtenäisyys ja läsnäolo</span><span class="meta">yhtenäisyys kiistanalaisissa äänestyksissä</span></div>
        <div class="scroll-x"><table class="data"><thead><tr><th>Ryhmä</th><th class="num">Yhtenäisyys</th><th class="num">Poikk. / 1000</th><th class="num">Läsnäolo</th></tr></thead><tbody>
        ${parties.map((r) => `<tr><td><span class="pdot" style="background:${pc(r.p)}"></span>${NAMES[r.p]}</td><td class="num">${fmt(r.coh)}</td><td class="num">${fmt(r.per1000)}</td><td class="num">${fmt(r.att)} %</td></tr>`).join("")}
        </tbody></table></div>
        <div class="panel-title" style="margin-top:28px"><span>Äänestykset kuukausittain</span><span class="meta"><span class="pdot" style="background:var(--lasku)"></span>hallituksen tappiot</span></div>
        <div class="chart" id="voteBars"></div>
      </div>
      <div>
        <div class="panel-title"><span>Kuinka usein ryhmät äänestävät samoin</span>
          <div class="seg" id="agreeMode"><button data-m="agreement" class="${state.agreeMode === "agreement" ? "on" : ""}">Koko kausi</button><button data-m="agreement12" class="${state.agreeMode === "agreement12" ? "on" : ""}">12 kk</button></div></div>
        <div class="heat" id="heat"></div>
        <div class="legend-note">% äänestyksistä, joissa ryhmien enemmistöt äänestivät samoin.</div>
      </div>
    </div>
    <div class="grid2" style="margin-top:32px">
      <div>
        <div class="panel-title"><span>Eniten ryhmän linjasta poikenneet</span><span class="meta">poikkeavat äänet</span></div>
        <div class="scroll-x"><table class="data"><thead><tr><th>Edustaja</th><th>Ryhmä</th><th class="num">Poikk.</th><th class="num">% äänistä</th><th class="num">Läsnä</th></tr></thead><tbody>
        ${P.mps.slice(0, 15).map((r) => `<tr><td>${esc(r.name)}</td><td><span class="pdot" style="background:${pc(r.party)}"></span>${r.party}</td><td class="num">${r.rebel}</td><td class="num">${fmt(r.rebelPct, 1)}</td><td class="num">${fmt(r.attendance, 0)} %</td></tr>`).join("")}
        </tbody></table></div>
      </div>
      <div>
        <div class="panel-title"><span>Viimeisimmät hallituksen tappiot</span></div>
        <ul class="ini">${P.defeats.slice(0, 8).map((d) => `<li>${esc(d.item || d.title)}<div class="meta"><span>${esc(d.title)}</span><span>${d.res[0]}–${d.res[1]} · ${new Date(d.t).toLocaleDateString("fi-FI")}</span></div></li>`).join("") || '<li class="empty">Ei tappioita.</li>'}</ul>
      </div>
    </div>`;
  $("agreeMode").addEventListener("click", (ev) => {
    const b = ev.target.closest("button"); if (!b) return;
    state.agreeMode = b.dataset.m; renderParliament();
  });
  drawHeat(); drawVoteBars();
}
function drawHeat() {
  const A = D.parliament[state.agreeMode], ps = D.parties, el = $("heat");
  el.style.gridTemplateColumns = `40px repeat(${ps.length}, minmax(0,1fr))`;
  let h = `<div class="h"></div>` + ps.map((p) => `<div class="h">${p}</div>`).join("");
  for (const a of ps) {
    h += `<div class="h">${a}</div>`;
    for (const b of ps) {
      if (a === b) { h += `<div style="background:var(--rule-2)"></div>`; continue; }
      const v = A[`${a}-${b}`];
      const t = v == null ? 0 : Math.max(0, (v - 30) / 70);
      h += `<div title="${NAMES[a]} – ${NAMES[b]}: ${fmt(v)} %" style="background:color-mix(in oklab, var(--heat-1) ${Math.round(t * 100)}%, var(--heat-0));color:${t > 0.55 ? "var(--bg)" : "var(--ink-2)"}">${v == null ? "" : Math.round(v)}</div>`;
    }
  }
  el.innerHTML = h;
}
function drawVoteBars() {
  const el = $("voteBars"), M = D.parliament.monthly.filter((m) => m.votes > 0);
  el.innerHTML = "";
  const W = el.clientWidth || 500, H = 170, m = { l: 34, r: 8, t: 8, b: 22 };
  const hi = Math.max(...M.map((r) => r.votes));
  const step = niceStep(hi, 4), top = Math.ceil(hi / step) * step;
  const y = scale(0, top, H - m.b, m.t), bw = (W - m.l - m.r) / M.length;
  const root = svg("svg", { width: W, height: H }, el);
  const g = svg("g", { class: "grid" }, root);
  for (let v = 0; v <= top; v += step) { svg("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v) }, g); text(root, m.l - 6, y(v) + 4, v, { "text-anchor": "end" }); }
  M.forEach((r, i) => {
    const x0 = m.l + i * bw + 1, w = Math.max(1, bw - 2);
    svg("rect", { x: x0, y: y(r.votes), width: w, height: y(0) - y(r.votes), fill: "var(--ink-3)", opacity: 0.45, rx: Math.min(2, w / 2) }, root);
    if (r.defeats) svg("rect", { x: x0, y: y(r.defeats), width: w, height: y(0) - y(r.defeats), fill: "var(--lasku)" }, root);
    if (r.m.endsWith("-01") || i === 0) text(root, x0 + w / 2, H - 6, r.m.slice(0, 4), { "text-anchor": "start" });
    const hit = svg("rect", { x: m.l + i * bw, y: m.t, width: bw, height: H - m.t - m.b, fill: "transparent" }, root);
    onTip(hit, (ev) => showTip(ev, `<b>${ml(r.m)}</b><div class="row"><span>Äänestyksiä</span><b>${r.votes}</b></div><div class="row"><span>Hallituksen tappiot</span><b>${r.defeats}</b></div><div class="row"><span>Tiukat</span><b>${r.close}</b></div><div class="row"><span>Poikkeavia ääniä</span><b>${r.rebel}</b></div>`));
    hit.addEventListener("mouseleave", hideTip);
  });
}

/* ---------- compass ---------- */
function setupCompass() {
  const C = D.compass, el = $("compassBody");
  if (!C) { el.innerHTML = `<div class="empty">Äänestysdataa ei ole vielä haettu.</div>`; return; }
  const opts = [{ label: "Koko kausi", i: -1 }, ...C.frames.map((f, i) => ({ label: f.label, i }))];
  el.innerHTML = `<div class="grid2"><div>
      <div class="panel-title"><span>Edustajat ja ryhmien keskipisteet</span>
        <div class="player"><input type="range" id="compSlider" min="0" max="${opts.length - 1}" value="0" aria-label="Kausi"><span class="when" id="compWhen"></span></div></div>
      <div class="chart" id="compassChart"></div>
      <div class="legend" id="compLegend"></div>
    </div><div>
      <div class="panel-title"><span>Ryhmien sijainnit</span><span class="meta" id="compSub"></span></div>
      <table class="data" id="compTable"></table>
      <div class="legend-note" style="margin-top:12px">Vaaka-akseli: oppositio vasemmalla, hallitus oikealla. Pystyakseli: toinen ulottuvuus, suunnattu niin että PS on Vihreitä ylempänä. Liukurin kartat lasketaan kukin 12 kuukauden äänestyksistä erikseen ja käännetään koko kauden kartan suuntaan.</div>
    </div></div>
    ${C.defining ? `<div class="grid2" style="margin-top:28px">${axisExplain(C, 0)}${axisExplain(C, 1)}</div>` : ""}`;
  $("compSlider").addEventListener("input", (ev) => { state.compassIdx = opts[+ev.target.value].i; drawCompass(); });
  $("compSlider").dataset.labels = JSON.stringify(opts.map((o) => o.label));
  legend($("compLegend"), D.parties.map((p) => ({ key: p, name: p, color: pc(p) })));
  drawCompass();
}
function axisExplain(C, dim) {
  const P = C.full.parties, names = Object.keys(P).sort((a, b) => P[a][dim] - P[b][dim]);
  const vals = names.map((p) => P[p][dim]).sort((a, b) => a - b), med = vals[Math.floor(vals.length / 2)];
  const out = names.filter((p) => Math.abs(P[p][dim] - med) > 0.1);
  const rest = names.filter((p) => !out.includes(p));
  const pos = (v) => fmt(v * 100, 0);
  const ends = dim === 0 ? ["vasemmalla", "oikealla"] : ["alhaalla", "ylhäällä"];
  const strength = Math.round((100 * C.explained[1]) / C.explained[0]);
  const summary = dim === 0
    ? `Erottelee lähes täysin hallituksen (${D.government.join(", ")}) ja opposition. Keskellä ne, jotka äänestävät välillä hallituksen kanssa.`
    : `Selvästi muista erottuvat ${out.map((p) => `<b>${p}</b> (${pos(P[p][dim])})`).join(", ") || "ei kukaan"}; muut ryhmät välillä ${pos(P[rest[0]][dim])}…${pos(P[rest[rest.length - 1]][dim])}. Akseli on noin ${strength} % ensimmäisen vahvuudesta, joten erot ovat pieniä.`;
  const rows = C.defining[dim].map((v) => `<li>${esc(v.item.length > 120 ? v.item.slice(0, 117) + "…" : v.item)}
    <div class="meta"><span>${esc(v.title)}</span><span style="white-space:nowrap">${new Date(v.t).toLocaleDateString("fi-FI")}</span></div>
    <div class="meta"><span>${ends[1]} <b>${v.high === "J" ? "jaa" : "ei"}</b>, ${ends[0]} <b>${v.high === "J" ? "ei" : "jaa"}</b></span><span>${v.res[0]}–${v.res[1]}</span></div></li>`).join("");
  return `<div><div class="panel-title"><span>${dim === 0 ? "Vaaka-akseli" : "Pystyakseli"}: mikä sen määrää?</span></div>
    <p class="lede" style="margin:0 0 6px">${summary}</p>
    <div class="legend-note" style="margin:0 0 4px">Äänestykset, jotka erottavat akselin päät parhaiten:</div>
    <ul class="ini">${rows}</ul></div>`;
}

function drawCompass() {
  const C = D.compass; if (!C) return;
  const el = $("compassChart");
  el.innerHTML = "";
  const info = Object.fromEntries(C.full.mps.map(([hn, name, party]) => [hn, { name, party }]));
  const frame = state.compassIdx < 0 ? null : C.frames[state.compassIdx];
  const mps = frame ? frame.mps.filter((r) => info[r[0]]).map(([hn, x, y]) => ({ hn, x, y, ...info[hn] }))
                    : C.full.mps.map(([hn, name, party, x, y]) => ({ hn, name, party, x, y }));
  const parties = frame ? frame.parties : C.full.parties;
  $("compWhen").textContent = frame ? frame.label : "Koko kausi";
  $("compSub").textContent = `${(frame ? frame.votes : C.full.votes).toLocaleString("fi-FI")} kiistanalaista äänestystä`;
  let ext = 0.05;
  for (const r of C.full.mps) ext = Math.max(ext, Math.abs(r[3]), Math.abs(r[4]));
  for (const f of C.frames) for (const r of f.mps) ext = Math.max(ext, Math.abs(r[1]), Math.abs(r[2]));
  ext *= 1.05;
  const W = el.clientWidth || 600, H = Math.min(480, Math.max(320, W * 0.8)), m = { l: 14, r: 14, t: 14, b: 26 };
  const x = scale(-ext, ext, m.l, W - m.r), y = scale(-ext, ext, H - m.b, m.t);
  const root = svg("svg", { width: W, height: H, role: "img", "aria-label": "Nelikenttä" }, el);
  svg("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "none", stroke: "var(--rule)" }, root);
  svg("line", { class: "zero", x1: x(0), x2: x(0), y1: m.t, y2: H - m.b }, root);
  svg("line", { class: "zero", x1: m.l, x2: W - m.r, y1: y(0), y2: y(0) }, root);
  text(root, m.l + 4, H - 8, "← oppositio", {});
  text(root, W - m.r - 4, H - 8, "hallitus →", { "text-anchor": "end" });
  text(root, x(0) + 6, m.t + 14, "2. ulottuvuus ↑", { class: "q-label" });
  for (const r of mps) {
    const c = svg("circle", { cx: x(r.x), cy: y(r.y), r: 3.5, fill: pc(r.party), opacity: 0.6 }, root);
    onTip(c, (ev) => showTip(ev, `<b>${esc(r.name)}</b> · ${r.party}`));
    c.addEventListener("mouseleave", hideTip);
  }
  // Parties that sit (almost) on top of each other share one label, e.g. "KOK · PS · RKP · KD".
  const clusters = [];
  for (const [p, [px, py]] of Object.entries(parties)) {
    const cx = x(px), cy = y(py);
    svg("circle", { cx, cy, r: 8, fill: pc(p), stroke: "var(--bg)", "stroke-width": 2 }, root);
    const c = clusters.find((k) => Math.hypot(k.x - cx, k.y - cy) < 16);
    if (c) c.names.push(p); else clusters.push({ x: cx, y: cy, names: [p] });
  }
  for (const c of clusters) text(root, c.x, c.y - 12, c.names.join(" · "), { class: "lab", "text-anchor": "middle" });
  const rows = Object.entries(parties).sort((a, b) => a[1][0] - b[1][0]);
  $("compTable").innerHTML = `<thead><tr><th>Ryhmä</th><th class="num">Vaaka</th><th class="num">Pysty</th></tr></thead><tbody>${
    rows.map(([p, [px, py]]) => `<tr><td><span class="pdot" style="background:${pc(p)}"></span>${NAMES[p]}</td><td class="num">${fmt(px * 100, 0)}</td><td class="num">${fmt(py * 100, 0)}</td></tr>`).join("")}</tbody>`;
}

/* ---------- initiatives ---------- */
function renderInitiatives() {
  const I = D.initiatives, el = $("iniBody");
  el.innerHTML = `
    <div class="tiles" style="grid-template-columns:repeat(auto-fit,minmax(170px,1fr));margin-bottom:28px">
      <div class="tile"><div class="t">Kannatusta keräämässä</div><div class="v">${I.running}</div><div class="s">aloitetta</div></div>
      <div class="tile"><div class="t">Yli 50 000 käynnissä</div><div class="v">${I.runningOver50k}</div><div class="s">raja eduskuntakäsittelyyn</div></div>
      <div class="tile"><div class="t">50 000 ylittäneet, 12 kk</div><div class="v">${I.succeeded12}</div><div class="s">keräys päättynyt viim. vuoden aikana</div></div>
      <div class="tile"><div class="t">Eduskuntaan viety</div><div class="v">${I.toParliamentTotal}</div><div class="s">vuodesta 2012</div></div>
    </div>
    <div class="grid2"><div>
      <div class="panel-title"><span>Eniten kannatusta keränneet käynnissä olevat</span><span class="meta">palkki = osuus 50 000:sta</span></div>
      <ul class="ini">${I.top.map((x) => `<li><a href="${x.url}" target="_blank" rel="noopener">${esc(x.name)}</a>
        <div class="bar"><span style="width:${Math.min(100, (x.support / 50000) * 100)}%"></span></div>
        <div class="meta"><span>${x.support.toLocaleString("fi-FI")} kannattajaa</span><span>päättyy ${new Date(x.end).toLocaleDateString("fi-FI")}</span></div></li>`).join("")}</ul>
    </div><div>
      <div class="panel-title"><span>Uudet aloitteet vuosittain</span><span class="meta">tummempi = ylitti 50 000</span></div>
      <div class="chart" id="iniBars"></div>
    </div></div>`;
  drawIniBars();
}
function drawIniBars() {
  const el = $("iniBars"), Y = D.initiatives.byYear;
  el.innerHTML = "";
  const W = el.clientWidth || 400, H = 220, m = { l: 34, r: 8, t: 8, b: 22 };
  const hi = Math.max(...Y.map((r) => r.started)), step = niceStep(hi, 4), top = Math.ceil(hi / step) * step;
  const y = scale(0, top, H - m.b, m.t), bw = (W - m.l - m.r) / Y.length;
  const root = svg("svg", { width: W, height: H }, el);
  const g = svg("g", { class: "grid" }, root);
  for (let v = 0; v <= top; v += step) { svg("line", { x1: m.l, x2: W - m.r, y1: y(v), y2: y(v) }, g); text(root, m.l - 6, y(v) + 4, v, { "text-anchor": "end" }); }
  Y.forEach((r, i) => {
    const x0 = m.l + i * bw + 1, w = Math.max(1, bw - 2);
    svg("rect", { x: x0, y: y(r.started), width: w, height: y(0) - y(r.started), fill: "var(--accent)", opacity: 0.35, rx: 2 }, root);
    if (r.over50k) svg("rect", { x: x0, y: y(r.over50k), width: w, height: y(0) - y(r.over50k), fill: "var(--accent)" }, root);
    if (i % Math.ceil(Y.length / 8) === 0) text(root, x0 + w / 2, H - 6, "’" + r.y.slice(2), { "text-anchor": "middle" });
    const hit = svg("rect", { x: m.l + i * bw, y: m.t, width: bw, height: H - m.t - m.b, fill: "transparent" }, root);
    onTip(hit, (ev) => showTip(ev, `<b>${r.y}</b><div class="row"><span>Uusia aloitteita</span><b>${r.started}</b></div><div class="row"><span>Yli 50 000</span><b>${r.over50k}</b></div>`));
    hit.addEventListener("mouseleave", hideTip);
  });
}

/* ---------- history ---------- */
const ymPos = (s) => +s.slice(0, 4) + (+s.slice(5, 7) - 1) / 12;
function governmentBands(nowPos) {
  const govs = D.history.governments.map((g) => ({ ...g, from: ymPos(g.start), to: g.end ? ymPos(g.end) : nowPos }));
  const bands = govs.map((g) => ({ from: g.from, to: g.to, label: g.name.split(" / ")[0], color: pc(g.parties[0]) }));
  const govAt = (t) => govs.find((g) => t >= g.from && t < g.to) || govs[govs.length - 1];
  return { bands, govAt };
}
const govRow = (g) => `<div class="row" style="color:var(--ink-3)"><span>Hallitus: ${esc(g.name)} (${g.parties.join(", ")})</span></div>`;

function renderEconomy() {
  const E = D.economy; if (!E) return;
  if (!state.econMode) {
    state.econMode = "esi";
    $("econMode").addEventListener("click", (ev) => {
      const b = ev.target.closest("button"); if (!b) return;
      state.econMode = b.dataset.m;
      for (const x of $("econMode").children) x.classList.toggle("on", x === b);
      renderEconomy();
    });
  }
  const isEsi = state.econMode === "esi", data = E[state.econMode];
  const xs = data.map((r) => r[0]), pos = xs.map(ymPos);
  const { bands, govAt } = governmentBands(pos[pos.length - 1] + 1 / 12);
  const ticks = [];
  for (let y = Math.ceil(pos[0] / 5) * 5; y <= pos[pos.length - 1]; y += 5) ticks.push({ pos: y, label: String(y) });
  lineChart($("econChart"), {
    xs, pos, endLabels: false, height: 300, unit: isEsi ? "" : "%",
    bands: bands.filter((b) => b.to > pos[0]).map((b) => ({ ...b, from: Math.max(b.from, pos[0]) })),
    series: [{ key: state.econMode, name: isEsi ? "Luottamusindikaattori" : "Työttömyysaste", color: "var(--ink)", values: data.map((r) => r[1]) }],
    yMin: isEsi ? undefined : 0, xLabel: ml, ticks,
    tipExtra: (i) => govRow(govAt(pos[i])),
  });
  $("econNote").textContent = isEsi
    ? "Euroopan komission luottamusindikaattori (ESI): yritysten ja kuluttajien luottamuksen yhdistelmä, kausitasoitettu, pitkän aikavälin keskiarvo = 100. Taustan jaksot ovat hallituksia; yläreunan väri = pääministeripuolue."
    : "Työttömyysaste, trendi (% työvoimasta), Eurostat. Taustan jaksot ovat hallituksia; yläreunan väri = pääministeripuolue.";
}

const SMALL_NAMES = {
  SKP: "Suomen Kommunistinen Puolue", LIBE: "Liberaalipuolue – Vapaus valita", "Piraattip.": "Piraattipuolue",
  EOP: "Eläinoikeuspuolue", FP: "Feministinen puolue", SKE: "Suomen Kansa Ensin", KRIP: "Kristallipuolue",
  VKK: "Valta kuuluu kansalle", VL: "Vapauden liitto", KaL: "Kansalaispuolue", STL: "Seitsemän tähden liike",
  KTP: "Kommunistinen Työväenpuolue", STP: "Suomen Työväenpuolue", KA: "Köyhien Asialla", Muutos2011: "Muutos 2011",
  SSP: "Suomen Senioripuolue", SKS: "Suomen Kansan Sinivalkoiset", KIPU: "Kirjava ”Puolue” – Elonkehän Puolue",
  REM: "Remonttiryhmä", LLP: "Luonnonlakipuolue", SEP: "Suomen Eläkeläisten Puolue",
};
function renderAllParties() {
  const A = D.history.allParties; if (!A || !Object.keys(A).length) return;
  if (!state.allMode) {
    state.allMode = "share";
    $("allMode").addEventListener("click", (ev) => {
      const b = ev.target.closest("button"); if (!b) return;
      state.allMode = b.dataset.m;
      for (const x of $("allMode").children) x.classList.toggle("on", x === b);
      renderAllParties();
    });
  }
  const years = Object.keys(D.history.national).sort(), last = years[years.length - 1];
  const lastYear = (r) => Object.keys(r.votes).sort().pop();
  const rows = Object.values(A).sort((a, b) => {
    const tail = (r) => (/^Muu/.test(r.abbr) ? 1 : 0);
    return tail(a) - tail(b) || (b.votes[last] || 0) - (a.votes[last] || 0) || lastYear(b).localeCompare(lastYear(a)) ||
      Math.max(...Object.values(b.votes)) - Math.max(...Object.values(a.votes));
  });
  const cell = (r, y) => {
    const v = r.votes[y]; if (!v) return `<td class="num"></td>`;
    if (state.allMode === "votes") return `<td class="num">${v.toLocaleString("fi-FI")}</td>`;
    const sh = r.share[y];
    return `<td class="num${sh != null && sh < 1 ? " dim" : ""}">${sh ? fmt(sh) : "<0,1"}</td>`;
  };
  const best = (r) => { const y = Object.keys(r.votes).sort((a, b) => r.votes[b] - r.votes[a])[0]; return `${state.allMode === "votes" ? r.votes[y].toLocaleString("fi-FI") : (r.share[y] ? fmt(r.share[y]) + " %" : "<0,1 %")} (${y})`; };
  $("allParties").innerHTML = `<thead><tr><th>Puolue</th>${years.map((y) => `<th class="num">${y}</th>`).join("")}<th class="num">Paras</th></tr></thead><tbody>${
    rows.map((r) => {
      const base = r.abbr.replace(/ \(\d{4}\)$/, ""), full = NAMES[base] && base !== "Muut" ? NAMES[base] : SMALL_NAMES[base];
      const dot = D.parties.includes(base) ? `<span class="pdot" style="background:${pc(base)}"></span>` : "";
      return `<tr><td style="white-space:nowrap">${dot}<b title="${esc(full || r.abbr)}">${esc(r.abbr)}</b>${full && full !== base ? ` <span class="fullname">${esc(full)}</span>` : ""}</td>${years.map((y) => cell(r, y)).join("")}<td class="num" style="white-space:nowrap">${best(r)}</td></tr>`;
    }).join("")}</tbody>`;
}

function renderHistory() {
  const N = D.history.national, years = Object.keys(N).sort();
  if (!state.histHidden) state.histHidden = new Set();
  legend($("histLegend"), D.parties.map((p) => ({ key: p, name: p, color: pc(p), off: state.histHidden.has(p) })),
    (k) => { state.histHidden.has(k) ? state.histHidden.delete(k) : state.histHidden.add(k); renderHistory(); });
  // Real time axis: elections in spring (~year + 0.25), plus today's poll average as a dashed "now" point.
  const ym = (s) => +s.slice(0, 4) + (+s.slice(5, 7) - 1) / 12;
  const today = new Date(), nowPos = today.getFullYear() + today.getMonth() / 12;
  const xs = [...years, "nyt"], pos = [...years.map((y) => +y + 0.25), nowPos];
  const series = D.parties.filter((p) => !state.histHidden.has(p)).map((p) => ({
    key: p, name: NAMES[p], color: pc(p), dots: true, values: [...years.map((y) => N[y][p] ?? null), D.polls.latest[p] ?? null],
  }));
  const { bands, govAt } = governmentBands(nowPos);
  lineChart($("histChart"), {
    xs, pos, bands, series, yMin: 0, height: 340, dashLast: true,
    xLabel: (y) => (y === "nyt" ? "Mittaukset nyt" : `Eduskuntavaalit ${y}`),
    ticks: [...years.map((y) => ({ pos: +y + 0.25, label: y })), { pos: nowPos, label: "nyt" }].reverse(),
    tipExtra: (i) => govRow(govAt(pos[i] - 0.01)),
  });
  renderEconomy();
  renderAllParties();
  $("govList").innerHTML = [...D.history.governments].reverse().map((g) =>
    `<div class="gov"><b>${esc(g.name)}</b><span class="y">${g.start.slice(0, 4)}–${g.end ? g.end.slice(0, 4) : ""}</span>
     <span class="ps">${g.parties.map((p) => `<span style="white-space:nowrap;margin-right:8px"><span class="pdot" style="background:${pc(p)};margin-right:4px"></span>${p}</span>`).join("")}${g.note ? `<span class="note">${esc(g.note)}</span>` : ""}</span></div>`).join("");
}

/* ---------- nav ---------- */
function setupNav() {
  const links = [...document.querySelectorAll("nav.sections a")];
  const map = new Map(links.map((a) => [a.getAttribute("href").slice(1), a]));
  const obs = new IntersectionObserver((ents) => {
    for (const e of ents) if (e.isIntersecting) {
      links.forEach((a) => a.classList.remove("active"));
      map.get(e.target.id)?.classList.add("active");
    }
  }, { rootMargin: "-45% 0px -50% 0px" });
  document.querySelectorAll("main section[id]").forEach((s) => obs.observe(s));
}
