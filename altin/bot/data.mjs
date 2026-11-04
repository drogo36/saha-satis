const sleep = ms => new Promise(r => setTimeout(r, ms));
export async function getJSON(url, tries = 3) {
  let last;
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(url, { headers: { "User-Agent": "altin-robotu/1.0" } });
      if (r.ok) return await r.json();
      last = new Error(`HTTP ${r.status}`);
      await sleep(r.status === 429 ? 3000 * (i + 1) : 800);
    } catch (e) { last = e; await sleep(800); }
  }
  throw new Error(`veri alınamadı: ${url} (${last?.message})`);
}
// 15 dakikalık tamamlanmış mumlar, 25 günlük parçalarla.
export async function fetchCandles(days, now = Math.floor(Date.now() / 1000)) {
  const all = new Map();
  for (let k = days; k > 0; k -= 25) {
    const from = now - k * 86400, to = Math.min(now, from + 25 * 86400);
    const d = await getJSON(`https://graph-api.btcturk.com/v1/klines/history?symbol=XAUTTRY&resolution=15&from=${from}&to=${to}`);
    if (d?.s === "ok" && d.t) d.t.forEach((t, i) => all.set(t, { t, o: +d.o[i], h: +d.h[i], l: +d.l[i], c: +d.c[i], v: +(d.v?.[i] ?? 0) }));
    await sleep(200);
  }
  return [...all.values()].sort((a, b) => a.t - b.t).filter(c => c.t + 900 <= now && c.o > 0 && c.h >= c.l);
}
