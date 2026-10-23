// Geçmiş veri testi: aynı stratejiyi son ~60 günün saatlik verisinde dener, sonucu backtest.json'a yazar.
import { readFile, writeFile } from "node:fs/promises";
import { analyze, entrySignal, manage, sizePosition } from "./strategy.mjs";

const DIR = new URL(".", import.meta.url);
const cfg = JSON.parse(await readFile(new URL("config.json", DIR), "utf8"));
const DAYS = Number(process.env.BT_DAYS || 60);
const now = Math.floor(Date.now() / 1000 / 3600) * 3600;
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function getJSON(url) { for (let i = 0; i < 3; i++) { try { const r = await fetch(url); if (r.ok) return r.json(); } catch {} await sleep(1000); } return null; }

const tick = (await getJSON("https://api.btcturk.com/api/v2/ticker"))?.data || [];
const uni = tick.filter(x => x.denominatorSymbol === cfg.quote && !cfg.exclude.includes(x.numeratorSymbol))
  .map(x => ({ pair: x.pair, tl: Number(x.volume) * Number(x.average || x.last) }))
  .filter(x => x.tl >= cfg.minDailyVolumeTRY).sort((a, b) => b.tl - a.tl).slice(0, cfg.scanTop);

const hist = {};
for (const u of uni) {
  let all = [];
  for (let k = DAYS + 8; k > 0; k -= 25) {
    const from = now - k * 86400, to = Math.min(now, from + 25 * 86400);
    const d = await getJSON(`https://graph-api.btcturk.com/v1/klines/history?symbol=${u.pair}&resolution=60&from=${from}&to=${to}`);
    if (d?.s === "ok") all = all.concat(d.t.map((t, i) => ({ t, o: +d.o[i], h: +d.h[i], l: +d.l[i], c: +d.c[i], v: +d.v[i] })));
    await sleep(150);
  }
  const seen = new Set(); all = all.filter(x => !seen.has(x.t) && seen.add(x.t)).sort((a, b) => a.t - b.t);
  if (all.length > 300) hist[u.pair] = all;
}
const pairs = Object.keys(hist);
const idx = Object.fromEntries(pairs.map(p => [p, new Map(hist[p].map((x, i) => [x.t, i]))]));
const start = now - DAYS * 86400;

let cash = cfg.startEquity; const positions = []; const trades = []; let peak = cash, maxDD = 0; const curve = [];
const priceAt = (p, t) => { const i = idx[p].get(t); return i === undefined ? null : hist[p][i].c; };
for (let t = start; t < now - 3600; t += 3600) {
  // açık pozisyonlar
  for (const pos of [...positions]) {
    const i = idx[pos.pair].get(t); if (i === undefined) continue;
    const res = manage(pos, [hist[pos.pair][i]], t + 3600, cfg, 0);
    if (res.exit) {
      const gross = pos.qty * res.price, fee = gross * cfg.feePct, pnl = gross - fee - pos.cost;
      cash += gross - fee; positions.splice(positions.indexOf(pos), 1);
      trades.push({ pair: pos.pair, openT: pos.openT, closeT: t + 3600, entry: pos.entry, exit: res.price, pnl, pnlPct: pnl / pos.cost * 100, reason: res.reason });
    }
  }
  // sinyaller (t saatinin kapanışında)
  if (positions.length < cfg.maxOpen) {
    const cands = [];
    for (const p of pairs) {
      const i = idx[p].get(t); if (i === undefined || i < 192) continue;
      const win = hist[p].slice(i - 191, i + 1);
      const an = analyze(win, { dailyPercent: (win.at(-1).c / win.at(-25).c - 1) * 100 });
      cands.push({ p, win, an });
    }
    cands.sort((a, b) => b.an.atrPct - a.an.atrPct);
    for (const c of cands.slice(0, cfg.volatileTop)) {
      if (positions.length >= cfg.maxOpen || positions.some(x => x.pair === c.p)) continue;
      if (trades.some(x => x.pair === c.p && t - x.closeT < 6 * 3600 && x.pnl < 0)) continue;
      const sig = entrySignal(c.win, c.an, cfg); if (!sig.ok) continue;
      const eq = cash + positions.reduce((s, x) => s + x.qty * (priceAt(x.pair, t) ?? x.entry), 0);
      const entry = c.an.last * (1 + cfg.slippagePct);
      const qty = sizePosition(eq, cash, entry, sig.stop, cfg); if (!qty) continue;
      const cost = qty * entry * (1 + cfg.feePct); cash -= cost;
      positions.push({ pair: c.p, openT: t + 3600, lastT: t, entry, qty, cost, stop: sig.stop, initStop: sig.stop, target: sig.target, be: false });
    }
  }
  const eq = cash + positions.reduce((s, x) => s + x.qty * (priceAt(x.pair, t) ?? x.entry), 0);
  peak = Math.max(peak, eq); maxDD = Math.max(maxDD, (peak - eq) / peak);
  if (t % 86400 === 0) curve.push({ t, e: +eq.toFixed(2) });
}
const finalEq = cash + positions.reduce((s, x) => s + x.qty * x.entry, 0);
const wins = trades.filter(x => x.pnl > 0), losses = trades.filter(x => x.pnl <= 0);
const gp = wins.reduce((s, x) => s + x.pnl, 0), gl = -losses.reduce((s, x) => s + x.pnl, 0);
// karşılaştırma: aynı paritelerde eşit ağırlıklı al-tut
const bh = pairs.map(p => { const a = hist[p].find(x => x.t >= start), b = hist[p].at(-1); return a && b ? b.c / a.c - 1 : 0; });
const out = {
  at: Math.floor(Date.now() / 1000), days: DAYS, pairs: pairs.length,
  startEquity: cfg.startEquity, finalEquity: +finalEq.toFixed(2), returnPct: +((finalEq / cfg.startEquity - 1) * 100).toFixed(2),
  trades: trades.length, winRate: trades.length ? +(wins.length / trades.length * 100).toFixed(1) : 0,
  profitFactor: gl ? +(gp / gl).toFixed(2) : null, avgWinPct: wins.length ? +(wins.reduce((s, x) => s + x.pnlPct, 0) / wins.length).toFixed(2) : 0,
  avgLossPct: losses.length ? +(losses.reduce((s, x) => s + x.pnlPct, 0) / losses.length).toFixed(2) : 0,
  maxDrawdownPct: +(maxDD * 100).toFixed(2), buyHoldPct: +(bh.reduce((s, x) => s + x, 0) / (bh.length || 1) * 100).toFixed(2),
  byReason: trades.reduce((m, x) => (m[x.reason] = (m[x.reason] || 0) + 1, m), {}),
  curve, lastTrades: trades.slice(-40).reverse(),
};
await writeFile(new URL("backtest.json", DIR), JSON.stringify(out, null, 1));
console.log(JSON.stringify({ ...out, curve: undefined, lastTrades: undefined }, null, 1));
