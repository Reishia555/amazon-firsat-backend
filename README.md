# Amazon Fırsat Avcısı Backend

Amazon.com.tr'den gerçek büyük indirimleri bulan ve iOS'a bildirim gönderen backend sistemi.

## 🎯 Amaç

- Amazon'daki **GERÇEK** büyük indirimleri bulma (%70+ indirim)
- Sahte indirimleri eleme (fiyatı önce artırıp sonra indirim yapanlar)
- iOS cihazlara push notification gönderme
- Railway.app'e kolay deployment

## 🏗️ Proje Yapısı

```
backend/
├── app.py              # Flask API server
├── amazon_scraper.py   # Amazon.com.tr scraping
├── database.py         # PostgreSQL veritabanı işlemleri
├── price_tracker.py    # Fiyat takip ve sahte indirim tespiti
├── notifier.py         # Apple Push Notification sistemi
├── scheduler.py        # Otomatik görev zamanlayıcısı
├── requirements.txt    # Python bağımlılıkları
├── Procfile           # Railway deployment
├── railway.json       # Railway konfigürasyonu
├── .env.example       # Çevre değişkenleri örneği
└── README.md          # Bu dosya
```

## 🚀 Özellikler

### 🔍 Akıllı Scraping
- Amazon.com.tr günün fırsatlarını otomatik tarar
- Sadece belirli kategorileri takip eder (Bilgisayar, Elektronik, Ev&Mutfak, Spor, Oyun)
- %70+ indirimli ürünleri filtreler
- Rate limiting ile bot tespitini önler

### 🕵️ Sahte İndirim Tespiti
- Fiyat geçmişi analizi
- Son 7 günde fiyat artışı kontrolü
- Liste fiyatı mantık kontrolü
- Şüpheli aktivite tespiti

### 📱 iOS Bildirimleri
- Apple Push Notification Service (APNS) entegrasyonu
- Gerçek zamanlı fırsat bildirimleri
- Fiyat düşüşü uyarıları
- Kullanıcı tercihlerine göre filtreleme

### ⏰ Otomatik Görevler
- Her saat başı Amazon taraması
- Her 30 dakikada fiyat değişikliği kontrolü
- Günlük veri temizleme
- Sistem sağlık kontrolü

## 📊 API Endpoints

### Genel
- `GET /health` - Sistem sağlığı
- `GET /stats` - Genel istatistikler
- `GET /scheduler/status` - Scheduler durumu

### Fırsatlar
- `GET /deals` - Mevcut fırsatları getir
- `GET /deals/new` - Yeni bulunan fırsatlar
- `GET /trending` - Trend gösteren ürünler
- `GET /categories` - Kategori listesi

### Ürün Detayları
- `GET /product/<asin>` - Ürün detayı
- `GET /product/<asin>/history` - Fiyat geçmişi

### Kullanıcı İşlemleri
- `POST /register` - Cihaz kaydı ve tercihler
- `POST /test-notification` - Test bildirimi

### Test (Sadece Development)
- `POST /scrape` - Manuel scraping tetikle

## 🛠️ Kurulum

### 1. Railway'de Deployment

1. Railway hesabı oluşturun: https://railway.app
2. GitHub reposunu bağlayın
3. PostgreSQL database ekleyin (otomatik)
4. Environment variables'ları ayarlayın:

```bash
# APNS ayarları (Apple Developer'dan alın)
APNS_KEY_ID=your_key_id
APNS_TEAM_ID=your_team_id
APNS_KEY_PATH=./apns_key.p8
BUNDLE_ID=com.yourname.amazonfirsat

# Production için
FLASK_ENV=production
APNS_USE_SANDBOX=false
```

5. APNS key dosyasını (.p8) projeye ekleyin
6. Deploy edin!

### 2. Local Development

```bash
# Repoyu klonlayın
git clone <repo-url>
cd backend

# Virtual environment oluşturun
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Environment dosyasını oluşturun
cp .env.example .env
# .env dosyasını düzenleyin

# PostgreSQL kurulu olmalı
# Database oluşturun ve DATABASE_URL'i .env'e ekleyin

# Uygulamayı başlatın
python app.py
```

## 🔧 Yapılandırma

### Database Schema

**products** tablosu:
- ASIN (Amazon ürün ID)
- Başlık, fiyatlar, indirim yüzdesi
- Kategori, resim URL, ürün linki
- İlk görülme ve son güncelleme tarihleri

**price_history** tablosu:
- ASIN referansı
- Fiyat ve kayıt tarihi

**user_preferences** tablosu:
- Cihaz token'ı
- Minimum indirim, kategoriler
- Fiyat aralığı tercihleri

### Scraping Mantığı

1. **Kategori Filtreleme**: Sadece belirlenen kategorilerdeki ürünler
2. **Fiyat Filtreleme**: 10₺ - 10.000₺ arası
3. **İndirim Filtreleme**: Minimum %70 indirim
4. **Sahte İndirim Tespiti**:
   - Son 7 günde %20+ fiyat artışı varsa şüpheli
   - Liste fiyatı mevcut fiyatın 3 katından fazlaysa şüpheli
   - Fiyat geçmişinde manipülasyon pattern'i varsa şüpheli

### Bildirim Sistemi

- **Deal Alert**: Yeni gerçek fırsat bulunduğunda
- **Price Drop**: Takip edilen üründe önemli fiyat düşüşü
- **Test Notification**: Sistem test için

## 📈 Monitoring

### Health Check
```bash
curl https://yourapp.railway.app/health
```

### Stats Endpoint
```bash
curl https://yourapp.railway.app/stats
```

### Scheduler Status
```bash
curl https://yourapp.railway.app/scheduler/status
```

## 🔒 Güvenlik

- Environment variables ile hassas bilgi saklama
- Rate limiting ile bot koruması
- CORS yapılandırması
- Input validation
- SQL injection koruması (parameterized queries)

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Railway'de PostgreSQL eklendi mi kontrol edin
   - DATABASE_URL doğru mu kontrol edin

2. **APNS Not Working**
   - APNS key dosyası doğru yerde mi?
   - Key ID ve Team ID doğru mu?
   - Sandbox/Production ayarı doğru mu?

3. **Scraping Issues**
   - Amazon anti-bot önlemlerini artırmış olabilir
   - User-Agent'ları güncelleyin
   - Delay ayarlarını artırın

### Logs

Railway'de logs:
```bash
railway logs
```

Local development:
```bash
python app.py  # Console'da loglar görünür
```

## 📚 Dependencies

- **Flask**: Web framework
- **BeautifulSoup4**: HTML parsing
- **Requests**: HTTP client
- **psycopg2-binary**: PostgreSQL adapter
- **APScheduler**: Task scheduling
- **aioapns**: Apple Push Notifications
- **python-dotenv**: Environment variables

## 🤝 Contributing

1. Fork'layın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit'leyin (`git commit -m 'Add amazing feature'`)
4. Push'layın (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📄 License

Bu proje MIT lisansı altında lisanslanmıştır.

## 🔗 Railway Deployment

Railway'e deploy etmek için:

1. Railway hesabı oluşturun
2. GitHub repo'yu bağlayın  
3. PostgreSQL service ekleyin
4. Environment variables'ları ayarlayın
5. Deploy!

Railway otomatik olarak:
- `requirements.txt`'den bağımlılıkları yükler
- `Procfile`'daki komutu çalıştırır
- PostgreSQL veritabanı URL'ini otomatik sağlar
- Health check yapar

## 📞 Support

Sorunlar için GitHub Issues kullanın.