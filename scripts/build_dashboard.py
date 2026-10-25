"""
Build results/dashboard.html: one self-contained page (no server, no
internet) that shows every test result in the repo.

Tabs:
  - Overview: headline numbers from the latest runs
  - Judge vs humans: every item, judge scores next to both labellers',
    with filters (split, disagreements only, search) and the full text
  - Position bias: each pair judged in both orders
  - Verbosity bias: original vs padded grades
  - Runs: every judge run with cost and latency

Usage:
    python scripts/build_dashboard.py
    python scripts/build_dashboard.py --judge-run results/llm_judge_dev_<ts>.jsonl

Then open results/dashboard.html in a browser. Re-run after each new run.
By default it picks the newest llm_judge run with any scored rows (padded
verbosity runs excluded) and the newest position_bias run.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
RESULTS = REPO_ROOT / "results"
OUT_PATH = RESULTS / "dashboard.html"
AXES = ["correctness", "politeness", "completeness"]
PAD_SUFFIX = "~pad"


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def read_labels(*paths: Path) -> dict[str, dict]:
    labels = {}
    for path in paths:
        if not path.exists():
            continue
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                scores = {a: row.get(f"{a}_score_0_1_2", "").strip() for a in AXES}
                if all(v in ("0", "1", "2") for v in scores.values()):
                    labels[row["item_id"]] = {
                        **{a: int(v) for a, v in scores.items()},
                        "notes": row.get("labeller_notes", ""),
                    }
    return labels


def run_timestamp(path: Path) -> int:
    try:
        return int(path.stem.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return 0


def summarize_run(path: Path) -> dict:
    rows = read_jsonl(path)
    metas = [r["meta"] for r in rows if r.get("meta")]
    latencies = sorted(m["latency_s"] for m in metas if "latency_s" in m)
    return {
        "file": path.name,
        "when": time.strftime("%Y-%m-%d %H:%M", time.localtime(run_timestamp(path))),
        "items": len(rows),
        "scored": sum(1 for r in rows if r.get("output")),
        "padded": any(r["item_id"].endswith(PAD_SUFFIX) for r in rows),
        "cost": sum(m.get("cost_usd", 0) for m in metas),
        "calls": len(metas),
        "p50": latencies[len(latencies) // 2] if latencies else None,
    }


def judge_scores(rows: list[dict]) -> dict[str, dict]:
    out = {}
    for r in rows:
        o = r.get("output")
        out[r["item_id"]] = (
            {**{a: o[a] for a in AXES}, **{f"{a}_reason": o[f"{a}_reason"] for a in AXES}}
            if o
            else {"error": (r.get("parse_error") or "")[-300:]}
        )
    return out


def collect(judge_run: Path | None) -> dict:
    golden = read_jsonl(DATA / "golden_set.jsonl")
    splits_path = DATA / "splits.json"
    splits = json.loads(splits_path.read_text(encoding="utf-8"))["items"] if splits_path.exists() else {}
    h1 = read_labels(DATA / "labelling_sheet_labeler1_completed.csv", DATA / "labelling_sheet_labeler1_stage2.csv")
    h2 = read_labels(DATA / "labelling_sheet_labeler2_completed.csv", DATA / "labelling_sheet_labeler2_stage2.csv")

    judge_runs = sorted(RESULTS.glob("llm_judge_*.jsonl"), key=run_timestamp)
    runs = [summarize_run(p) for p in judge_runs]

    if judge_run is None:
        usable = [p for p, s in zip(judge_runs, runs) if s["scored"] and not s["padded"]]
        judge_run = usable[-1] if usable else None
    judge = judge_scores(read_jsonl(judge_run)) if judge_run else {}

    items = []
    for g in golden:
        i = g["item_id"]
        items.append(
            {
                "id": i,
                "split": splits.get(i, ""),
                "theme": g["theme"],
                "intent": g.get("challenge_type") or "",
                "message": g["customer_message"],
                "policy": g["policy_excerpt"],
                "reply": g["candidate_reply"],
                "judge": judge.get(i),
                "h1": h1.get(i),
                "h2": h2.get(i),
            }
        )

    position = None
    pos_runs = sorted(RESULTS.glob("position_bias_*.jsonl"), key=run_timestamp)
    if pos_runs:
        rows = read_jsonl(pos_runs[-1])
        pairs = {}
        for r in rows:
            pairs.setdefault(r["pair_id"], {})[r["order"]] = {
                "winner": r.get("winner_item"),
                "position": r.get("winner_position"),
                "reason": r.get("reason") or r.get("error", ""),
            }
        position = {"file": pos_runs[-1].name, "pairs": pairs}

    verbosity = None
    padded_runs = [p for p, s in zip(judge_runs, runs) if s["padded"] and s["scored"]]
    if padded_runs:
        padded = judge_scores(read_jsonl(padded_runs[-1]))
        verbosity = {
            "file": padded_runs[-1].name,
            "original_file": judge_run.name if judge_run else None,
            "items": [
                {"id": k.removesuffix(PAD_SUFFIX), "orig": judge.get(k.removesuffix(PAD_SUFFIX)), "pad": v}
                for k, v in sorted(padded.items())
            ],
        }

    return {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "judge_file": judge_run.name if judge_run else None,
        "items": items,
        "position": position,
        "verbosity": verbosity,
        "runs": runs,
    }


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SupportScore Results</title>
<style>
:root {
  --bg: #f6f7f9; --panel: #ffffff; --text: #1d2330; --muted: #5d6677;
  --border: #dde1e8; --accent: #2457c5; --accent-soft: #e6edfb;
  --good: #1f7a46; --good-bg: #e3f4ea; --mid: #8a5a00; --mid-bg: #fdf1d8;
  --bad: #b3261e; --bad-bg: #fbe4e2; --flag: #fff6d6;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #12151b; --panel: #1b2029; --text: #e6e9ef; --muted: #9aa3b2;
    --border: #2c3340; --accent: #7ea6ff; --accent-soft: #233150;
    --good: #6fd39a; --good-bg: #173226; --mid: #f0c36a; --mid-bg: #3a2f14;
    --bad: #ff8a80; --bad-bg: #3d1d1b; --flag: #332c12;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
header { padding: 20px 16px 0; max-width: 1200px; margin: 0 auto; }
h1 { margin: 0; font-size: 22px; }
.sub { color: var(--muted); font-size: 13px; margin-top: 2px; }
nav { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 16px; border-bottom: 1px solid var(--border); }
nav button { background: none; border: 0; padding: 10px 14px; font: inherit; color: var(--muted);
  cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; }
nav button.on { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
main { max-width: 1200px; margin: 0 auto; padding: 16px; }
section { display: none; } section.on { display: block; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.card { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
.card h3 { margin: 0 0 6px; font-size: 13px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .03em; }
.big { font-size: 26px; font-weight: 700; }
.verdict { margin-top: 4px; font-size: 13px; }
.ok { color: var(--good); } .warn { color: var(--mid); } .fail { color: var(--bad); }
.panel { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; margin-top: 12px; overflow-x: auto; }
.panel h2 { margin: 0 0 8px; font-size: 16px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { text-align: left; padding: 7px 8px; border-bottom: 1px solid var(--border); vertical-align: top; }
th { color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: .03em; }
tr.item { cursor: pointer; } tr.item:hover { background: var(--accent-soft); }
tr.dis { background: var(--flag); }
.s { display: inline-block; min-width: 22px; text-align: center; border-radius: 5px; padding: 0 5px; font-weight: 700; }
.s0 { background: var(--bad-bg); color: var(--bad); } .s1 { background: var(--mid-bg); color: var(--mid); }
.s2 { background: var(--good-bg); color: var(--good); } .sx { color: var(--muted); }
.trio { white-space: nowrap; } .trio .s { margin-right: 2px; }
.detail td { background: var(--bg); }
.detail .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
.detail h4 { margin: 0 0 4px; font-size: 12px; color: var(--muted); text-transform: uppercase; }
.detail p { margin: 0 0 10px; white-space: pre-wrap; }
.controls { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 10px; }
select, input[type=search], input[type=password] { font: inherit; padding: 6px 8px; border: 1px solid var(--border); border-radius: 6px;
  background: var(--panel); color: var(--text); }
input[type=search] { flex: 1; min-width: 160px; }
label.chk { display: flex; gap: 6px; align-items: center; color: var(--muted); font-size: 14px; }
.legend { color: var(--muted); font-size: 13px; margin: 6px 0 0; }
.empty { color: var(--muted); padding: 20px 0; }
.btn { font: inherit; font-size: 14px; padding: 7px 12px; border-radius: 6px; cursor: pointer;
  border: 1px solid var(--accent); background: var(--accent-soft); color: var(--accent); }
.btn:disabled { opacity: .45; cursor: default; }
code { font-size: 13px; background: var(--accent-soft); padding: 1px 5px; border-radius: 4px; }
</style>
</head>
<body>
<header>
  <h1>SupportScore: test results</h1>
  <div class="sub" id="sub"></div>
  <nav id="nav">
    <button data-tab="overview" class="on">Overview</button>
    <button data-tab="items">Judge vs humans</button>
    <button data-tab="position">Position bias</button>
    <button data-tab="verbosity">Verbosity bias</button>
    <button data-tab="runs">Runs &amp; cost</button>
    <button data-tab="run">▶ Run tests</button>
  </nav>
</header>
<main>
  <section id="overview" class="on"></section>
  <section id="items">
    <div class="controls">
      <select id="f-split"><option value="">All splits</option><option value="dev">Dev</option><option value="test">Test</option></select>
      <select id="f-who">
        <option value="h1">Compare judge with labeller 1</option>
        <option value="h2">Compare judge with labeller 2</option>
      </select>
      <label class="chk"><input type="checkbox" id="f-dis"> Only disagreements</label>
      <label class="chk"><input type="checkbox" id="f-judged" checked> Only judged items</label>
      <input type="search" id="f-q" placeholder="Search id, message, reply…">
    </div>
    <div class="panel"><table id="t-items"></table></div>
    <p class="legend">Scores are correctness · politeness · completeness (0 / 1 / 2). Highlighted rows: judge and the chosen labeller disagree on at least one axis. Click a row for the full text and reasons.</p>
  </section>
  <section id="position"></section>
  <section id="verbosity"></section>
  <section id="runs"></section>
  <section id="run">
    <div class="panel" id="run-offline">
      <h2>Run tests from this page</h2>
      <p>This page was opened as a file, so it can't start Python. Start the interface instead:</p>
      <p><code>python scripts/dashboard_server.py</code></p>
      <p class="legend">It opens <code>http://localhost:8765</code>, where this tab has working buttons.</p>
    </div>
    <div id="run-online" style="display:none">
      <div class="panel">
        <h2>Groq API key</h2>
        <div class="controls">
          <input type="password" id="r-key" placeholder="gsk_… (only needed if GROQ_API_KEY isn't set; kept in memory, never saved)" style="flex:1;min-width:240px">
        </div>
        <p class="legend" id="r-keystate"></p>
      </div>
      <div class="panel">
        <h2>Start a run</h2>
        <div class="controls">
          <select id="r-split"><option value="dev">Dev split</option><option value="test">Test split</option><option value="">All items</option></select>
          <button class="btn" data-task="judge">Run LLM judge</button>
          <button class="btn" data-task="baseline">Run keyword baseline (no key)</button>
          <button class="btn" data-task="position">Run position-bias test</button>
          <button class="btn" data-task="verbosity">Run verbosity-bias test</button>
          <button class="btn" data-task="tests">Run unit tests (no key)</button>
        </div>
        <p class="legend">One run at a time. The free tier allows roughly 100 judge calls a day: a dev-split judge run is about 43 calls, position bias 20, verbosity bias about 43.</p>
      </div>
      <div class="panel">
        <h2 id="r-title">Output</h2>
        <pre id="r-log" style="max-height:420px;overflow:auto;white-space:pre-wrap;margin:0;font-size:13px"></pre>
        <div class="controls" style="margin-top:10px"><button class="btn" id="r-reload" style="display:none">Show new results</button></div>
      </div>
    </div>
  </section>
</main>
<script>
const DATA = __DATA__;
const AXES = ["correctness", "politeness", "completeness"];
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const chip = (v) => v === undefined || v === null ? '<span class="s sx">–</span>' : `<span class="s s${v}">${v}</span>`;
const trio = (o) => !o || o.error ? (o && o.error ? '<span class="fail">error</span>' : '<span class="sx">—</span>') : `<span class="trio">${AXES.map((a) => chip(o[a])).join("")}</span>`;
const pct = (n, d) => d ? `${n}/${d} (${Math.round(100 * n / d)}%)` : "–";

function kappa(pairs) {
  const n = pairs.length; if (!n) return null;
  const cats = [0, 1, 2]; let agree = 0; const ca = {0:0,1:0,2:0}, cb = {0:0,1:0,2:0};
  for (const [a, b] of pairs) { if (a === b) agree++; ca[a]++; cb[b]++; }
  const po = agree / n, pe = cats.reduce((s, c) => s + (ca[c] / n) * (cb[c] / n), 0);
  return pe === 1 ? 1 : (po - pe) / (1 - pe);
}
const kLabel = (k) => k === null ? "–" : k.toFixed(2);
const kClass = (k) => k === null ? "" : k >= 0.6 ? "ok" : k >= 0.4 ? "warn" : "fail";

function agreement(who, items) {
  const out = {};
  for (const a of AXES) {
    const pairs = items.filter((i) => i.judge && !i.judge.error && i[who]).map((i) => [i.judge[a], i[who][a]]);
    out[a] = { n: pairs.length, same: pairs.filter(([x, y]) => x === y).length, k: kappa(pairs) };
  }
  return out;
}
function humanAgreement(items) {
  const out = {};
  for (const a of AXES) {
    const pairs = items.filter((i) => i.h1 && i.h2).map((i) => [i.h1[a], i.h2[a]]);
    out[a] = { n: pairs.length, same: pairs.filter(([x, y]) => x === y).length, k: kappa(pairs) };
  }
  return out;
}
function agreeTable(title, ag, note) {
  return `<div class="panel"><h2>${title}</h2><table><tr><th>Axis</th><th>Items</th><th>Exact agreement</th><th>Cohen's κ</th></tr>${
    AXES.map((a) => `<tr><td>${a}</td><td>${ag[a].n}</td><td>${pct(ag[a].same, ag[a].n)}</td><td class="${kClass(ag[a].k)}"><b>${kLabel(ag[a].k)}</b></td></tr>`).join("")
  }</table><p class="legend">${note}</p></div>`;
}

function positionStats() {
  const P = DATA.position; if (!P) return null;
  let both = 0, same = 0, aWins = 0, decided = 0;
  for (const v of Object.values(P.pairs)) {
    for (const o of ["AB", "BA"]) if (v[o] && v[o].position && v[o].position !== "tie") { decided++; if (v[o].position === "A") aWins++; }
    if (v.AB && v.BA && v.AB.winner && v.BA.winner) { both++; if (v.AB.winner === v.BA.winner) same++; }
  }
  return { both, same, flipped: both - same, aWins, decided };
}
function verbosityStats() {
  const V = DATA.verbosity; if (!V) return null;
  const rows = V.items.filter((r) => r.orig && !r.orig.error && r.pad && !r.pad.error);
  const by = {}; for (const a of AXES) by[a] = { up: 0, same: 0, down: 0 };
  let up = 0;
  for (const r of rows) {
    let t = 0;
    for (const a of AXES) { const d = r.pad[a] - r.orig[a]; t += d; by[a][d > 0 ? "up" : d < 0 ? "down" : "same"]++; }
    if (t > 0) up++;
  }
  return { n: rows.length, by, up, rows };
}

function renderOverview() {
  const items = DATA.items, judged = items.filter((i) => i.judge && !i.judge.error);
  const labelled = items.filter((i) => i.h1 && i.h2).length;
  const ag = agreement("h1", items), ps = positionStats(), vs = verbosityStats();
  const lastRun = DATA.runs.filter((r) => r.calls).slice(-1)[0];
  const minK = Math.min(...AXES.map((a) => ag[a].k ?? 1));
  let html = '<div class="cards">';
  html += `<div class="card"><h3>Golden set</h3><div class="big">${items.length}</div><div class="verdict ${items.length >= 150 ? "ok" : "warn"}">${items.length >= 150 ? "meets 150+ target" : `${150 - items.length} more needed for 150+`}</div></div>`;
  html += `<div class="card"><h3>Labelled by both people</h3><div class="big">${labelled}</div><div class="verdict ${labelled === items.length ? "ok" : "warn"}">${items.length - labelled} items still unlabelled</div></div>`;
  html += `<div class="card"><h3>Judge vs labeller 1 (lowest κ)</h3><div class="big ${kClass(isFinite(minK) ? minK : null)}">${judged.length ? minK.toFixed(2) : "–"}</div><div class="verdict">${judged.length} items judged · target κ ≥ 0.6</div></div>`;
  html += ps ? `<div class="card"><h3>Position bias</h3><div class="big ${ps.flipped ? "fail" : "ok"}">${pct(ps.flipped, ps.both)}</div><div class="verdict">verdicts changed after swapping order</div></div>`
             : `<div class="card"><h3>Position bias</h3><div class="big sx">not run</div><div class="verdict">python scripts/position_bias.py</div></div>`;
  html += vs ? `<div class="card"><h3>Verbosity bias</h3><div class="big ${vs.up ? "fail" : "ok"}">${pct(vs.up, vs.n)}</div><div class="verdict">padded replies whose total grade went up</div></div>`
             : `<div class="card"><h3>Verbosity bias</h3><div class="big sx">not run</div><div class="verdict">see the Verbosity bias tab</div></div>`;
  if (lastRun) html += `<div class="card"><h3>Cost per judged item</h3><div class="big">$${(lastRun.cost / lastRun.calls).toFixed(5)}</div><div class="verdict">paid-tier equivalent · p50 ${lastRun.p50 ? lastRun.p50.toFixed(2) + "s" : "–"} · $0 on free tier</div></div>`;
  html += "</div>";
  html += agreeTable("Judge vs labeller 1", ag, `Judge run: <code>${esc(DATA.judge_file || "none")}</code>. Only items both judged and labelled are counted.`);
  html += agreeTable("Labeller 1 vs labeller 2 (human agreement)", humanAgreement(items), "How often the two humans agree. The judge can't be expected to agree with humans more than they agree with each other.");
  $("#overview").innerHTML = html;
}

let openId = null;
function renderItems() {
  const split = $("#f-split").value, who = $("#f-who").value, dis = $("#f-dis").checked,
        judgedOnly = $("#f-judged").checked, q = $("#f-q").value.toLowerCase().trim();
  const isDis = (i) => i.judge && !i.judge.error && i[who] && AXES.some((a) => i.judge[a] !== i[who][a]);
  const rows = DATA.items.filter((i) =>
    (!split || i.split === split) && (!judgedOnly || i.judge) && (!dis || isDis(i)) &&
    (!q || [i.id, i.message, i.reply, i.theme].join(" ").toLowerCase().includes(q)));
  let html = `<tr><th>Item</th><th>Split</th><th>Theme</th><th>Judge</th><th>Labeller 1</th><th>Labeller 2</th><th>Customer message</th></tr>`;
  for (const i of rows) {
    html += `<tr class="item ${isDis(i) ? "dis" : ""}" data-id="${i.id}"><td><b>${i.id}</b></td><td>${i.split}</td><td>${esc(i.theme)}</td>
      <td>${trio(i.judge)}</td><td>${trio(i.h1)}</td><td>${trio(i.h2)}</td><td>${esc(i.message.slice(0, 90))}${i.message.length > 90 ? "…" : ""}</td></tr>`;
    if (openId === i.id) {
      const j = i.judge || {};
      const reasons = j.error ? `<p class="fail">${esc(j.error)}</p>` : AXES.map((a) => `<p>${chip(j[a])} <b>${a}:</b> ${esc(j[a + "_reason"] || "")}</p>`).join("");
      html += `<tr class="detail"><td colspan="7"><div class="grid">
        <div><h4>Customer message</h4><p>${esc(i.message)}</p><h4>Policy excerpt</h4><p>${esc(i.policy)}</p></div>
        <div><h4>Candidate reply</h4><p>${esc(i.reply)}</p>${i.intent ? `<h4>Author's intent</h4><p>${esc(i.intent)}</p>` : ""}</div>
        <div><h4>Judge's reasons</h4>${i.judge ? reasons : "<p>Not judged in this run.</p>"}
          <h4>Labeller notes</h4><p>1: ${esc(i.h1?.notes || "—")}\n2: ${esc(i.h2?.notes || "—")}</p></div></div></td></tr>`;
    }
  }
  if (!rows.length) html += `<tr><td colspan="7" class="empty">No items match these filters.</td></tr>`;
  $("#t-items").innerHTML = html;
}
$("#t-items").addEventListener("click", (e) => {
  const tr = e.target.closest("tr.item"); if (!tr) return;
  openId = openId === tr.dataset.id ? null : tr.dataset.id; renderItems();
});
for (const id of ["#f-split", "#f-who", "#f-dis", "#f-judged", "#f-q"]) $(id).addEventListener("input", renderItems);

function renderPosition() {
  const P = DATA.position, s = positionStats();
  if (!P) { $("#position").innerHTML = '<div class="panel empty">Not run yet. Run <code>python scripts/position_bias.py</code>, then rebuild this page.</div>'; return; }
  let html = `<div class="cards">
    <div class="card"><h3>Same reply picked after swap</h3><div class="big ${s.flipped ? "warn" : "ok"}">${pct(s.same, s.both)}</div></div>
    <div class="card"><h3>Verdict changed after swap</h3><div class="big ${s.flipped ? "fail" : "ok"}">${pct(s.flipped, s.both)}</div></div>
    <div class="card"><h3>First-shown reply won</h3><div class="big">${pct(s.aWins, s.decided)}</div><div class="verdict">no bias ≈ 50%</div></div></div>
    <div class="panel"><h2>Each pair, judged in both orders</h2><table><tr><th>Pair</th><th>Winner (original order)</th><th>Winner (swapped)</th><th>Result</th><th>Judge's reason (original order)</th></tr>`;
  for (const [id, v] of Object.entries(P.pairs).sort()) {
    const ok = v.AB?.winner && v.AB.winner === v.BA?.winner;
    html += `<tr><td><b>${esc(id)}</b></td><td>${esc(v.AB?.winner || "–")}</td><td>${esc(v.BA?.winner || "–")}</td>
      <td class="${ok ? "ok" : "fail"}">${ok ? "consistent" : "flipped"}</td><td>${esc(v.AB?.reason || "")}</td></tr>`;
  }
  html += `</table><p class="legend">Source: <code>${esc(P.file)}</code>. Each pair is two replies to the same customer message.</p></div>`;
  $("#position").innerHTML = html;
}

function renderVerbosity() {
  const V = DATA.verbosity, s = verbosityStats();
  if (!V) { $("#verbosity").innerHTML = `<div class="panel empty">Not run yet. Steps:<br>
    1. <code>python scripts/verbosity_bias.py make --split dev</code><br>
    2. <code>python -m harness.run --system llm_judge --items data/bias/verbosity_padded.jsonl</code><br>
    3. <code>python scripts/build_dashboard.py</code></div>`; return; }
  let html = `<div class="panel"><h2>Did padding change the grade?</h2><table><tr><th>Axis</th><th>Went up</th><th>Unchanged</th><th>Went down</th></tr>${
    AXES.map((a) => `<tr><td>${a}</td><td class="${s.by[a].up ? "fail" : ""}">${pct(s.by[a].up, s.n)}</td><td>${pct(s.by[a].same, s.n)}</td><td>${pct(s.by[a].down, s.n)}</td></tr>`).join("")
  }</table><p class="legend">Padded = same reply plus content-free filler. "Went up" is verbosity bias. Original: <code>${esc(V.original_file)}</code>, padded: <code>${esc(V.file)}</code>.</p></div>
  <div class="panel"><h2>Items whose grade changed</h2><table><tr><th>Item</th><th>Original</th><th>Padded</th></tr>`;
  const changed = s.rows.filter((r) => AXES.some((a) => r.orig[a] !== r.pad[a]));
  for (const r of changed) html += `<tr><td><b>${r.id}</b></td><td>${trio(r.orig)}</td><td>${trio(r.pad)}</td></tr>`;
  if (!changed.length) html += `<tr><td colspan="3" class="empty">None: padding never changed a grade.</td></tr>`;
  $("#verbosity").innerHTML = html + "</table></div>";
}

function renderRuns() {
  let html = `<div class="panel"><h2>Judge runs</h2><table><tr><th>File</th><th>When</th><th>Scored</th><th>Cost (paid-tier eq.)</th><th>Cost / 1k items</th><th>p50 latency</th></tr>`;
  for (const r of [...DATA.runs].reverse()) {
    html += `<tr><td><code>${esc(r.file)}</code>${r.padded ? " (padded)" : ""}</td><td>${r.when}</td>
      <td class="${r.scored === r.items ? "ok" : r.scored ? "warn" : "fail"}">${r.scored}/${r.items}</td>
      <td>${r.calls ? "$" + r.cost.toFixed(4) : "–"}</td><td>${r.calls ? "$" + (r.cost / r.calls * 1000).toFixed(2) : "–"}</td>
      <td>${r.p50 ? r.p50.toFixed(2) + "s" : "–"}</td></tr>`;
  }
  $("#runs").innerHTML = html + `</table><p class="legend">Runs with 0 scored items failed (missing API key or free-tier quota). Cost is what the same tokens would cost on Groq's paid tier; the free tier costs $0.</p></div>`;
}

$("#sub").textContent = `Generated ${DATA.generated} · judge run ${DATA.judge_file || "none"} · rebuild with: python scripts/build_dashboard.py`;
function showTab(tab) {
  const b = document.querySelector(`nav button[data-tab="${tab}"]`); if (!b) return;
  document.querySelectorAll("nav button").forEach((x) => x.classList.toggle("on", x === b));
  document.querySelectorAll("main section").forEach((s) => s.classList.toggle("on", s.id === tab));
  history.replaceState(null, "", "#" + tab);
}
$("#nav").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) showTab(b.dataset.tab); });
if (location.hash) showTab(location.hash.slice(1));
renderOverview(); renderItems(); renderPosition(); renderVerbosity(); renderRuns();

// ---- Run tests tab: only works when served by scripts/dashboard_server.py
if (location.protocol.startsWith("http")) {
  $("#run-offline").style.display = "none";
  $("#run-online").style.display = "block";
  let wasRunning = false;
  async function poll() {
    try {
      const s = await (await fetch("/status")).json();
      $("#r-keystate").textContent = s.key_set ? "A key is available (environment or entered above)." : "No key yet: enter one above to run the LLM judge or bias tests.";
      document.querySelectorAll("button[data-task]").forEach((b) => (b.disabled = s.running));
      $("#r-title").textContent = s.task ? `Output: ${s.task}` + (s.running ? " (running…)" : s.exit_code === 0 ? " (finished)" : ` (failed, exit ${s.exit_code})`) : "Output";
      const log = $("#r-log"), atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 20;
      log.textContent = s.log || "Nothing run yet.";
      if (atBottom) log.scrollTop = log.scrollHeight;
      if (wasRunning && !s.running) $("#r-reload").style.display = "inline-block";
      wasRunning = s.running;
    } catch (e) { $("#r-title").textContent = "Output (server not reachable)"; }
  }
  document.querySelectorAll("button[data-task]").forEach((b) => b.addEventListener("click", async () => {
    $("#r-reload").style.display = "none";
    const r = await fetch("/run", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: b.dataset.task, split: $("#r-split").value, key: $("#r-key").value.trim() }) });
    if (!r.ok) alert(await r.text());
    poll();
  }));
  $("#r-reload").addEventListener("click", () => location.reload());
  poll(); setInterval(poll, 1500);
}
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--judge-run", type=Path, default=None, help="Judge results to show (default: newest usable)")
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    html, data = render_html(args.judge_run)
    args.out.write_text(html, encoding="utf-8")
    print(f"Wrote {args.out} -- open it in a browser.")
    print(f"Judge run shown: {data['judge_file']}")


def render_html(judge_run: Path | None = None) -> tuple[str, dict]:
    data = collect(judge_run)
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return PAGE.replace("__DATA__", payload), data


if __name__ == "__main__":
    main()
