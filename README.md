# Prometheus

Türkçe öncelikli, yerel Ollama ile sohbet edebilen kişisel asistanın **erken web sürümü**. Bu depo tam özellikli bir masaüstü/mobil asistan değildir; aşağıdaki sınırlar geçerlidir.

## Gereksinimler ve çalıştırma

- Node.js 22 veya üzeri ve npm.
- Yerel sohbet için [Ollama](https://ollama.com/download), çalışan sunucu ve kullanıcının kendi seçip kurduğu bir model. Örnek: `ollama pull llama3.2` (model indirmek kullanıcı tarafından başlatılır).
- İsteğe bağlı: Supabase projesi; OpenAI uyumlu sağlayıcı anahtarı.

```bash
npm ci
cp .env.example .env
# İsteğe bağlı değişkenleri düzenleyin
npm run dev
```

Vite'ın gösterdiği adrese gidin. **AI Sağlayıcıları** sayfasında bağlantıyı yenileyip kurulu modeli seçin. Önizlemede Ollama uygulama sunucusunun çalıştığı makinede aranır; tarayıcıyı açan cihazın localhost'u kullanılmaz. `.env` değişikliklerinden sonra süreçleri yeniden başlatın.

Üretim benzeri yerel kullanım:

```bash
npm run build
npm start
# http://127.0.0.1:3001
```

`OLLAMA_URL` sunucu tarafında ayarlanır. İsteğe bağlı OpenAI uyumlu sağlayıcı için `OPENAI_BASE_URL` ve `OPENAI_API_KEY` sunucu `.env` dosyasında ayarlanır; arayüzde model adı ve sağlayıcı seçilir. Sağlayıcı otomatik olarak değiştirilmez. Sağlayıcı kullanımı ücretli olabilir; ücretsiz kota garanti edilmez. Sağlayıcı anahtarını `VITE_` değişkenine koymayın.

## Supabase

1. Bir Supabase projesi açın; Auth e-posta yöntemini projenizde yapılandırın.
2. `supabase/migrations/` klasöründeki SQL dosyalarını tarih sırasıyla Supabase SQL Editor'de veya Supabase CLI migration mekanizmasıyla uygulayın.
3. Proje URL'sini ve **anon/publishable** anahtarını `.env` içinde `VITE_SUPABASE_URL` ve `VITE_SUPABASE_ANON_KEY` alanlarına yazın. **Service-role anahtarını istemciye koymayın.**
4. Uygulamayı yeniden başlatın, Ayarlar'dan hesap oluşturun/giriş yapın. E-posta doğrulaması proje ayarlarına bağlıdır. Supabase Auth URL Configuration bölümünde uygulamanın adresini Site URL ve Redirect URLs listesine ekleyin. Önizleme adresi değişirse yeni adresi eklemeniz gerekir. Hafıza Merkezi'nden açıkça bilgi ekleyin, arayın, düzenleyin veya kalıcı olarak silin.

Migration tüm tablolarda RLS uygular; mesaj ve konuşma sahipliği ayrıca bileşik yabancı anahtarla eşleştirilir. Migration’ları hedef projeye uyguladıktan sonra `tests/supabase-rls.integration.sql` dosyasını test projesinin SQL Editor’ünde çalıştırabilirsiniz; test geçici kullanıcı ve verileri transaction sonunda geri alır. Daha önce eski `20261101000000`/`20261101010000` sürüm numaralarıyla migration uyguladıysanız, CLI kullanmadan önce migration geçmişini yedekleyip Supabase migration repair yöntemiyle uzlaştırın; aynı tabloları tekrar oluşturmayın. Tablo şemasının bulunması, tüm tabloların uygulama tarafından kullanıldığı anlamına gelmez: Auth, `memories`, sohbet kopyaları ve görünüm/ses tercihleri bağlıdır. Hafıza otomatik gönderilmez: Hafıza Merkezi’nde en fazla beş kayıt seçilip mevcut model ve sağlayıcı için açıkça onaylanırsa sonraki sohbet isteklerine eklenir. Paylaşım kapatılabilir; seçim, oturum veya model/sağlayıcı değişirse onay sıfırlanır. Her kayıt en fazla 500 karakterdir. Model bu bilgileri yanıtında tekrar edebilir; yanıtlar sohbet geçmişine kaydedilebilir. Kayıtlar veri olarak işaretlenir ama istem enjeksiyonuna karşı model davranışı garanti edilemez.

## Bu sürümde çalışanlar

- Mobil ekranlara uyumlu React arayüzü; yerel tema, vurgu rengi, metin boyutu, animasyon ve panel ayarları.
- Ollama model listesi/bağlantı durumu ve sohbet; isteğe bağlı OpenAI uyumlu `/chat/completions` adaptörü; istek iptali ve sınırlandırılmış sohbet bağlamı.
- Tarayıcı Web Speech API üzerinden tek seferlik Türkçe konuşma tanıma ve isteğe bağlı konuşma sentezi. Destek, sesin nerede işlendiği ve mikrofon izinleri tarayıcıya bağlıdır; yerel/çevrimdışı tanıma garantisi yoktur. Sürekli dinleme yoktur.
- Sunucu üzerinden Türkçe Vikipedi araması ve gerçek sayfa giriş metinleri; bağlantılı raporu Markdown olarak indirme. Bu bir başlangıç kaynak araştırmasıdır: kapsamlı web araması, doğrulama, çelişki analizi ve model tarafından sentezleme **yapmaz**.
- Araştırma görevi için oturum içi durum ve iptal. Sohbetler ve tercihler tarayıcının localStorage alanında tutulur. Giriş yapan kullanıcı sohbetin bir anlık görüntüsünü açık onayla buluta kopyalayabilir, diğer cihazda listeleyip içe aktarabilir veya bulut kopyasını kalıcı silebilir. Yerel ve bulut silme ayrıdır; bu otomatik senkronizasyon veya çatışma çözümü değildir. Görünüm/ses tercihleri ayrı onaylarla buluta yazılabilir veya cihazda uygulanabilir; sağlayıcı/model ve anahtarlar aktarılmaz. Supabase hafızaları giriş yapmış kullanıcının projesinde tutulur. Kullanıcı onaylarsa seçilmiş kayıtlar sohbet bağlamına eklenir. Sohbet ve hafıza ayrı silinir; hafızayı silmek önceki yanıtlardaki tekrarlarını silmez.
- Yerel yardımcı ayrı bir terminalde açıkça etkinleştirilirse, belirlenen klasörde dizin listeleme ve en fazla 64 KB UTF-8 dosya okuma. Her işlem için yerel terminal onayı gerekir; dosyalar otomatik olarak modele veya buluta gönderilmez.
- Hata mesajları, testler ve RLS migration dosyası.

## Bilinen önemli eksikler

- Windows/macOS/Linux için Tauri/Electron kabuğu veya Android/iOS için native paket **yoktur**; yalnızca uyumlu web arayüzü vardır. Bu platformlarda native derleme ve cihaz testleri yapılmadı.
- Yerel yardımcı yalnızca elle istenen klasör listeleme ve metin okuma işlemlerini destekler. Modelin önerdiği JSON plan kullanıcı tarafından incelenip forma aktarılabilir; otomatik araç yürütme, dosya yazma/silme, program açma/kapama, tarayıcı otomasyonu, sistem ayarları ve çok adımlı otonom görev yürütücüsü uygulanmadı. Model çıktıları işletim sistemi komutu olarak çalıştırılmaz.
- Sohbet ve tercih aktarımı manueldir; görevler ve raporların Supabase üzerinden eşitlenmesi yoktur. Görev geçmişi sayfa yenilenince kaybolur. Hesap silme akışı ve sunucu tarafı kapsamlı veri dışa aktarma yoktur; indirme sadece arayüzde görünen yerel geçmiş, ayar ve yüklenmiş hafızaları içerir.
- Mikrofon cihazı seçimi, ses seviyesi, kapsamlı dil/arka plan/panel yerleşimi ayarları, model indirme arayüzü, yanıt akışı, sağlayıcı model listesi ve bağımsız sağlayıcı bağlantı testi yoktur.
- Gerçek Supabase projesinde şema, RLS politikaları ve geri alınan iki kullanıcılı veritabanı testi doğrulandı; bu çalışma ortamından Supabase Auth/REST HTTP erişimi kısıtlı olduğundan tarayıcı üzerinden uçtan uca giriş test edilmedi. Gerçek Ollama, OpenAI veya Wikipedia bağlantıları doğrulanmadı. Testlerde kullanılan sahte Ollama gerçek servis doğrulaması değildir.

## İsteğe bağlı yerel dosya yardımcısı

Bu özellik yalnızca sunucu ve yardımcının kullanıcının kendi bilgisayarında çalıştığı durum içindir. Bulut önizleme sunucusu, tarayıcınızı açtığınız bilgisayarın dosyalarına erişemez. **Yardımcı anahtarını uzak veya paylaşılan bir önizlemeye girmeyin.** Yardımcı varsayılan olarak kapalıdır.

İki yerel terminal açın; yalnızca erişilmesini istediğiniz bir klasörü seçin:

```bash
# Terminal 1 — macOS/Linux (çalışma klasörünüzün tam yoluyla değiştirin)
PROMETHEUS_WORKSPACE="/tam/yol/izinli-klasor" npm run desktop-helper
# Terminal 2 — sunucu yönlendirmesini açıkça etkinleştirin
ENABLE_DESKTOP_HELPER=true npm run dev
```

Windows PowerShell:

```powershell
# Terminal 1
$env:PROMETHEUS_WORKSPACE = 'C:\Users\Kullanici\Belgeler\Prometheus'
npm run desktop-helper
# Terminal 2
$env:ENABLE_DESKTOP_HELPER = 'true'
npm run dev
```

Yerel uygulamada Araçlar sayfasına, yalnızca yardımcı terminalinde gösterilen oturuma özel anahtarı girin. Anahtar tarayıcının kalıcı depolamasına yazılmaz ve yardımcı her yeniden başlatıldığında değişir. Göreli yol belirtip isteği başlatın. İsteğe bağlı “AI ile planla” yalnızca sınırlı bir listeleme/okuma JSON önerisi üretir; kullanıcı öneriyi gözden geçirip forma aktarmalıdır. Planlama metni seçili modele gider, dosya içeriği gönderilmez. Desteklenmeyen veya geçersiz planlar reddedilir. **Her isteği Terminal 1’de `evet` yazarak ayrıca onaylayın**. Yanıt verilmezse 60 saniyede zaman aşımına uğrar. İstek onay beklerken iptal edilebilir; işlem yürütülmeye başladıktan sonra iptal geri alma garantisi vermez. Terminali kapatmak yetkiyi sona erdirir.

Yardımcı sadece loopback üzerinde dinler, rastgele 256 bit anahtar kullanır, `..` ve mutlak yolları reddeder, sembolik bağlantıları izlemez ve tek seferde en fazla 200 öğe/64 KB UTF-8 metin döndürür. Günlükler dosya içeriklerini içermez; terminal onay istemi seçilen yolu gösterir. Bu mekanizma kötü niyetli yerel bir sürecin dosyaları eş zamanlı değiştirmesine karşı tam bir işletim sistemi sandbox'ı değildir. Yalnızca güvenilir yerel bilgisayarda ve düşük yetkili kullanıcıyla çalıştırın. Ağda yayınlamayın, anahtarı paylaşmayın ve hassas klasörleri kök olarak seçmeyin.

## Güvenlik ve gizlilik

Sunucu yalnızca `127.0.0.1` üzerinde dinler ve sağlayıcı adresleri istemciden değil ortam değişkenlerinden alınır. Farklı Origin'lerden API erişimi reddedilir. Bu uygulamada kullanıcı başına sunucu API kimlik doğrulaması, hız sınırlama veya internet üzerinden güvenli çok kullanıcılı dağıtım yoktur: **sunucuyu veya geliştirme önizleme bağlantısını güvenilmeyen kişilerle paylaşmayın**, aksi hâlde sunucuda yapılandırılmış sağlayıcıyı kullanabilirler. Geliştirme sunucusunu genel internete açmayın.

`.env` ve anahtarlar Git'e eklenmez. localStorage şifreli değildir; hassas bilgileri sohbet ve hafızaya girmeyin. Supabase anonim anahtarı genel istemci anahtarıdır; veri izolasyonu için RLS zorunludur. Harici API seçildiğinde sohbet içeriği seçili sağlayıcıya gider. Vikipedi aramasında araştırma konusu Vikipedi'ye gönderilir. Tarayıcı tabanlı konuşma tanıma sağlayıcıya ses gönderebilir. Uygulama dışarıdan yüklenen Google Fonts kullanır; erişilemezse sistem fontlarına döner.

## Test

```bash
npm test
npm run build
npm audit
```

Node testleri doğrulama, hata mesajları, köken kontrolü, sahte Ollama ile API bağlantısını, yerel yardımcı yol/izin denetimlerini ve sahte Supabase adaptörüyle senkronizasyon kurallarını; jsdom testleri temel gezinme ve ayar kalıcılığını kapsar. Bunlar gerçek mobil/masaüstü cihaz, mikrofon, internet araştırması, gerçek Supabase RLS veya gerçek sağlayıcı entegrasyon testlerinin yerine geçmez.
