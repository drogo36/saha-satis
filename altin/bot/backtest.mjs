// 1000 TL geçmiş testi. Sonucu backtest.json dosyasına yazar. Gerçek emir vermez.
import { writeFile } from "node:fs/promises";
import { DEFAULTS, WINDOW, newAccount, step, openValue } from "./strategy.mjs";
import { fetchCandles } from "./data.mjs";

const DAYS = Number(process.env.BT_DAYS || 90);
const cfg = { ...DEFAULTS };
const candles = await fetchCandles(DAYS + 4);
if (candles.length <= WINDOW + 10) throw new Error(`yetersiz mum: ${candles.length}`);
const acc = newAccount(cfg);
const curve = [];
for (let i = WINDOW; i < candles.length; i++) {
  step(acc, candles, i, cfg);
  if ((i - WINDOW) % 48 === 0) curve.push([candles[i].t, +acc.equity.toFixed(2)]);
}
const first = candles[WINDOW], last = candles.at(-1);
const open = openValue(acc, last.c * (1 - cfg.spread / 2), cfg);
const final = acc.equity + open;
const wins = acc.trades.filter(t => t.pnl > 0), losses = acc.trades.filter(t => t.pnl <= 0);
const sum = a => a.reduce((s, t) => s + t.pnl, 0);
const out = {
  at: Math.floor(Date.now() / 1000), source: "BtcTurk XAUT/TRY 15 dk", candles: candles.length - WINDOW,
  from: first.t, to: last.t, days: (last.t - first.t) / 86400, start: cfg.capital, final: +final.toFixed(2),
  net: +(final - cfg.capital).toFixed(2), pct: +((final / cfg.capital - 1) * 100).toFixed(2),
  trades: acc.trades.length, wins: wins.length, losses: losses.length,
  profitFactor: losses.length && sum(losses) ? +(sum(wins) / -sum(losses)).toFixed(2) : null,
  maxDD: +acc.maxDD.toFixed(2), holdPct: +((last.c / first.c * (1 - cfg.spread) * (1 - cfg.fee / 100) ** 2 - 1) * 100).toFixed(2),
  stops: acc.trades.filter(t => t.reason !== "Hedef").length, targets: acc.trades.filter(t => t.reason === "Hedef").length,
  open: !!acc.pos, openPnl: +open.toFixed(2), curve: [...curve, [last.t, +final.toFixed(2)]],
  list: acc.trades.slice(-30).reverse().map(t => ({ ...t, buy: +t.buy.toFixed(2), sell: +t.sell.toFixed(2), pnl: +t.pnl.toFixed(2), pct: +t.pct.toFixed(2) })),
};
await writeFile(new URL("backtest.json", import.meta.url), JSON.stringify(out, null, 1));
console.log(JSON.stringify({ ...out, curve: undefined, list: undefined }));
