// Kripto Radar — her çalıştırmada: piyasayı tara, açık pozisyonları yönet, yeni sinyalleri sanal olarak işle.
// Çalıştırma: node bot/run.mjs   (GitHub Actions 15 dakikada bir çalıştırır)
import { readFile, writeFile } from "node:fs/promises";
import { analyze, entrySignal, manage, sizePosition, fmt } from "./strategy.mjs";

const DIR = new URL(".", import.meta.url);
const cfg = JSON.parse(await readFile(new URL("config.json", DIR), "utf8"));
const statePath = new URL("state.json", DIR), scanPath = new URL("scan.json", DIR);
const now = Math.floor(Date.now() / 1000);
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function getJSON(url, tries = 3) {
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(url, { headers: { "User-Agent": "kripto-radar/1.0" } });
      if (r.ok) return await r.json();
      if (r.status === 429) await sleep(2000 * (i + 1)); else await sleep(500);
    } catch { await sleep(800); }
  }
  throw new Error("veri alınamadı: " + url);
}
async function candles(pair, hours = 192) {
  const d = await getJSON(`https://graph-api.btcturk.com/v1/klines/history?symbol=${pair}&resolution=60&from=${now - hours * 3600}&to=${now}`);
  if (d.s !== "ok" || !d.t) return [];
  return d.t.map((t, i) => ({ t, o: +d.o[i], h: +d.h[i], l: +d.l[i], c: +d.c[i], v: +d.v[i] }));
}
async function notify(title, msg, tags = "chart_with_upwards_trend") {
  if (!cfg.ntfyTopic) return;
  try { await fetch(`https://ntfy.sh/${cfg.ntfyTopic}`, { method: "POST", headers: { Title: encodeURIComponent(title), Tags: tags, "Content-Type": "text/plain; charset=utf-8", "X-Title": title }, body: msg }); } catch {}
}

let state;
try { state = JSON.parse(await readFile(statePath, "utf8")); }
catch { state = { mode: cfg.mode, startEquity: cfg.startEquity, cash: cfg.startEquity, positions: [], trades: [], equityCurve: [], startedAt: now, runs: 0 }; }

// 1) Tarama evreni: TL pariteleri, hacim filtresi
const tick = (await getJSON("https://api.btcturk.com/api/v2/ticker")).data || [];
const tmap = Object.fromEntries(tick.map(x => [x.pair, x]));
const universe = tick
  .filter(x => x.denominatorSymbol === cfg.quote && !cfg.exclude.includes(x.numeratorSymbol))
  .map(x => ({ ...x, tl: Number(x.volume) * Number(x.average || x.last) }))
  .filter(x => x.tl >= cfg.minDailyVolumeTRY)
  .sort((a, b) => b.tl - a.tl)
  .slice(0, cfg.scanTop);

// 2) Açık pozisyonları da kesin tara
const pairs = [...new Set([...universe.map(x => x.pair), ...state.positions.map(p => p.pair)])];
const data = {};
for (const p of pairs) {
  try { data[p] = await candles(p); } catch { data[p] = []; }
  await sleep(120);
}
const closed = c => c.filter(x => x.t + 3600 <= now); // sadece kapanmış mumlar

// 3) Pozisyon yönetimi
const events = [];
for (const pos of [...state.positions]) {
  const c = data[pos.pair] || [];
  const res = manage(pos, c, now, cfg, Number(tmap[pos.pair]?.last) || 0);
  if (res.exit) {
    const gross = pos.qty * res.price;
    const fee = gross * cfg.feePct;
    const pnl = gross - fee - pos.cost;
    state.cash += gross - fee;
    state.positions = state.positions.filter(x => x !== pos);
    const tr = { pair: pos.pair, openT: pos.openT, closeT: now, entry: pos.entry, exit: res.price, qty: pos.qty, pnl, pnlPct: pnl / pos.cost * 100, reason: res.reason, why: pos.why };
    state.trades.unshift(tr);
    events.push(tr);
    await notify(`${pnl >= 0 ? "✅" : "🔻"} ${pos.pair} kapandı: ${pnl >= 0 ? "+" : ""}${fmt(pnl)} TL`, `${res.reason} · giriş ${fmt(pos.entry)} → çıkış ${fmt(res.price)} (${tr.pnlPct.toFixed(1)}%)`, pnl >= 0 ? "white_check_mark" : "small_red_triangle_down");
  }
}

