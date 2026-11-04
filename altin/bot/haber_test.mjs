// Haber ve ekonomik takvim, robotun sonucunu iyileştiriyor mu? Kurallar veriye bakılmadan önce sabitlendi.
// Yalnızca o ana kadar yayınlanmış veri kullanılır. Sonuç haber.json dosyasına yazılır. Gerçek emir vermez.
import { writeFile } from "node:fs/promises";
import { inflateRawSync } from "node:zlib";
import { pathToFileURL } from "node:url";
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

// GDELT 2.0 ham dosyaları: her 15 dakikada bir yayınlanır. Sorgu servisi sınır koyduğu için doğrudan dosyalar okunur.
const BASE = "http://data.gdeltproject.org/gdeltv2/";
const stamp = t => new Date(t * 1000).toISOString().replace(/[-:T]|\.\d+|Z/g, "").slice(0, 14);
export function unzipOne(buf) {
  let e = buf.length - 22;
  while (e >= 0 && buf.readUInt32LE(e) !== 0x06054b50) e--;
  if (e < 0) throw new Error("zip sonu yok");
  const c = buf.readUInt32LE(e + 16);
  if (buf.readUInt32LE(c) !== 0x02014b50) throw new Error("zip dizini yok");
  const method = buf.readUInt16LE(c + 10), size = buf.readUInt32LE(c + 20), off = buf.readUInt32LE(c + 42);
  const start = off + 30 + buf.readUInt16LE(off + 26) + buf.readUInt16LE(off + 28);
  const body = buf.subarray(start, start + size);
  return method === 0 ? body : inflateRawSync(body);
}
// Hataları sayar; eksik dosya oranı sonuçla birlikte raporlanır.
async function readFiles(times, suffix, onText, deadline, workers = 8) {
  let next = 0, ok = 0, missing = 0, failed = 0, bytes = 0, late = false;
  async function worker() {
    while (next < times.length) {
      if (Date.now() > deadline) { late = true; return; }
      const t = times[next++];
      for (let i = 0; i < 3; i++) {
        try {
          const r = await fetch(`${BASE}${stamp(t)}${suffix}`, { headers: { "User-Agent": "altin-robotu/1.0" }, signal: AbortSignal.timeout(60000) });
          if (r.status === 404) { missing++; break; }
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          const buf = Buffer.from(await r.arrayBuffer());
          bytes += buf.length;
          onText(t, unzipOne(buf).toString("latin1"));
          ok++;
          break;
        } catch { if (i === 2) failed++; else await sleep(2000 * (i + 1)); }
      }
    }
  }
  await Promise.all(Array.from({ length: workers }, worker));
  return { files: times.length, ok, missing, failed, late, mb: Math.round(bytes / 1e6) };
}
const hour = t => t - t % 3600;
const quarters = (from, to, step = 900) => { const out = []; for (let t = from - from % step; t <= to; t += step) out.push(t); return out; };
// Savaş: askerî güç ve kitlesel şiddet olaylarının (CAMEO 19 ve 20) saatlik haber payı, yüzde.
export function warLine(text, add) {
  for (const line of text.split("\n")) {
    if (!line) continue;
    const f = line.split("\t"), n = +f[33] || 0;
    add(n, f[28] === "19" || f[28] === "20" ? n : 0);
  }
}
async function warSeries(from, to, deadline) {
  const bins = new Map();
  const info = await readFiles(quarters(from, to), ".export.CSV.zip", (t, text) => {
    const b = bins.get(hour(t)) || [0, 0];
    warLine(text, (all, war) => { b[0] += all; b[1] += war; });
    bins.set(hour(t), b);
  }, deadline, 12);
  return { info, series: [...bins.entries()].filter(([, b]) => b[0] > 0).map(([t, b]) => [t, b[1] / b[0] * 100]).sort((x, y) => x[0] - y[0]) };
}
// Ton: başlığında veya adresinde altın fiyatı geçen İngilizce haberlerin ortalama tonu (GKG).
const GOLD = /gold[-_ ]?prices?|spot[-_ ]?gold/gi;
export function goldTones(text, add) {
  let last = -1;
  for (const m of text.matchAll(GOLD)) {
    const a = text.lastIndexOf("\n", m.index) + 1;
    if (a === last) continue;
    last = a;
    const z = text.indexOf("\n", m.index);
    const f = text.slice(a, z < 0 ? text.length : z).split("\t");
    const tone = parseFloat(f[15]);
    if (Number.isFinite(tone)) add(tone);
  }
}
async function toneSeries(from, to, deadline) {
  const bins = new Map();
  const info = await readFiles(quarters(from, to, 1800), ".gkg.csv.zip", (t, text) => {
    const b = bins.get(hour(t)) || [0, 0];
    goldTones(text, x => { b[0]++; b[1] += x; });
    bins.set(hour(t), b);
  }, deadline, 8);
  return { info, series: [...bins.entries()].filter(([, b]) => b[0] > 0).map(([t, b]) => [t, b[1] / b[0]]).sort((x, y) => x[0] - y[0]) };
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
if (import.meta.url === pathToFileURL(process.argv[1]).href) {
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
const started = Date.now();
const coverage = {};
const enough = i => i.ok >= i.files * 0.9;
try {
  const w = await warSeries(from - 8 * 86400, to, started + 25 * 60000);
  coverage.war = w.info; console.log("savaş", JSON.stringify(w.info), w.series.length);
  if (enough(w.info)) war = w.series; else errors.war = "Savaş verisi eksik kaldı";
} catch (e) { errors.war = e.message; }
try {
  const g = await toneSeries(from - 8 * 86400, to, started + 70 * 60000);
  coverage.tone = g.info; console.log("ton", JSON.stringify(g.info), g.series.length);
  if (enough(g.info)) tone = g.series; else errors.tone = "Ton verisi eksik kaldı";
} catch (e) { errors.tone = e.message; }
if (war?.length) {
  const g = warGate(war);
  results.push(run("Savaş haberi", "Askerî çatışma haberlerinin payı son 6 saatte olağandışı artınca yeni alım yok", g));
  results.push(run("Takvim ve savaş", "İki filtre birlikte", t => calendarClear(t) && g(t)));
}
if (tone?.length) {
  const g = toneGate(tone);
  results.push(run("Altın haber tonu", "Son 24 saatin tonu 7 günlük ortalamanın altındaysa alım yok", g));
  if (war?.length) { const w = warGate(war); results.push(run("Hepsi birlikte", "Takvim, savaş ve haber tonu", t => calendarClear(t) && w(t) && g(t))); }
}
// Filtrelerin gerçekten devreye girip girmediğini ölçer.
const base = (() => { const acc = newAccount(DEFAULTS); for (let i = WINDOW; i < candles.length; i++) step(acc, candles, i, DEFAULTS); return acc.trades; })();
const gateStats = g => {
  const inRange = candles.slice(WINDOW);
  return { blockedPct: +(inRange.filter(c => !g(c.t)).length / inRange.length * 100).toFixed(1), blockedEntries: base.filter(x => !g(x.openT)).length, entries: base.length };
};
const gates = { calendar: gateStats(calendarClear) };
if (war?.length) gates.war = gateStats(warGate(war));
if (tone?.length) gates.tone = gateStats(toneGate(tone));
const first = candles[WINDOW], last = candles.at(-1);
const out = { at: Math.floor(Date.now() / 1000), from, to, holdPct: +((last.c / first.c * (1 - DEFAULTS.spread) * (1 - DEFAULTS.fee / 100) ** 2 - 1) * 100).toFixed(2),
  coverage, gates, warBins: war?.length || 0, toneBins: tone?.length || 0, sample: { war: war?.slice(-2), tone: tone?.slice(-2) }, errors, results };
await writeFile(new URL("haber.json", import.meta.url), JSON.stringify(out, null, 1));
console.log(JSON.stringify(out));
}
