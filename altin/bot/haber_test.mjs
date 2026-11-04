// Haber ve ekonomik takvim, robotun sonucunu iyileştiriyor mu? Kurallar veriye bakılmadan önce sabitlendi.
// Yalnızca o ana kadar yayınlanmış veri kullanılır. Sonuç haber.json dosyasına yazılır. Gerçek emir vermez.
import { writeFile } from "node:fs/promises";
import { DEFAULTS, WINDOW, newAccount, step, openValue } from "./strategy.mjs";
import { fetchCandles } from "./data.mjs";

const sleep = ms => new Promise(r => setTimeout(r, ms));
const utc = s => Date.parse(s) / 1000;
// Resmi takvimler: federalreserve.gov, bls.gov, TCMB
const EVENTS = [
  ["ABD tarım dışı istihdam", "2026-08-07T12:30Z"], ["ABD enflasyonu", "2026-08-12T12:30Z"],
  ["ABD tarım dışı istihdam", "2026-09-04T12:30Z"], ["TCMB faiz kararı", "2026-09-10T11:00Z"],
  ["ABD enflasyonu", "2026-09-11T12:30Z"], ["Fed faiz kararı", "2026-09-16T18:00Z"],
  ["ABD tarım dışı istihdam", "2026-10-02T12:30Z"], ["ABD enflasyonu", "2026-10-14T12:30Z"],
  ["TCMB faiz kararı", "2026-10-22T11:00Z"], ["Fed faiz kararı", "2026-10-28T18:00Z"],
].map(([name, at]) => ({ name, t: utc(at) }));
const calendarClear = t => !EVENTS.some(e => t >= e.t - 86400 && t <= e.t + 7200);

const stamp = t => new Date(t * 1000).toISOString().replace(/[-:T]|\.\d+|Z/g, "").slice(0, 14);
async function gdelt(query, mode, from, to) {
  const out = new Map();
  for (let a = from; a < to; a += 7 * 86400) {
    const b = Math.min(to, a + 7 * 86400);
    const url = `https://api.gdeltproject.org/api/v2/doc/doc?query=${encodeURIComponent(query)}&mode=${mode}&format=json&startdatetime=${stamp(a)}&enddatetime=${stamp(b)}`;
    let done = false;
    for (let i = 0; i < 4 && !done; i++) {
      await sleep(6000 * (i + 1));
      try {
        const r = await fetch(url, { headers: { "User-Agent": "altin-robotu/1.0" } });
        if (!r.ok) continue;
        const j = JSON.parse(await r.text());
        for (const p of j.timeline?.[0]?.data || []) {
          const d = p.date; out.set(utc(`${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}T${d.slice(9, 11)}:${d.slice(11, 13)}Z`), +p.value);
        }
        done = true;
      } catch {}
    }
    if (!done) throw new Error("GDELT parçası alınamadı " + stamp(a));
  }
  return [...out.entries()].sort((x, y) => x[0] - y[0]);
}
// Her t için yalnızca t'den en az 1 saat önce biten saatlik kovalar kullanılır.
const mean = a => a.reduce((s, x) => s + x, 0) / a.length;
function warGate(series) {
  return t => {
    const past = series.filter(([x]) => x <= t - 3600 && x > t - 7 * 86400).map(p => p[1]);
    if (past.length < 72) return true;
    const last = past.slice(-6), base = past.slice(0, -6), m = mean(base), sd = Math.sqrt(mean(base.map(x => (x - m) ** 2)));
    return sd === 0 || (mean(last) - m) / sd <= 2;
  };
}
function toneGate(series) {
  return t => {
    const past = series.filter(([x]) => x <= t - 3600 && x > t - 7 * 86400).map(p => p[1]);
    if (past.length < 72) return true;
    return mean(past.slice(-24)) >= mean(past);
  };
}
const candles = await fetchCandles(94);
const from = candles[WINDOW].t, to = candles.at(-1).t, mid = (from + to) / 2;
function run(name, rule, allowBuy) {
  const cfg = { ...DEFAULTS, allowBuy };
  const acc = newAccount(cfg);
  for (let i = WINDOW; i < candles.length; i++) step(acc, candles, i, cfg);
  const final = acc.equity + openValue(acc, candles.at(-1).c * (1 - cfg.spread / 2), cfg);
  const part = f => +acc.trades.filter(x => f(x.closeT)).reduce((s, x) => s + x.pnl, 0).toFixed(2);
  return { name, rule, final: +final.toFixed(2), net: +(final - cfg.capital).toFixed(2), trades: acc.trades.length, wins: acc.trades.filter(x => x.pnl > 0).length,
    maxDD: +acc.maxDD.toFixed(2), half1: part(t => t < mid), half2: part(t => t >= mid), open: !!acc.pos };
}
const results = [run("Yalnızca fiyat", "Mevcut kurallar", null), run("Ekonomik takvim", "Veriden 24 saat önce ve 2 saat sonra yeni alım yok", calendarClear)];
const errors = {};
let war = null, tone = null;
const warQuery = '(war OR missile OR airstrike OR invasion OR sanctions OR ceasefire) sourcelang:english';
const goldQuery = '("gold price" OR "gold prices" OR "spot gold") sourcelang:english';
try { war = await gdelt(warQuery, "timelinevol", from - 8 * 86400, to); } catch (e) { errors.war = e.message; }
try { tone = await gdelt(goldQuery, "timelinetone", from - 8 * 86400, to); } catch (e) { errors.tone = e.message; }
if (war?.length) {
  const g = warGate(war);
  results.push(run("Savaş haberi", "Savaş haberleri son 6 saatte olağandışı artınca yeni alım yok", g));
  results.push(run("Takvim ve savaş", "İki filtre birlikte", t => calendarClear(t) && g(t)));
}
if (tone?.length) {
  const g = toneGate(tone);
  results.push(run("Altın haber tonu", "Son 24 saatin tonu 7 günlük ortalamanın altındaysa alım yok", g));
  if (war?.length) { const w = warGate(war); results.push(run("Hepsi birlikte", "Takvim, savaş ve haber tonu", t => calendarClear(t) && w(t) && g(t))); }
}
const first = candles[WINDOW], last = candles.at(-1);
const out = { at: Math.floor(Date.now() / 1000), from, to, holdPct: +((last.c / first.c * (1 - DEFAULTS.spread) * (1 - DEFAULTS.fee / 100) ** 2 - 1) * 100).toFixed(2),
  warBins: war?.length || 0, toneBins: tone?.length || 0, sample: { war: war?.slice(-2), tone: tone?.slice(-2) }, errors, results };
await writeFile(new URL("haber.json", import.meta.url), JSON.stringify(out, null, 1));
console.log(JSON.stringify(out));
