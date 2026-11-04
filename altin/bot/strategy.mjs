// Altın Robotu kuralları. Geçmiş testi ve sanal robot aynı motoru kullanır, sonuçları karşılaştırılabilir.
export const WINDOW = 288;        // 72 saatlik 15 dakikalık mum
export const MIN_CANDLES = 96;
export const COOLDOWN_AFTER_EXIT = 900;
export const COOLDOWN_AFTER_STOP = 7200;
export const DEFAULTS = { capital: 1000, minProfit: 0.8, stop: 1.0, dailyLoss: 30, fee: 0.2, maxBuys: 3, spread: 0.001, slip: 0.001, compound: true };

export function percentile(values, ratio) {
  const s = [...values].sort((a, b) => a - b);
  const pos = (s.length - 1) * ratio, low = Math.floor(pos), high = Math.min(low + 1, s.length - 1);
  return s[low] + (s[high] - s[low]) * (pos - low);
}

export function rsi(closes, period = 14) {
  if (closes.length <= period) return null;
  let gains = 0, losses = 0;
  for (let i = 1; i <= period; i++) { const d = closes[i] - closes[i - 1]; gains += Math.max(d, 0); losses += Math.max(-d, 0); }
  let g = gains / period, l = losses / period;
  for (let i = period + 1; i < closes.length; i++) {
    const d = closes[i] - closes[i - 1];
    g = (g * (period - 1) + Math.max(d, 0)) / period;
    l = (l * (period - 1) + Math.max(-d, 0)) / period;
  }
  if (l === 0) return g > 0 ? 100 : 50;
  return 100 - 100 / (1 + g / l);
}

export function readMarket(candles, bid, ask, cfg) {
  if (candles.length < MIN_CANDLES || bid <= 0 || ask <= 0) {
    return { ok: false, checks: [{ name: "Yeterli fiyat geçmişi", ok: false, value: `${candles.length} mum` }] };
  }
  const w = candles.slice(-WINDOW);
  const support = percentile(w.map(c => c.l), 0.10), resistance = percentile(w.map(c => c.h), 0.90);
  const width = resistance - support;
  const position = width > 0 ? (ask - support) / width : 1;
  const fee = cfg.fee / 100;
  const net = resistance * (1 - fee) / (ask * (1 + fee)) - 1;
  const strength = rsi(w.map(c => c.c));
  const spread = (ask - bid) / ask;
  const lastClose = candles[candles.length - 2].c;
  const half = Math.floor(w.length / 2);
  const mean = a => a.reduce((s, c) => s + c.c, 0) / a.length;
  const trend = mean(w.slice(half)) / mean(w.slice(0, half)) - 1;
  const checks = [
    { name: "Fiyat aralığın alt bölgesinde", ok: position <= 0.30, value: `%${Math.round(position * 100)}` },
    { name: "Güçlü düşüş trendi yok", ok: trend >= -0.015, value: `%${(trend * 100).toFixed(1)}` },
    { name: "Destek kırılmadı", ok: ask >= support * 0.996, value: `${Math.round(support)} TL` },
    { name: "Aşırı alım yok (RSI 45 altı)", ok: strength !== null && strength <= 45, value: `${Math.round(strength ?? 0)}` },
    { name: "Düşüş yavaşladı", ok: ask > lastClose, value: `önceki kapanış ${Math.round(lastClose)}` },
    { name: "Alış-satış makası dar", ok: spread <= 0.0025, value: `%${(spread * 100).toFixed(2)}` },
    { name: "Hedefe kadar net kâr yeterli", ok: net * 100 >= cfg.minProfit, value: `%${(net * 100).toFixed(2)}` },
  ];
  return { ok: checks.every(c => c.ok), checks, support, resistance };
}

export function entryLevels(unit, resistance, cfg) {
  const floor = unit * (1 + cfg.minProfit / 100) / (1 - cfg.fee / 100);
  return { target: Math.max(resistance, floor), stopPrice: unit * (1 - cfg.stop / 100) };
}

export const newAccount = cfg => ({ equity: cfg.capital, pos: null, pending: null, waitUntil: 0, day: "", dayPnl: 0, dayBuys: 0, trades: [], peak: cfg.capital, maxDD: 0 });
const istanbulDay = t => new Date((t + 10800) * 1000).toISOString().slice(0, 10);

// i numaralı tamamlanmış mumu işler. Karar kapanışta, giriş sonraki açılışta, aynı mumda önce zarar durdurma.
export function step(acc, candles, i, cfg) {
  const now = candles[i], fee = cfg.fee / 100, half = cfg.spread / 2;
  const day = istanbulDay(now.t);
  if (acc.day !== day) { acc.day = day; acc.dayPnl = 0; acc.dayBuys = 0; }
  if (acc.pending) {
    const spend = cfg.compound ? acc.equity : cfg.capital;
    const unit = now.o * (1 + half) * (1 + fee);
    acc.pos = { qty: spend / unit, cost: spend, unit, openT: now.t, ...entryLevels(unit, acc.pending.resistance, cfg) };
    acc.pending = null;
    acc.dayBuys++;
  }
  if (acc.pos) {
    const p = acc.pos;
    let price = null, reason = null;
    if (now.l * (1 - half) <= p.stopPrice) { price = Math.min(p.stopPrice, now.o * (1 - half)) * (1 - cfg.slip); reason = "Zarar durdurma"; }
    else if (now.h * (1 - half) >= p.target) { price = p.target; reason = "Hedef"; }
    if (price === null) return null;
    const pnl = p.qty * price * (1 - fee) - p.cost;
    acc.equity += pnl; acc.dayPnl += pnl;
    acc.trades.push({ openT: p.openT, closeT: now.t, buy: p.unit, sell: price, reason, pnl, pct: pnl / p.cost * 100 });
    acc.peak = Math.max(acc.peak, acc.equity);
    acc.maxDD = Math.min(acc.maxDD, acc.equity - acc.peak);
    acc.pos = null;
    acc.waitUntil = now.t + (reason === "Hedef" ? COOLDOWN_AFTER_EXIT : COOLDOWN_AFTER_STOP);
    return null;
  }
  const read = readMarket(candles.slice(Math.max(0, i - WINDOW + 1), i + 1), now.c * (1 - half), now.c * (1 + half), cfg);
  if (now.t < acc.waitUntil || acc.dayPnl <= -cfg.dailyLoss || acc.dayBuys >= cfg.maxBuys) return read;
  if (read.ok && (!cfg.allowBuy || cfg.allowBuy(now.t))) acc.pending = { resistance: read.resistance };
  return read;
}

export function openValue(acc, price, cfg) {
  return acc.pos ? acc.pos.qty * price * (1 - cfg.fee / 100) - acc.pos.cost : 0;
}
