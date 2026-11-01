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
2. `supabase/migrations/20261101000000_initial.sql` dosyasını Supabase SQL Editor'de veya Supabase CLI migration mekanizmasıyla uygulayın.
3. Proje URL'sini ve **anon/publishable** anahtarını `.env` içinde `VITE_SUPABASE_URL` ve `VITE_SUPABASE_ANON_KEY` alanlarına yazın. **Service-role anahtarını istemciye koymayın.**
4. Uygulamayı yeniden başlatın, Ayarlar'dan hesap oluşturun/giriş yapın. E-posta doğrulaması proje ayarlarına bağlıdır. Hafıza Merkezi'nden açıkça bilgi ekleyin, arayın, düzenleyin veya kalıcı olarak silin.

Migration tüm tablolarda RLS uygular; mesaj ve konuşma sahipliği ayrıca bileşik yabancı anahtarla eşleştirilir. Gerçek bir Supabase projesinde migration ve farklı kullanıcılarla RLS testleri ayrıca yapılmalıdır. Tablo şemasının bulunması, tüm tabloların uygulama tarafından kullanıldığı anlamına gelmez: şu anda yalnızca Auth ve `memories` bağlıdır. Hafıza otomatik olarak modele bağlam olarak gönderilmez.

## Bu sürümde çalışanlar

- Mobil ekranlara uyumlu React arayüzü; yerel tema, vurgu rengi, metin boyutu, animasyon ve panel ayarları.
- Ollama model listesi/bağlantı durumu ve sohbet; isteğe bağlı OpenAI uyumlu `/chat/completions` adaptörü; istek iptali ve sınırlandırılmış sohbet bağlamı.
- Tarayıcı Web Speech API üzerinden tek seferlik Türkçe konuşma tanıma ve isteğe bağlı konuşma sentezi. Destek, sesin nerede işlendiği ve mikrofon izinleri tarayıcıya bağlıdır; yerel/çevrimdışı tanıma garantisi yoktur. Sürekli dinleme yoktur.
- Sunucu üzerinden Türkçe Vikipedi araması ve gerçek sayfa giriş metinleri; bağlantılı raporu Markdown olarak indirme. Bu bir başlangıç kaynak araştırmasıdır: kapsamlı web araması, doğrulama, çelişki analizi ve model tarafından sentezleme **yapmaz**.
- Araştırma görevi için oturum içi durum ve iptal. Sohbet geçmişi ve tercihler tarayıcının localStorage alanında, Supabase hafızaları ise giriş yapmış kullanıcının projesinde tutulur. Sohbet ve hafıza ayrı silinir.
- Hata mesajları, testler ve RLS migration dosyası.

## Bilinen önemli eksikler

- Windows/macOS/Linux için Tauri/Electron kabuğu veya Android/iOS için native paket **yoktur**; yalnızca uyumlu web arayüzü vardır. Bu platformlarda native derleme ve cihaz testleri yapılmadı.
- Bilgisayar kontrolü, yapılandırılmış araç çağrıları, dosya/uygulama kontrolü, onay sistemi ve çok adımlı otonom görev yürütücüsü uygulanmadı. Model çıktıları işletim sistemi komutu olarak çalıştırılmaz.
- Hafızalar dışında sohbet, tercihler, görevler ve raporların Supabase üzerinden eşitlenmesi yoktur. Görev geçmişi sayfa yenilenince kaybolur. Hesap silme akışı ve sunucu tarafı kapsamlı veri dışa aktarma yoktur; indirme sadece arayüzde görünen yerel geçmiş, ayar ve yüklenmiş hafızaları içerir.
- Mikrofon cihazı seçimi, ses seviyesi, kapsamlı dil/arka plan/panel yerleşimi ayarları, model indirme arayüzü, yanıt akışı, sağlayıcı model listesi ve bağımsız sağlayıcı bağlantı testi yoktur.
- Gerçek Ollama, Supabase, OpenAI veya Wikipedia bağlantıları bu ortamda doğrulanmadı. Testlerde kullanılan sahte Ollama gerçek servis doğrulaması değildir.

## Güvenlik ve gizlilik

Sunucu yalnızca `127.0.0.1` üzerinde dinler ve sağlayıcı adresleri istemciden değil ortam değişkenlerinden alınır. Farklı Origin'lerden API erişimi reddedilir. Bu uygulamada kullanıcı başına sunucu API kimlik doğrulaması, hız sınırlama veya internet üzerinden güvenli çok kullanıcılı dağıtım yoktur: **sunucuyu veya geliştirme önizleme bağlantısını güvenilmeyen kişilerle paylaşmayın**, aksi hâlde sunucuda yapılandırılmış sağlayıcıyı kullanabilirler. Geliştirme sunucusunu genel internete açmayın.

`.env` ve anahtarlar Git'e eklenmez. localStorage şifreli değildir; hassas bilgileri sohbet ve hafızaya girmeyin. Supabase anonim anahtarı genel istemci anahtarıdır; veri izolasyonu için RLS zorunludur. Harici API seçildiğinde sohbet içeriği seçili sağlayıcıya gider. Vikipedi aramasında araştırma konusu Vikipedi'ye gönderilir. Tarayıcı tabanlı konuşma tanıma sağlayıcıya ses gönderebilir. Uygulama dışarıdan yüklenen Google Fonts kullanır; erişilemezse sistem fontlarına döner.

## Test

```bash
npm test
npm run build
npm audit
```

Node testleri doğrulama, hata mesajları, köken kontrolü ve sahte Ollama ile API bağlantısını; jsdom testleri temel gezinme ve ayar kalıcılığını kapsar. Bunlar gerçek mobil/masaüstü cihaz, mikrofon, internet araştırması, gerçek Supabase RLS veya gerçek sağlayıcı entegrasyon testlerinin yerine geçmez.
