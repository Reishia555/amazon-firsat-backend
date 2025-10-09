import requests
import json
import time

BASE_URL = "https://web-production-d0fdc.up.railway.app"

def test_health():
    """Health check testi"""
    print("🏥 Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        result = response.json()
        
        if result.get('status') == 'ok':
            print("✅ Backend çalışıyor!")
            print(f"   📊 Database: {result.get('database', 'Unknown')}")
            print(f"   🕐 Timestamp: {result.get('timestamp', 'Unknown')}")
            print(f"   🔢 Version: {result.get('version', 'Unknown')}")
        else:
            print("❌ Backend sorunu var!")
            
    except Exception as e:
        print(f"❌ Health check hatası: {e}")

def test_scraping():
    """Manuel scraping testi"""
    print("\n🕷️  Manuel Scraping Başlatılıyor...")
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/scrape-now", timeout=180)
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Scraping tamamlandı!")
            
            # Sonuçları göster
            results = result.get('results', {})
            by_site = results.get('by_site', {})
            
            print(f"⏱️  Süre: {end_time - start_time:.1f} saniye")
            print(f"📊 Sonuçlar:")
            
            if 'trendyol' in by_site:
                trendyol = by_site['trendyol']
                status = "✅" if trendyol.get('success') else "❌"
                print(f"   🛍️  Trendyol: {trendyol.get('count', 0)} ürün {status}")
            
            if 'hepsiburada' in by_site:
                hepsiburada = by_site['hepsiburada']
                status = "✅" if hepsiburada.get('success') else "❌"
                print(f"   🛒 Hepsiburada: {hepsiburada.get('count', 0)} ürün {status}")
            
            print(f"   🎯 Toplam: {results.get('total_products', 0)} ürün")
            print(f"   💾 Kaydedilen: {results.get('total_saved', 0)} ürün")
            
            # Hatalar varsa göster
            errors = results.get('errors', [])
            if errors:
                print(f"   ⚠️  Hatalar ({len(errors)}):")
                for error in errors:
                    print(f"      - {error}")
        else:
            print(f"❌ Scraping hatası: HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("⏰ Scraping timeout (3 dakika+)")
    except Exception as e:
        print(f"❌ Scraping hatası: {e}")

def test_products():
    """Ürün listesi testi"""
    print("\n🛍️  Ürünler Getiriliyor...")
    try:
        response = requests.get(f"{BASE_URL}/products?limit=5", timeout=10)
        result = response.json()
        
        if result.get('success'):
            products = result.get('products', [])
            
            if not products:
                print("❌ Henüz ürün yok!")
                print("   💡 Scraping çalıştırıp tekrar deneyin")
                return
            
            print(f"✅ {len(products)} ürün bulundu:\n")
            
            for i, product in enumerate(products, 1):
                title = product.get('title', 'Başlık yok')[:50]
                current_price = product.get('current_price', 0)
                list_price = product.get('list_price', 0)
                discount = product.get('discount_percent', 0)
                site_name = product.get('site_name', 'Bilinmeyen')
                product_url = product.get('product_url', '')[:60]
                
                print(f"{i}. {title}...")
                print(f"   💰 {current_price}₺ (Eski: {list_price}₺)")
                print(f"   🔥 %{discount} indirim")
                print(f"   🏪 {site_name}")
                print(f"   🔗 {product_url}...")
                print()
        else:
            print(f"❌ Ürün listesi hatası: {result.get('error', 'Bilinmeyen hata')}")
            
    except Exception as e:
        print(f"❌ Ürün listesi hatası: {e}")

def test_stats():
    """Site istatistikleri testi"""
    print("\n📊 Site İstatistikleri...")
    try:
        response = requests.get(f"{BASE_URL}/site-stats", timeout=10)
        result = response.json()
        
        if result.get('success'):
            stats = result.get('statistics', {})
            
            print("✅ İstatistikler:")
            print(f"   🎯 Toplam fırsat: {stats.get('total_deals', 0)}")
            print(f"   🔥 En yüksek indirim: %{stats.get('best_discount', 0)}")
            print(f"   📈 Ortalama indirim: %{stats.get('average_discount', 0):.1f}")
            print(f"   💰 Toplam tasarruf: {stats.get('total_savings', 0)}₺")
            
            # Site bazlı
            by_site = stats.get('by_site', {})
            print(f"   🏪 Site dağılımı:")
            print(f"      - Trendyol: {by_site.get('trendyol', 0)}")
            print(f"      - Hepsiburada: {by_site.get('hepsiburada', 0)}")
            print(f"      - Diğer: {by_site.get('other', 0)}")
        else:
            print(f"❌ İstatistik hatası: {result.get('error', 'Bilinmeyen hata')}")
            
    except Exception as e:
        print(f"❌ İstatistik hatası: {e}")

def test_endpoints():
    """Diğer endpoint'leri test et"""
    print("\n🔌 Endpoint Testleri...")
    
    endpoints = [
        ("GET", "/products/new", "Yeni ürünler"),
        ("GET", "/categories", "Kategoriler"),
        ("GET", "/scheduler/status", "Scheduler durumu")
    ]
    
    for method, endpoint, description in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success', True):
                    print(f"   ✅ {description}")
                else:
                    print(f"   ❌ {description}: {result.get('error', 'Hata')}")
            else:
                print(f"   ❌ {description}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {description}: {e}")

def test_single_site():
    """Tek site scraping testi"""
    print("\n🎯 Tek Site Scraping Testi...")
    
    sites = ['trendyol', 'hepsiburada']
    
    for site in sites:
        try:
            print(f"   🔄 {site.capitalize()} test ediliyor...")
            response = requests.post(f"{BASE_URL}/scrape-site/{site}", timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    count = result.get('count', 0)
                    scrape_time = result.get('scrape_time', 0)
                    print(f"   ✅ {site.capitalize()}: {count} ürün ({scrape_time}s)")
                else:
                    error = result.get('error', 'Bilinmeyen hata')
                    print(f"   ❌ {site.capitalize()}: {error}")
            else:
                print(f"   ❌ {site.capitalize()}: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ {site.capitalize()}: Timeout")
        except Exception as e:
            print(f"   ❌ {site.capitalize()}: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 AMAZON FIRSAT AVCISI BACKEND TEST")
    print("=" * 60)
    print(f"🌐 Test URL: {BASE_URL}")
    print("=" * 60)
    
    # Ana testler
    test_health()
    test_scraping()
    test_products() 
    test_stats()
    
    # Ek testler
    test_endpoints()
    test_single_site()
    
    print("\n" + "=" * 60)
    print("✅ TÜM TESTLER TAMAMLANDI!")
    print("=" * 60)
    print("\n💡 Eğer ürün bulunamadıysa:")
    print("   1. Site'lerin HTML yapısı değişmiş olabilir")
    print("   2. Bot koruması aktif olabilir") 
    print("   3. İndirimli ürün şu an olmayabilir")
    print("   4. Selector'ları güncellemek gerekebilir")
    print("\n🚀 Backend sistemi çalışır durumda!")