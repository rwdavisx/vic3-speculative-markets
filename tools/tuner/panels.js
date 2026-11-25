// Two views shared by the dashboard (/) and the room (/room): Tuner vs Game (windows.json, from windows.py) and the
// Key Map (keymap.json, from lab.py map). Each page gives a box: SpecPanels.vs(box), SpecPanels.km(box). Styles in panels.css.
window.SpecPanels = (() => {
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const isNum = v => typeof v === "number" && Number.isFinite(v);
  const fnum = v => Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? String(+v.toFixed(1)) : String(+v.toFixed(2));
  const kv = v => String(+(+v).toPrecision(4));  // a key's value as set, small ones kept exact
  const sgn = (v, d) => (v < 0 ? "−" : "+") + Math.abs(v).toFixed(d);
  const list = a => { a = a.filter(Boolean); return a.length > 1 ? a.slice(0, -1).join(", ") + " and " + a[a.length - 1] : a.join(""); };
  const get = u => fetch(u).then(r => r.ok ? r.json() : Promise.reject(r.status));
  const ticks = (a, b, n) => {
    const raw = (b - a) / n || 1, p = 10 ** Math.floor(Math.log10(raw)), s = [1, 2, 5, 10].map(m => m * p).find(x => x >= raw);
    const out = []; for (let v = Math.ceil(a / s) * s; v <= b + 1e-9; v += s) out.push(+v.toFixed(10)); return out;
  };
  let tip = null;
  const showTip = (e, txt) => {
    if (!tip) { tip = document.createElement("div"); tip.id = "spx-tip"; tip.hidden = true; document.body.append(tip); }
    tip.hidden = !txt; if (!txt) return;
    tip.textContent = txt;
    const w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.min(e.clientX + 16, innerWidth - w - 8) + "px";
    tip.style.top = (e.clientY + 18 + h > innerHeight ? e.clientY - h - 12 : e.clientY + 18) + "px";
  };

  // ---------- Tuner vs Game ----------
  const eraName = s => String(s).replace("-", "–");
  const span = s => String(s).split("-").map(Number);
  function gapLine(g, t, se, where) {
    if (!isNum(g)) return [`No game reading ${where} yet.`, false];
    if (!isNum(t)) return [`No tuner reading ${where}.`, false];
    const d = t - g;
    if (Math.abs(d) < 1e-9) return [`Tuner matches the game ${where}.`, false];
    const size = Math.abs(g) > 1e-9 ? `${Math.round(Math.abs(d / g) * 100)}% ${d > 0 ? "high" : "low"}` : `${fnum(Math.abs(d))} ${d > 0 ? "high" : "low"}`;
    if (!isNum(se) || se <= 0) return [`Tuner reads ${size} ${where}. The game's noise is not known.`, false];
    const far = Math.abs(d) > se;
    return [`Tuner reads ${size} ${where}; ${far ? "outside" : "within"} the game's noise.`, far];
  }
  // rows: {label, v, lo, hi, kind: "g"|"t", total}; the whole run's rows sit below a rule, on a light wash
  function vsChart(rows, unit) {
    const Wd = 430, L = 150, Rm = 40, top = 4, rh = 22, gapY = 10, nT = rows.filter(r => r.total).length;
    const yOf = i => top + i * rh + (rows[i].total && nT < rows.length ? gapY : 0);
    const y1 = yOf(rows.length - 1) + rh;
    const vals = rows.flatMap(r => [r.v, r.lo, r.hi]).filter(isNum);
    let a = vals.length ? Math.min(...vals) : 0, b = vals.length ? Math.max(...vals) : 1;
    const pad = (b - a) * .1 || Math.abs(a) * .2 || 1; a -= pad; b += pad;
    const X = v => +(L + (v - a) / (b - a) * (Wd - L - Rm)).toFixed(1);
    let s = ticks(a, b, 5).map(t => `<line class="spx-grid-l" x1="${X(t)}" x2="${X(t)}" y1="${top}" y2="${y1}"/><text x="${X(t)}" y="${y1 + 14}" text-anchor="middle">${fnum(t)}</text>`).join("");
    const t0 = rows.findIndex(r => r.total);
    if (t0 > 0) s += `<rect class="spx-wash" x="0" y="${yOf(t0) - 3}" width="${Wd}" height="${y1 - yOf(t0) + 3}"/><line class="spx-rule" x1="0" x2="${Wd}" y1="${yOf(t0) - 3}" y2="${yOf(t0) - 3}"/>`;
    rows.forEach((r, i) => {
      const y = yOf(i) + rh / 2, x = X(r.v), far = x > Wd - 70;
      s += `<text class="spx-rl${r.total ? " spx-tot" : ""}" x="0" y="${y + 4}">${esc(r.label)}</text>`;
      if (isNum(r.lo) && isNum(r.hi)) s += `<line class="spx-se" x1="${X(r.lo)}" x2="${X(r.hi)}" y1="${y}" y2="${y}"/><line class="spx-se" x1="${X(r.lo)}" x2="${X(r.lo)}" y1="${y - 5}" y2="${y + 5}"/><line class="spx-se" x1="${X(r.hi)}" x2="${X(r.hi)}" y1="${y - 5}" y2="${y + 5}"/>`;
      if (isNum(r.v)) s += `<circle class="spx-${r.kind}" cx="${x}" cy="${y}" r="${r.total ? 7 : 5.5}"/><text class="spx-vl" x="${x + (far ? -10 : 10)}" y="${y - 5}" text-anchor="${far ? "end" : "start"}">${fnum(r.v)}${unit}</text>`;
    });
    return `<svg class="spx-dots" viewBox="0 0 ${Wd} ${y1 + 20}" role="img">${s}</svg>`;
  }
  const NO_WINDOWS = "The game windows have not been run yet. Run py -3 -B tools/tuner/windows.py run, then py -3 -B tools/tuner/windows.py compare.";
  function vs(box) {
    box.classList.add("spx");
    return get("/api/windows").then(V => {
      if (!V) { box.innerHTML = `<p class="spx-empty">${NO_WINDOWS}</p>`; return; }
      const eras = V.eras || [], ms = V.metrics || [], sp = eras.map(span);
      // the whole run: the era that covers every other one
      const whole = eras.map((_, i) => eras.length > 1 && sp.every((o, j) => j === i || (sp[i][0] <= o[0] && sp[i][1] >= o[1])));
      const order = eras.map((_, i) => i).sort((i, j) => whole[i] - whole[j]);
      const cards = ms.map(m => {
        const rows = [], lines = [];
        for (const i of order) {
          const g = m.game?.[i], t = m.tuner?.[i], se = m.game_se?.[i], era = eraName(eras[i]), tot = whole[i], band = isNum(g) && isNum(se);
          rows.push({ label: tot ? `Game, whole run` : `Game ${era}`, v: g, lo: band ? g - se : NaN, hi: band ? g + se : NaN, kind: "g", total: tot },
            { label: tot ? `Tuner, whole run` : `Tuner ${era}`, v: t, kind: "t", total: tot });
          const [txt, far] = gapLine(g, t, se, tot ? `over the whole run, ${era}` : `in ${era}`);
          lines[tot ? "unshift" : "push"]({ txt, far, tot });
        }
        const n = (m.game_n || []).filter(isNum), lo = Math.min(...n), hi = Math.max(...n);
        const who = n.length ? `${lo === hi ? lo : `${lo} to ${hi}`} countries a window` : "";
        return `<div class="spx-card"><header><b>${esc(m.label || m.key)}</b><span>${esc([m.unit === "%" ? "" : m.unit, who].filter(Boolean).join(", "))}</span></header>` +
          vsChart(rows, m.unit === "%" ? "%" : "") + lines.map(l => `<p class="spx-gap${l.far ? " far" : ""}${l.tot ? " tot" : ""}">${esc(l.txt)}</p>`).join("") + "</div>";
      }).join("");
      const noGame = !ms.some(m => (m.game || []).some(isNum));
      const notes = [...(noGame ? ["No game readings yet. " + NO_WINDOWS.split(". ").slice(1).join(". ")] : []), ...(V.notes || []).filter(n => n !== V.source)];
      box.innerHTML = `<p class="spx-cap">${V.source ? esc(V.source) + " " : ""}Build ${esc(V.build || "unknown")}, made ${esc(V.made || "on an unknown date")}.</p>` +
        `<p class="spx-key"><svg width="16" height="12"><circle class="spx-g" cx="8" cy="6" r="5"/></svg> the game, its line one standard error either side <svg width="16" height="12"><circle class="spx-t" cx="8" cy="6" r="5"/></svg> the tuner. The whole run sits below the decades, on a lighter ground.</p>` +
        `<div class="spx-grid">${cards || `<p class="spx-empty">windows.json has no metrics.</p>`}</div>` + (notes.length ? `<ul class="spx-notes">${notes.map(s => `<li>${esc(s)}</li>`).join("")}</ul>` : "");
    }).catch(() => { box.innerHTML = `<p class="spx-empty">windows.json could not be read. It may be half written, or the server was started before this view; try again, or restart the server.</p>`; });
  }

  // ---------- the Key Map: one step of each key against every target ----------
  let KM = null, KMR = [];
  const outBy = (v, t) => v < t.lo ? t.lo - v : v > t.hi ? v - t.hi : 0;
  const bwf = w => Math.abs(w) >= 1 ? Math.abs(w).toFixed(1) : Math.abs(w).toFixed(2);
  function km(box) {
    box.classList.add("spx");
    return get("/api/keymap").then(K => { KM = K; drawKm(box); })
      .catch(() => { box.innerHTML = `<p class="spx-empty">keymap.json could not be read. The server may have been started before this view; restart it.</p>`; });
  }
  function drawKm(box) {
    const K = KM;
    if (!K) { box.innerHTML = `<p class="spx-empty">There is no key map yet. keymap.json has not been made.</p>`; return; }
    const T = K.targets, bw = T.map(t => (t.hi - t.lo) || 1), noise = K.noise || [];
    // ponytail: a reading counts only past both the seed noise and 0.02 band widths
    const sig = (e, j) => isNum(e) && Math.abs(e) > (noise[j] || 0) && Math.abs(e) > 0.02 * bw[j];
    const cell = (k, s, j) => {
      const e = k["effect_" + s]?.[j]; if (!sig(e, j)) return null;
      const t = T[j], d0 = outBy(t.base, t), d1 = outBy(t.base + e, t);
      return { e, w: e / bw[j], toward: d1 < d0, away: d1 > d0, leaves: d0 === 0 && d1 > 0 };
    };
    KMR = K.keys.map(k => {
      const c = { down: T.map((_, j) => cell(k, "down", j)), up: T.map((_, j) => cell(k, "up", j)) };
      const total = [...c.down, ...c.up].reduce((a, x) => a + (x ? Math.abs(x.w) : 0), 0);
      return { k, c, total, conf: ["down", "up"].filter(s => c[s].some(x => x?.toward) && c[s].some(x => x?.away)) };
    }).sort((a, b) => b.total - a.total);
    const live = KMR.filter(r => r.total > 0), dead = KMR.filter(r => !r.total);
    const score = v => isNum(v) ? (v < K.base_score ? `<b>${v.toFixed(2)}</b>` : v.toFixed(2)) : "–";
    const half = (x, ri, s, j) => {
      if (!x) return `<i class="no" data-kr="${ri}" data-ks="${s}" data-kj="${j}"></i>`;
      const col = x.toward ? "--spx-good" : x.away ? "--spx-bad" : "--spx-in", a = Math.round(15 + 70 * Math.min(1, Math.abs(x.w)));
      return `<i data-kr="${ri}" data-ks="${s}" data-kj="${j}" style="background:color-mix(in srgb, var(${col}) ${a}%, transparent)">${sgn(x.w, Math.abs(x.w) >= 1 ? 1 : 2)}</i>`;
    };
    box.innerHTML = `<p class="spx-cap">${live.length} keys move something across ${T.length} targets. Each key was stepped once down and once up on ${K.n} countries over ${K.years} years, seed ${K.seed}, made ${esc(K.made)}. ` +
      `The left half of a cell is the step down and the right half the step up, in band widths of that target. Green moves the target nearer its band, red moves it further away, blue moves it inside its band. Grey is within the noise. ` +
      `An amber edge marks a key whose step helps some targets and hurts others. The current numbers score ${K.base_score.toFixed(2)}, and lower is better; a step's score shows green when it beats that. Hover a cell for what it does.</p>` +
      `<div class="spx-kmscroll"><table class="spx-km"><thead><tr><th class="kn">Key, its steps and their scores</th>${T.map((t, j) => `<th data-kh="${j}" class="${outBy(t.base, t) ? "out" : ""}">${esc(t.label)}</th>`).join("")}</tr></thead><tbody>` +
      live.map(r => { const ri = KMR.indexOf(r), k = r.k;
        return `<tr><th class="kn${r.conf.length ? " conflict" : ""}" data-kr="${ri}">${esc(k.key)}<small>${kv(k.base)}, stepped to ${kv(k.down)} and ${kv(k.up)}</small><small>Scores ${score(k.score_down)} down, ${score(k.score_up)} up</small></th>` +
          T.map((_, j) => `<td><div class="kc">${half(r.c.down[j], ri, "down", j)}${half(r.c.up[j], ri, "up", j)}</div></td>`).join("") + "</tr>"; }).join("") + "</tbody></table></div>" +
      `<p class="spx-none">${dead.length ? `<b>${esc(list(dead.map(r => r.k.key)))}</b> ${dead.length > 1 ? "have" : "has"} no measurable effect.` : ""}` +
      (K.skipped || []).map(s => { const [a, ...b] = String(s).split(": "); return ` ${esc(a)} is left out${b.length ? "; " + esc(b.join(": ")) : ""}.`; }).join("") + "</p>";
    if (box.dataset.spxTip) return;
    box.dataset.spxTip = 1;
    box.addEventListener("mousemove", e => {
      const el = e.target.closest("[data-kr]"), th = !el && e.target.closest("[data-kh]");
      showTip(e, el ? kmTip(el) : th ? (t => `${t.label} should sit between ${fnum(t.lo)} and ${fnum(t.hi)}. The current numbers give ${fnum(t.base)}, with seed noise of ${fnum((KM.noise || [])[+th.dataset.kh] || 0)}.`)(KM.targets[+th.dataset.kh]) : "");
    });
    box.addEventListener("mouseleave", e => showTip(e, ""));
  }
  function kmTip(el) {
    const T = KM.targets, r = KMR[+el.dataset.kr], k = r?.k; if (!k) return "";
    if (el.tagName === "TH") {
      if (!r.conf.length) return `${k.key} is at ${kv(k.base)}. Its steps move the targets one way only.`;
      return r.conf.map(s => { const c = r.c[s], nm = j => T[j].label;
        return `${s === "up" ? "Raising" : "Lowering"} it brings ${list(c.map((x, j) => x?.toward ? nm(j) : null))} nearer their bands but pushes ${list(c.map((x, j) => x?.away ? nm(j) : null))} further out.`; }).join(" ");
    }
    const j = +el.dataset.kj, s = el.dataset.ks, t = T[j], to = k[s], x = r.c[s][j], verb = s === "up" ? "Raising" : "Lowering";
    if (!x) return `${verb} ${k.key} from ${kv(k.base)} to ${kv(to)} moves ${t.label} by less than its noise.`;
    const after = x.leaves ? "That takes it out of its band." : x.toward ? (outBy(t.base + x.e, t) ? "That is nearer its band." : "That brings it into its band.") : x.away ? "That is further from its band." : "It stays inside its band.";
    return `${verb} ${k.key} from ${kv(k.base)} to ${kv(to)} ${x.w > 0 ? "adds" : "takes"} ${bwf(x.w)} band widths ${x.w > 0 ? "to" : "off"} ${t.label}, ${fnum(t.base)} to ${fnum(t.base + x.e)}. ${after}`;
  }
  return { vs, km };
})();
