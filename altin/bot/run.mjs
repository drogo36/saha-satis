// Sanal robot. GitHub Actions 15 dakikada bir çalıştırır, 1000 TL sanal bakiyeyle işler. Gerçek emir vermez.
import { readFile, writeFile } from "node:fs/promises";
import { DEFAULTS, WINDOW, newAccount, step, openValue } from "./strategy.mjs";
import { fetchCandles, getJSON } from "./data.mjs";

const path = new URL("state.json", import.meta.url);
const cfg = { ...DEFAULTS };
const now = Math.floor(Date.now() / 1000);
let state = null;
try { state = JSON.parse(await readFile(path, "utf8")); } catch {}
const candles = await fetchCandles(5, now);
if (candles.length < WINDOW / 2) throw new Error(`yetersiz mum: ${candles.length}`);
if (!state) state = { startedAt: now, lastT: candles.at(-2).t, acc: newAccount(cfg), curve: [], read: null };
for (let i = 1; i < candles.length; i++) {
  if (candles[i].t <= state.lastT) continue;
  const read = step(state.acc, candles, i, cfg);
  if (read) state.read = read;
  state.lastT = candles[i].t;
}
const tick = (await getJSON("https://api.btcturk.com/api/v2/ticker?pairSymbol=XAUTTRY")).data?.[0] || {};
const bid = +tick.bid || candles.at(-1).c, ask = +tick.ask || candles.at(-1).c;
const open = openValue(state.acc, bid, cfg);
state.updatedAt = now;
state.price = { bid, ask, gram: +((bid + ask) / 2 / 31.1034768).toFixed(2), candle: state.lastT };
state.value = +(state.acc.equity + open).toFixed(2);
state.openPnl = +open.toFixed(2);
state.cfg = cfg;
state.curve.push([now, state.value]);
if (state.curve.length > 500) state.curve = state.curve.filter((_, i) => i % 2 === 0);
await writeFile(path, JSON.stringify(state));
console.log(`değer ${state.value} TL, açık ${state.openPnl}, işlem ${state.acc.trades.length}`);
