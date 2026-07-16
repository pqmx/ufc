// Dashboard client: connects to /ws, renders FightState pushes, and sends
// fighter-name overrides back to the server.

const statusEl = document.getElementById("status");
const roundNumEl = document.getElementById("round-num");
const clockEl = document.getElementById("clock");
const totalRedEl = document.getElementById("total-red");
const totalBlueEl = document.getElementById("total-blue");
const tallyRedEl = document.getElementById("tally-red");
const tallyBlueEl = document.getElementById("tally-blue");
const nameRedEl = document.getElementById("name-red");
const nameBlueEl = document.getElementById("name-blue");
const scorecardBody = document.getElementById("scorecard-body");
const feedEl = document.getElementById("feed");

let ws = null;
const editing = { red: false, blue: false };

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = () => setStatus("live", "live");
  ws.onclose = () => {
    setStatus("disconnected — retrying…", "error");
    setTimeout(connect, 1500);
  };
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "state") render(msg.state);
  };
}

function setStatus(text, cls) {
  statusEl.textContent = text;
  statusEl.className = "status" + (cls ? " " + cls : "");
}

function tallyItems(f) {
  return `
    <li>${f.sig_strikes} sig. strikes</li>
    <li>${f.takedowns} takedowns</li>
    <li>${Math.floor(f.control_seconds / 60)}:${String(f.control_seconds % 60).padStart(2, "0")} control</li>
  `;
}

function render(s) {
  if (s.status === "capturing") setStatus("live", "live");
  else if (s.status === "error") setStatus("error", "error");

  roundNumEl.textContent = s.current_round;
  clockEl.textContent = s.clock || "--:--";

  totalRedEl.textContent = s.totals.red;
  totalBlueEl.textContent = s.totals.blue;
  tallyRedEl.innerHTML = tallyItems(s.red);
  tallyBlueEl.innerHTML = tallyItems(s.blue);

  if (!editing.red && document.activeElement !== nameRedEl) nameRedEl.value = s.red.name;
  if (!editing.blue && document.activeElement !== nameBlueEl) nameBlueEl.value = s.blue.name;

  renderScorecard(s);
  renderFeed(s);
}

// Provisional lean for the round currently in progress, from the live tallies.
// Judge (LLM) still owns the final number when the round rolls over.
function projectRound(s) {
  const w = (f) => f.sig_strikes + f.takedowns * 3 + Math.floor(f.control_seconds / 30);
  const r = w(s.red), b = w(s.blue);
  if (r === 0 && b === 0) return { red: "–", blue: "–", note: "no scoring action yet" };
  if (r === b) return { red: 10, blue: 10, note: "even so far" };
  return r > b
    ? { red: 10, blue: 9, note: "red leading" }
    : { red: 9, blue: 10, note: "blue leading" };
}

function renderScorecard(s) {
  const nameR = s.red.name || "Red";
  const nameB = s.blue.name || "Blue";
  const rows = [];

  // Completed (judged) rounds.
  const finalized = new Set(s.scorecard.map((r) => r.round));
  for (const r of s.scorecard) {
    rows.push(`
      <tr>
        <td>R${r.round}</td>
        <td class="num c-red">${r.red}</td>
        <td class="num c-blue">${r.blue}</td>
        <td>${escapeHtml(r.note)}</td>
      </tr>`);
  }

  // Live in-progress row for the current round (until the judge finalizes it).
  if (!finalized.has(s.current_round)) {
    const p = projectRound(s);
    rows.push(`
      <tr class="live">
        <td>R${s.current_round} · live</td>
        <td class="num c-red">${p.red}</td>
        <td class="num c-blue">${p.blue}</td>
        <td>${escapeHtml(p.note)}</td>
      </tr>`);
  }

  if (s.scorecard.length) {
    rows.push(`
      <tr>
        <td><strong>Total</strong></td>
        <td class="num c-red"><strong>${s.totals.red}</strong></td>
        <td class="num c-blue"><strong>${s.totals.blue}</strong></td>
        <td>${escapeHtml(nameR)} vs ${escapeHtml(nameB)}</td>
      </tr>`);
  }

  scorecardBody.innerHTML = rows.join("");
}

function renderFeed(s) {
  feedEl.innerHTML = s.feed
    .map((shot) => {
      const t = new Date(shot.ts * 1000).toLocaleTimeString();
      const cls = shot.corner + (shot.rocked ? " rocked" : "");
      const badge = shot.rocked ? `<span class="rocked-badge">ROCKED</span>` : "";
      return `
        <li class="${cls}">
          <div class="shot-text">${escapeHtml(shot.text)}${badge}</div>
          <div class="shot-meta">R${shot.round} · ${escapeHtml(shot.clock || "")} · ${shot.kind} · ${t}</div>
        </li>`;
    })
    .join("");
}

function escapeHtml(str) {
  return String(str || "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function wireNameInput(el, corner) {
  el.addEventListener("focus", () => (editing[corner] = true));
  el.addEventListener("blur", () => {
    editing[corner] = false;
    sendName(corner, el.value);
  });
  el.addEventListener("keydown", (e) => {
    if (e.key === "Enter") el.blur();
  });
}

function sendName(corner, name) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "set_name", corner, name }));
  }
}

wireNameInput(nameRedEl, "red");
wireNameInput(nameBlueEl, "blue");
connect();
