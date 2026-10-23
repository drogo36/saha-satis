// Kripto Radar — saf strateji fonksiyonları (ağ yok, test edilebilir)
// Mumlar: [{t,o,h,l,c,v}] eskiden yeniye, 1 saatlik.

export function ema(values, n) {
  const k = 2 / (n + 1); const out = []; let prev;
  values.forEach((v, i) => { prev = i === 0 ? v : v * k + prev * (1 - k); out.push(prev); });
  return out;
}

export function rsi(closes, n = 14) {
  if (closes.length <= n) return 50;
  let g = 0, l = 0;
  for (let i = 1; i <= n; i++) { const d = closes[i] - closes[i - 1]; if (d > 0) g += d; else l -= d; }
  g /= n; l /= n;
  for (let i = n + 1; i < closes.length; i++) {
    const d = closes[i] - closes[i - 1];
    g = (g * (n - 1) + Math.max(d, 0)) / n; l = (l * (n - 1) + Math.max(-d, 0)) / n;
  }
  return l === 0 ? 100 : 100 - 100 / (1 + g / l);
}

export function atr(c, n = 14) {
  if (c.length < 2) return 0;
  const tr = c.slice(1).map((x, i) => Math.max(x.h - x.l, Math.abs(x.h - c[i].c), Math.abs(x.l - c[i].c)));
  let a = tr.slice(0, n).reduce((s, v) => s + v, 0) / Math.min(n, tr.length);
  for (let i = n; i < tr.length; i++) a = (a * (n - 1) + tr[i]) / n;
  return a;
}

// Pivot dip/tepe noktalarını bul, ATR'nin bir kısmı kadar yakın olanları tek seviyede topla.
export function levels(c, a, win = 3) {
  const piv = [];
  for (let i = win; i < c.length - win; i++) {
    let hi = true, lo = true;
    for (let j = i - win; j <= i + win; j++) {
      if (j === i) continue;
      if (c[j].h >= c[i].h) hi = false;
      if (c[j].l <= c[i].l) lo = false;
    }
    if (hi) piv.push({ p: c[i].h, i });
    if (lo) piv.push({ p: c[i].l, i });
  }
  piv.sort((x, y) => x.p - y.p);
  const tol = Math.max(a * 0.6, 1e-12); const out = [];
  for (const p of piv) {
    const last = out[out.length - 1];
    if (last && p.p - last.max <= tol) { last.sum += p.p; last.n++; last.max = p.p; last.lastI = Math.max(last.lastI, p.i); }
    else out.push({ sum: p.p, n: 1, max: p.p, lastI: p.i });
  }
  return out.map(l => ({ price: l.sum / l.n, touches: l.n, recency: l.lastI }));
}

export function analyze(candles, ticker = {}) {
  const c = candles; const closes = c.map(x => x.c);
  const last = closes[closes.length - 1];
  const a = atr(c, 14);
  const lv = levels(c, a);
  const supports = lv.filter(l => l.price < last).sort((x, y) => y.price - x.price);
  const resistances = lv.filter(l => l.price > last).sort((x, y) => x.price - y.price);
  const e50 = ema(closes, 50);
  return {
    last, atr: a, atrPct: last ? (a / last) * 100 : 0,
    rsi: rsi(closes, 14), ema50: e50[e50.length - 1],
    ema50Slope: e50.length > 6 ? (e50[e50.length - 1] - e50[e50.length - 7]) / e50[e50.length - 7] * 100 : 0,
    supports: supports.slice(0, 3), resistances: resistances.slice(0, 3),
    dailyPercent: Number(ticker.dailyPercent) || 0,
  };
}

// Giriş kuralı: güçlü bir desteğe yakın, desteğe dokunup yeşil kapanmış, RSI düşük bölgede, hedef direnç yeterince uzak.
export function entrySignal(candles, an, cfg) {
  if (cfg.strategy === "kirilim") return breakoutSignal(candles, an, cfg);
  const s = an.supports.find(l => l.touches >= 2);
  if (!s) return { ok: false, why: "güçlü destek yok" };
  const r = an.resistances.find(l => l.price > an.last + an.atr * 0.8);
  if (!r) return { ok: false, why: "üstte direnç yok" };
  const a = an.atr;
  if (an.last > s.price + a * 0.8) return { ok: false, why: "desteğe uzak" };
  const recent = candles.slice(-3);
  const touched = recent.some(x => x.l <= s.price + a * 0.35);
  const lastC = candles[candles.length - 1];
  if (!touched) return { ok: false, why: "destek test edilmedi" };
  if (!(lastC.c > lastC.o)) return { ok: false, why: "dönüş mumu yok" };
  if (an.rsi < cfg.rsiMin || an.rsi > cfg.rsiMax) return { ok: false, why: `RSI ${an.rsi.toFixed(0)}` };
  if (an.dailyPercent < -15) return { ok: false, why: "sert düşüşte" };
  if (an.ema50Slope < (cfg.minEmaSlope ?? -1)) return { ok: false, why: "düşüş trendi" };
  const entry = an.last;
  const stop = s.price - a * 0.7;
  const risk = entry - stop;
  const target = Math.min(r.price - a * 0.2, entry + risk * (cfg.maxRR || 2.5));
  const reward = target - entry;
  if (risk <= 0 || reward <= 0) return { ok: false, why: "geçersiz seviye" };
  const rr = reward / risk;
  if (rr < cfg.minRewardRisk) return { ok: false, why: `kazanç/risk ${rr.toFixed(1)}` };
  return { ok: true, entry, stop, target, rr, support: s.price, resistance: r.price, why: `destek ${fmt(s.price)} (${s.touches} dokunuş), hedef ${fmt(r.price)}, RSI ${an.rsi.toFixed(0)}, K/R ${rr.toFixed(1)}` };
}