// 4) Analiz + sinyal
const lastPrice = p => Number(tmap[p]?.last) || (data[p]?.at(-1)?.c ?? 0);
const posValue = () => state.positions.reduce((s, p) => s + p.qty * lastPrice(p.pair), 0);
const scan = [];
for (const u of universe) {
  const c = closed(data[u.pair] || []);
  if (c.length < 60) continue;
  const an = analyze(c, u);
  an.last = Number(u.last) || an.last; // anlık fiyat
  scan.push({ pair: u.pair, sym: u.numeratorSymbol, last: an.last, dailyPercent: an.dailyPercent, volTL: Math.round(u.tl), atrPct: +an.atrPct.toFixed(2), rsi: +an.rsi.toFixed(1),
    supports: an.supports.map(l => ({ p: l.price, n: l.touches })), resistances: an.resistances.map(l => ({ p: l.price, n: l.touches })), an, c });
}
scan.sort((a, b) => b.atrPct - a.atrPct);
const volatile = scan.slice(0, cfg.volatileTop);
for (const s of volatile) {
  const sig = entrySignal(s.c, s.an, cfg);
  s.signal = sig.ok ? "AL" : "";
  s.why = sig.why;
  if (!sig.ok) continue;
  if (state.positions.length >= cfg.maxOpen || state.positions.some(p => p.pair === s.pair)) continue;
  if (state.trades.some(t => t.pair === s.pair && now - t.closeT < 6 * 3600 && t.pnl < 0)) { s.why += " · son 6 saatte zarar edildi, bekleniyor"; continue; }
  const equity = state.cash + posValue();
  const entry = s.last * (1 + cfg.slippagePct);
  const qty = sizePosition(equity, state.cash, entry, sig.stop, cfg);
  if (!qty) continue;
  const cost = qty * entry * (1 + cfg.feePct);
  state.cash -= cost;
  const pos = { pair: s.pair, sym: s.sym, openT: now, lastT: s.c.at(-1).t, entry, qty, cost, stop: sig.stop, initStop: sig.stop, target: sig.target, rr: sig.rr, why: sig.why, be: false };
  state.positions.push(pos);
  events.push({ open: pos });
  await notify(`🟢 SANAL ALIM: ${s.sym}/TL @ ${fmt(entry)}`, `${sig.why}\nStop ${fmt(sig.stop)} · Hedef ${fmt(sig.target)}\nTutar ${fmt(qty * entry)} TL (sanal)`, "green_circle");
}

// 5) Kayıt
const equity = state.cash + posValue();
state.equity = equity; state.lastRun = now; state.runs = (state.runs || 0) + 1; state.mode = cfg.mode;
const dayKey = new Date(now * 1000).toISOString().slice(0, 13); // saatlik nokta
if (!state.equityCurve.length || state.equityCurve.at(-1).k !== dayKey) state.equityCurve.push({ k: dayKey, t: now, e: +equity.toFixed(2) });
else state.equityCurve.at(-1).e = +equity.toFixed(2);
state.equityCurve = state.equityCurve.slice(-24 * 60);
state.trades = state.trades.slice(0, 500);
state.positions.forEach(p => { p.now = lastPrice(p.pair); });

await writeFile(statePath, JSON.stringify(state, null, 1));
await writeFile(scanPath, JSON.stringify({ at: now, count: scan.length, list: volatile.map(({ an, c, ...rest }) => rest) }, null, 1));
console.log(`çalıştı · ${scan.length} parite tarandı · açık ${state.positions.length} · olay ${events.length} · özsermaye ${equity.toFixed(2)} TL`);
