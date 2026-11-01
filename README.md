# Prometheus AI

Prometheus, Türkçe öncelikli, kişiselleştirilebilir kişisel asistan olarak aşamalı geliştirilmektedir. Mevcut sürüm; duyarlı web arayüzü, yerel tercihler/geçmiş, tarayıcı destekliyorsa ses tanıma ve isteğe bağlı gerçek model bağlantısı içerir. Araştırma taraması ve cihaz kontrolü henüz yoktur.

## Çalıştırma

Node.js 18+ gereklidir (yerleşik `fetch` kullanılır); ek npm bağımlılığı yoktur.

```bash
npm start
```

`http://localhost:4173` adresini açın. Farklı port için `PORT=4174 npm start` kullanın. Sunucu `0.0.0.0` üzerinde dinler.

## Model sağlayıcısı

Varsayılan sağlayıcı Ollama'dır. Ollama'yı ayrıca kurup çalıştırın, ardından istediğiniz yerel modeli indirin (ör. `ollama pull llama3.2`). Ayarlar sayfasından bağlantıyı test edin. Varsayılan uç nokta `http://127.0.0.1:11434`.

Ortam değişkenleriyle yapılandırılır; örnekler `.env.example` içindedir. Node sunucusu `.env` dosyasını kendiliğinden yüklemez; değişkenleri kabuk ortamınıza verin veya kendi yerel başlatma betiğinizi kullanın. Bulut/OpenAI uyumlu sağlayıcı örneği:

```bash
AI_PROVIDER=openai AI_BASE_URL=https://api.openai.com/v1 AI_MODEL=gpt-4o-mini AI_API_KEY='...' npm start
```

`AI_API_KEY` hiçbir zaman arayüze gönderilmez veya API durum yanıtında gösterilmez. Gerçek anahtarı `.env.example`, kaynak kodu veya Git'e eklenen dosyalara yazmayın. Sağlayıcıların ücretleri/kotaları değişebilir; ücretsiz hizmet olduğu varsayılmaz. OpenAI uyumlu uç nokta biçimi kullanan başka sağlayıcılar da `AI_BASE_URL` ile denenebilir.

## Mevcut işlevler

- Duyarlı arayüz ve sayfalar arası navigasyon.
- Tema, vurgu rengi, yazı boyutu ve dil tercihlerinin tarayıcıda saklanması.
- Yazılı ve (Web Speech API destekli tarayıcılarda) kullanıcı düğmesine basarak etkinleştirilen sesli komut.
- Sunucu üzerinden Ollama veya OpenAI uyumlu sohbet API'sine komut gönderme; yanıtı arayüzde ve isteğe bağlı tarayıcı TTS ile gösterme.
- Komut/yanıt geçmişinin yalnızca tarayıcı `localStorage` alanında saklanması.
- Ayarlar ekranında sağlayıcı/model durumu ve bağlantı testi.
- Araştırma konusu için plan taslağı; gerçek web araması yapılmadığı belirtilir.

Ses tanımada tarayıcı sağlayıcısına bağlı olarak ses cihaz dışında işlenebilir. Mikrofon, kullanıcı düğmeye basmadan başlatılmaz. Model sağlayıcısına gönderilen komutlar seçilen sağlayıcının koşullarına tabidir.

## Henüz uygulanmayanlar

Gerçek web araması ve kaynaklı araştırma raporu, masaüstü uygulama/dosya kontrolü, görev otomasyonu, native Windows/macOS/Linux ve Android/iOS istemcileri, senkronizasyon ve güvenli yerel sır kasası. Web arayüzü bilgisayar üzerinde işlem yapmaz. API anahtarları sunucu ortam değişkenlerinde yönetilir; ortak kullanıma açık sunucuya koymadan önce kimlik doğrulama, istek sınırlandırma ve ağ erişimi güvenliğini ekleyin.

## Doğrulama

```bash
node --check app.js
node --check server.mjs
npm test
npm start
```