// Kırılım: son kapanan mum güçlü bir direnci hacimle yukarı kırdıysa al; stop kırılan seviyenin altında.
export function breakoutSignal(c, an, cfg) {
  const a = an.atr, x = c[c.length - 1], prev = c.slice(-50, -1);
  const lv = levels(c.slice(0, -1), a).filter(l => l.touches >= 2 && l.price < x.c && l.price > c[c.length - 2].c * 0.995 - a * 0.1);
  const broke = lv.find(l => c[c.length - 2].c <= l.price + a * 0.1 && x.c > l.price + a * 0.25);
  if (!broke) return { ok: false, why: "kırılım yok" };
  const avgV = prev.reduce((s, y) => s + y.v, 0) / prev.length;
  if (x.v < avgV * (cfg.volMult || 1.5)) return { ok: false, why: "hacim zayıf" };
  if (an.ema50Slope < 0) return { ok: false, why: "trend aşağı" };
  if (an.rsi > 78) return { ok: false, why: "aşırı alım" };
  const entry = an.last, stop = broke.price - a * (cfg.stopAtr || 0.8), risk = entry - stop;
  if (risk <= 0 || risk / entry > 0.08) return { ok: false, why: "stop çok uzak" };
  const target = entry + risk * (cfg.maxRR || 2.5);
  return { ok: true, entry, stop, target, rr: (target - entry) / risk, support: broke.price, resistance: target, why: `${fmt(broke.price)} direnci ${(x.v / avgV).toFixed(1)}x hacimle kırıldı, RSI ${an.rsi.toFixed(0)}` };
}

// Açık pozisyonu son çalıştırmadan beri gelen mumlarla güncelle. Aynı mumda hem stop hem hedef varsa temkinli olarak stop sayılır.
export function manage(pos, candles, nowSec, cfg, livePrice) {
  // Sadece girişten SONRA başlayan ve kapanmış mumlar; giriş mumunun önceki fiyatları sayılmaz.
  for (const x of candles) {
    if (x.t + 3600 > nowSec) break;
    if (x.t <= pos.lastT || x.t < pos.openT) continue;
    pos.lastT = x.t;
    if (x.l <= pos.stop) return { exit: true, price: pos.stop * (1 - cfg.slippagePct), reason: pos.be ? "başabaş stop" : "stop" };
    if (x.h >= pos.target) return { exit: true, price: pos.target, reason: "hedef" };
    const oneR = pos.entry + (pos.entry - pos.initStop) * (cfg.beAtR || 1.2);
    if (!pos.be && x.h >= oneR) { pos.stop = pos.entry * (1 + cfg.feePct * 2); pos.be = true; }
  }
  // Anlık fiyat kontrolü
  if (livePrice) {
    if (livePrice <= pos.stop) return { exit: true, price: livePrice * (1 - cfg.slippagePct), reason: pos.be ? "başabaş stop" : "stop" };
    if (livePrice >= pos.target) return { exit: true, price: pos.target, reason: "hedef" };
  }
  if ((nowSec - pos.openT) / 3600 >= cfg.timeStopHours) {
    return { exit: true, price: (livePrice || pos.entry) * (1 - cfg.slippagePct), reason: "süre doldu" };
  }
  return { exit: false };
}

export function sizePosition(equity, cash, entry, stop, cfg) {
  const riskTL = equity * cfg.riskPerTrade;
  const perUnit = entry - stop + entry * cfg.feePct * 2;
  let qty = riskTL / perUnit;
  const maxTL = Math.min(equity * cfg.maxPositionPct, cash * 0.98);
  if (qty * entry > maxTL) qty = maxTL / entry;
  return qty * entry >= 100 ? qty : 0; // 100 TL altı emir yok
}

export function fmt(n) {
  if (!isFinite(n)) return "-";
  const d = n >= 1000 ? 0 : n >= 10 ? 2 : n >= 1 ? 3 : n >= 0.01 ? 5 : 8;
  return Number(n).toLocaleString("tr-TR", { minimumFractionDigits: d, maximumFractionDigits: d });
}
