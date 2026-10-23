# Saha Satış Defteri

Yedek parça saha satışı için telefon uygulaması: müşteri kartları, ziyaret notları, Excel'den sipariş/fatura yükleme, öncelikli toptan alıcı listesi ve 18:00'de evde biten Google Maps rotası.

**Aç:** https://drogo36.github.io/saha-satis/ → Chrome menüsü → *Ana ekrana ekle*

Kayıtlar telefonda tutulur. Rapor sekmesinden düzenli olarak **Yedek al**.

## Yapay zekâ asistanı
Asistan sekmesi Google Gemini ile çalışır (ücretsiz anahtar: https://aistudio.google.com/apikey). Anahtar sadece telefonda saklanır.

## Güncelleme
Yeni sürüm yayınlamak için `index.html` içindeki `APP_VERSION`, `sw.js` içindeki `V` ve `version.json` aynı numaraya yükseltilir. Uygulama açılışta ve 30 dakikada bir `version.json`'u kontrol edip "Şimdi güncelle" der.
