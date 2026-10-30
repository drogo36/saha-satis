#!/usr/bin/env bash
# Saha Satış Defteri – tam test seti. Kullanım: bash tests/run_all.sh   (depo kökünden ya da herhangi bir yerden)
# Gerekenler: python3 + playwright (chromium). Çıktının sonunda "TÜM TESTLER GEÇTİ" yazmalı.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
export TEST_OUT="${TEST_OUT:-/tmp}"
python3 -c "import re;s=open('index.html').read();js=re.findall(r'<script>(.*?)</script>',s,re.S)[0];open('$TEST_OUT/_app.js','w').write(js)" && node --check "$TEST_OUT/_app.js" || { echo "SÖZDİZİMİ HATASI"; exit 1; }
node --check sw.js || exit 1
python3 -c "import json;json.load(open('version.json'));json.load(open('manifest.webmanifest'))" || exit 1
V1=$(grep -o 'const APP_VERSION="[0-9.]*"' index.html | grep -o '[0-9.]*'); V2=$(python3 -c "import json;print(json.load(open('version.json'))['version'])"); V3=$(grep -o 'const V="saha-[0-9.]*"' sw.js | grep -o '[0-9][0-9.]*')
[ "$V1" = "$V2" ] && [ "$V1" = "$V3" ] || { echo "SÜRÜM UYUMSUZ: index=$V1 version.json=$V2 sw=$V3"; exit 1; }
if ! curl -s -o /dev/null http://127.0.0.1:8767/; then python3 -m http.server 8767 >/dev/null 2>&1 & SRV=$!; sleep 1; fi
FAIL=0
run(){ local name=$1; shift; local out; out=$(timeout 900 python3 "$@" 2>&1); local rc=$?
  if [ $rc -ne 0 ] || echo "$out" | grep -qE 'HATALAR \[[^]]|JS HATALARI: \[[^]]|SORUN [1-9]|Traceback|"hata [0-9]+": \[[^]]'; then echo "✗ $name"; echo "$out" | grep -vE "agent-proxy|connect_rejected|Allowed|For details" | tail -25; FAIL=1; else echo "✓ $name"; fi; }
run "Tarama 390px (her ekran, her buton)" tests/qa.py 390
run "Tarama 320px" tests/qa.py 320
run "Formlar ve yedek" tests/forms.py
run "Stok ve kod tanıma" tests/stk.py
run "Stok kodu sütunu" tests/sku.py
run "Silme, geri al, asistan işlemleri" tests/v20t.py
run "İki cihaz eşitleme ve giriş" tests/sync.py
run "Yakındakiler harita penceresi" tests/nearmap.py
run "Arama kutusunda klavye" tests/klavye.py
run "Müşteri haritası ve trafik" tests/harita.py
run "Öğle: TokenFlex yer önerisi" tests/ogle.py
run "Kendiliğinden güncelleme" tests/upd.py
[ -n "${SRV:-}" ] && kill $SRV 2>/dev/null
[ $FAIL -eq 0 ] && echo "TÜM TESTLER GEÇTİ ($V1)" || { echo "TESTLER BAŞARISIZ"; exit 1; }
