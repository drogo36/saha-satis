# Saha Satış Defteri — geliştirme kuralları

Bu dosya, uygulamayı geliştiren herkes (otomatik zamanlanmış görev dahil) için bağlayıcıdır.

## Uygulama
- Tek dosyalık PWA: `index.html` (tüm HTML/CSS/JS). `boot.html` açılış yükleyicisidir, **değiştirme**.
- Yayın: GitHub Pages → https://drogo36.github.io/saha-satis/boot.html . `boot.html`, `index.html`'i
  `raw.githubusercontent.com/drogo36/saha-satis/main/index.html` adresinden çeker.
- Kullanıcı Muhammed: İstanbul'da Ford/Fiat/PSA yedek parça saha satış danışmanı, teknik değil. Arayüz metinleri **Türkçe**, sade ve net.
- Kayıtlar telefonda (localStorage `saha-satis-v1`, fotoğraflar IndexedDB). Firebase eşitleme kodu hazır, `FB_CONFIG=null` iken kapalı.

## Her değişiklikte zorunlu
1. Sürümü **üç yerde** aynı artır: `index.html` → `const APP_VERSION`, `sw.js` → `const V="saha-x.y.z"`, `version.json` → `version` ve kısa Türkçe `notes`.
2. Var olan kayıtlarla **geriye uyumlu** kal: alan silme/yeniden adlandırma yok; yeni alanlar boş olabilir.
3. Kullanıcı verisini silen her işlem **onaylı** ve mümkünse **geri alınabilir** (`removeMany` + "Geri al") olsun.
4. Yeni özellik için `tests/` altına en az bir senaryo ekle (mevcut test dosyalarını örnek al).
5. `bash tests/run_all.sh` çıktısının sonunda **"TÜM TESTLER GEÇTİ"** görmeden yayınlama.
6. Gizli bilgi (anahtar, şifre, token) koda yazma. Harici servis eklerken ücretsiz ve anahtarsız olmasına dikkat et.
7. Telefon genişliği (320–390px) ve koyu tema bozulmamalı; yatay kaydırma olmamalı.

## İstekler
- Kullanıcı istekleri GitHub Issues'ta `istek` etiketiyle gelir (uygulamadaki Asistan → "Özellik iste").
- Belirsiz, riskli (toplu veri silme, ücretli servis, güvenlik) ya da büyük isteklerde kodu değiştirme; issue'ya Türkçe, sade bir soru yaz.
- Tamamlanan isteği issue'ya Türkçe kısa açıklama yazarak kapat (ne değişti, nerede görünür, sürüm no).
