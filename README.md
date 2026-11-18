# PROMETHEUS AI — Tony Stark'ın JARVIS'inden İlham Alan Tam Yetkili & %100 Ücretsiz Asistan

Prometheus; bilgisayarınızdaki tüm programları açıp kapatabilen, istediğiniz her web sitesine girip arama yapabilen, tam terminal/sistem yetkisine sahip, sesli komutları Türkçe ve İngilizce olarak kusursuz algılayan **tamamen ücretsiz** kişisel yapay zeka asistanınızdır.

---

## Öne Çıkan Özellikler

- **Tony Stark Arc Reactor HUD Arayüzü**: Canlı ses frekans görselleştiricili, gerçek zamanlı CPU / RAM / Disk telemetrili fütüristik arayüz.
- **Kusursuz Sesli Komut (Türkçe & İngilizce)**:
  - *"Prometheus..."* uyandırma kelimesi (fonetik hata toleranslı: *Prometyus, Prometeus, Jarvis* dahil) veya **Doğrudan Eller Serbest Modu**.
  - Yankı engelleme (Prometheus konuşurken kendini dinlemez), sessizlik ve bağlantı kopmalarına karşı otomatik yeniden başlatma.
  - **Ücretsiz Neural Seslendirme (`edge-tts`)**: Türkçe `tr-TR-AhmetNeural` (JARVIS tarzı erkek ses) ve `tr-TR-EmelNeural`, İngilizce `en-GB-RyanNeural` + çevrimdışı tarayıcı ses sentezi yedeği.
- **Her Programı Açma & Kapatma**:
  - Windows Başlat Menüsü, Kayıt Defteri (`App Paths`), UWP/Microsoft Store uygulamaları, macOS `/Applications` ve Linux `.desktop` dosyalarını otomatik tarar.
  - *"Discord'u aç"*, *"Hesap makinesini başlat"*, *"VS Code aç"*, *"Chrome'u kapat"* gibi doğal komutlar + **Özel Uygulama Ekleme** paneli.
- **Her Web Sitesine Girme & Site İçi Arama**:
  - *"YouTube'u aç"*, *"github.com'a gir"*, *"YouTube'da Lo-Fi çal"*, *"Google'da yapay zeka haberleri ara"*, *"Haritalarda İstanbul ara"*, *"Trendyol'da klavye ara"*.
- **Tam Yetki (Full Authority) Sistem Kontrolü**:
  - Ses seviyesi (*"Sesi yüzde 40 yap"*, *"Sessize al"*), medya tuşları, ekran görüntüsü alma, klasör açma (*"Masaüstünü aç"*), kilitleme/uyku/yeniden başlatma/kapatma.
  - Doğrudan terminal/PowerShell/bash komutları: *"komut çalıştır: ipconfig"* veya özel sesli makrolar.
- **%100 Ücretsiz Ekstra Zeka**:
  - Notlar, zamanlayıcılar, hesap makinesi, ücretsiz hava durumu (`Open-Meteo`), Wikipedia özetleri.
  - İsteğe bağlı ücretsiz yerel **Ollama** LLM desteği (`llama3.2`, `qwen2.5` vb.).

---

## Bilgisayarınızda Kurulum ve Çalıştırma

### Windows (Tek Tıkla)
`start_prometheus.bat` dosyasına çift tıklayın. Otomatik olarak Python sanal ortamını kurar, bağımlılıkları yükler ve Prometheus HUD'ı tarayıcınızda açar.

### macOS / Linux
```bash
chmod +x start_prometheus.sh
./start_prometheus.sh
```

### Manuel Başlatma
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

### Terminal / Arka Plan Mikrofon Modu (Opsiyonel)
```bash
pip install -r requirements-voice-offline.txt
python run.py --cli
```

---

## Örnek Sesli Komutlar

- *"Prometheus, YouTube'da Tarkan ara"*
- *"Prometheus, Discord'u aç"*
- *"Prometheus, github.com'a gir"*
- *"Prometheus, sesi yüzde 60 yap"*
- *"Prometheus, ekran görüntüsü al"*
- *"Prometheus, 5 dakika zamanlayıcı kur"*
- *"Prometheus, not al: Yarın saat 10'da toplantı var"*
- *"Prometheus, sistem durumu"*
- *"Prometheus, komut çalıştır: git status"*
- *"Prometheus, bilgisayarı kilitle"*
