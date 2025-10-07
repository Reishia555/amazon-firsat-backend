from .trendyol_scraper import TrendyolScraper
from .hepsiburada_scraper import HepsiburadaScraper
from typing import List, Dict, Tuple
from database import Database
import time

class MainScraper:
    """Tüm site scraper'larını yönetir"""
    
    def __init__(self):
        self.db = Database()
        self.trendyol_scraper = TrendyolScraper()
        self.hepsiburada_scraper = HepsiburadaScraper()
    
    def scrape_all_sites(self) -> Tuple[List[Dict], Dict]:
        """Tüm siteleri scrape et"""
        print("🚀 MULTI-SITE SCRAPING BAŞLIYOR")
        print("=" * 50)
        
        results = {
            'trendyol': {
                'products': [],
                'count': 0,
                'success': False,
                'error': None
            },
            'hepsiburada': {
                'products': [],
                'count': 0,
                'success': False,
                'error': None
            },
            'total_products': 0,
            'total_saved': 0,
            'scrape_time': 0,
            'errors': []
        }
        
        start_time = time.time()
        all_products = []
        
        # 1. Trendyol scraping
        try:
            print("\n🛍️ TRENDYOL SCRAPING")
            trendyol_products = self.trendyol_scraper.scrape(max_pages=2)
            
            results['trendyol']['products'] = trendyol_products
            results['trendyol']['count'] = len(trendyol_products)
            results['trendyol']['success'] = True
            
            all_products.extend(trendyol_products)
            print(f"✅ Trendyol: {len(trendyol_products)} ürün bulundu")
            
        except Exception as e:
            error_msg = f"Trendyol scraping hatası: {str(e)}"
            results['trendyol']['error'] = error_msg
            results['errors'].append(error_msg)
            print(f"❌ Trendyol hatası: {e}")
        
        # Site'ler arası bekleme
        time.sleep(5)
        
        # 2. Hepsiburada scraping
        try:
            print("\n🛒 HEPSIBURADA SCRAPING")
            hepsiburada_products = self.hepsiburada_scraper.scrape(max_pages=2)
            
            results['hepsiburada']['products'] = hepsiburada_products
            results['hepsiburada']['count'] = len(hepsiburada_products)
            results['hepsiburada']['success'] = True
            
            all_products.extend(hepsiburada_products)
            print(f"✅ Hepsiburada: {len(hepsiburada_products)} ürün bulundu")
            
        except Exception as e:
            error_msg = f"Hepsiburada scraping hatası: {str(e)}"
            results['hepsiburada']['error'] = error_msg
            results['errors'].append(error_msg)
            print(f"❌ Hepsiburada hatası: {e}")
        
        # 3. Veritabanına kaydet
        saved_count = 0
        print(f"\n💾 {len(all_products)} ürün veritabanına kaydediliyor...")
        
        for product in all_products:
            try:
                if self.db.add_product(product):
                    self.db.add_price_history(product['asin'], product['current_price'])
                    saved_count += 1
            except Exception as e:
                error_msg = f"DB kaydetme hatası: {str(e)}"
                results['errors'].append(error_msg)
                print(f"❌ DB hatası: {e}")
        
        # 4. Sonuçları tamamla
        end_time = time.time()
        results['total_products'] = len(all_products)
        results['total_saved'] = saved_count
        results['scrape_time'] = round(end_time - start_time, 2)
        
        print(f"\n🎯 SCRAPING TAMAMLANDI")
        print(f"📊 Toplam ürün: {results['total_products']}")
        print(f"💾 Kaydedilen: {results['total_saved']}")
        print(f"⏱️ Süre: {results['scrape_time']} saniye")
        print(f"❌ Hata sayısı: {len(results['errors'])}")
        
        return all_products, results
    
    def get_site_statistics(self) -> Dict:
        """Site bazlı istatistikler"""
        try:
            # Tüm ürünleri al
            all_deals = self.db.get_big_deals(min_discount=40)
            
            stats = {
                'total_deals': len(all_deals),
                'by_site': {
                    'trendyol': 0,
                    'hepsiburada': 0,
                    'other': 0
                },
                'best_discount': 0,
                'average_discount': 0,
                'total_savings': 0
            }
            
            trendyol_count = 0
            hepsiburada_count = 0
            other_count = 0
            total_savings = 0
            
            for deal in all_deals:
                # Site belirleme (URL'den)
                product_url = deal.get('product_url', '')
                if 'trendyol.com' in product_url:
                    trendyol_count += 1
                elif 'hepsiburada.com' in product_url:
                    hepsiburada_count += 1
                else:
                    other_count += 1
                
                # Tasarruf hesaplama
                current_price = float(deal['current_price'])
                list_price = float(deal['list_price'])
                saving = list_price - current_price
                total_savings += saving
            
            stats['by_site']['trendyol'] = trendyol_count
            stats['by_site']['hepsiburada'] = hepsiburada_count
            stats['by_site']['other'] = other_count
            
            if all_deals:
                stats['best_discount'] = max(deal['discount_percent'] for deal in all_deals)
                stats['average_discount'] = sum(deal['discount_percent'] for deal in all_deals) / len(all_deals)
                stats['total_savings'] = round(total_savings, 2)
            
            return stats
            
        except Exception as e:
            print(f"İstatistik hatası: {e}")
            return {
                'total_deals': 0,
                'by_site': {'trendyol': 0, 'hepsiburada': 0, 'other': 0},
                'best_discount': 0,
                'average_discount': 0,
                'total_savings': 0
            }
    
    def scrape_single_site(self, site_name: str) -> Tuple[List[Dict], Dict]:
        """Tek site scraping"""
        results = {
            'site': site_name,
            'products': [],
            'count': 0,
            'success': False,
            'error': None,
            'scrape_time': 0
        }
        
        start_time = time.time()
        
        try:
            if site_name.lower() == 'trendyol':
                products = self.trendyol_scraper.scrape(max_pages=2)
            elif site_name.lower() == 'hepsiburada':
                products = self.hepsiburada_scraper.scrape(max_pages=2)
            else:
                raise ValueError(f"Bilinmeyen site: {site_name}")
            
            # Veritabanına kaydet
            saved_count = 0
            for product in products:
                try:
                    if self.db.add_product(product):
                        self.db.add_price_history(product['asin'], product['current_price'])
                        saved_count += 1
                except Exception as e:
                    print(f"DB kaydetme hatası: {e}")
            
            results['products'] = products
            results['count'] = len(products)
            results['success'] = True
            results['saved_count'] = saved_count
            
        except Exception as e:
            results['error'] = str(e)
            print(f"❌ {site_name} scraping hatası: {e}")
        
        results['scrape_time'] = round(time.time() - start_time, 2)
        return results['products'], results

# Test fonksiyonu
if __name__ == "__main__":
    main_scraper = MainScraper()
    
    print("🧪 MULTI-SITE SCRAPER TEST")
    print("=" * 50)
    
    # Tüm siteleri test et
    all_products, results = main_scraper.scrape_all_sites()
    
    print("\n📊 TEST SONUÇLARI:")
    print(f"Trendyol: {results['trendyol']['count']} ürün ({'✅' if results['trendyol']['success'] else '❌'})")
    print(f"Hepsiburada: {results['hepsiburada']['count']} ürün ({'✅' if results['hepsiburada']['success'] else '❌'})")
    print(f"Toplam: {results['total_products']} ürün")
    print(f"Kaydedilen: {results['total_saved']} ürün")
    print(f"Süre: {results['scrape_time']} saniye")
    
    if results['errors']:
        print(f"\n❌ Hatalar ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"  - {error}")
    
    # İstatistikler
    stats = main_scraper.get_site_statistics()
    print(f"\n📈 İSTATİSTİKLER:")
    print(f"Toplam fırsat: {stats['total_deals']}")
    print(f"Trendyol: {stats['by_site']['trendyol']}")
    print(f"Hepsiburada: {stats['by_site']['hepsiburada']}")
    print(f"En yüksek indirim: %{stats['best_discount']}")
    print(f"Ortalama indirim: %{stats['average_discount']:.1f}")
    print(f"Toplam tasarruf: {stats['total_savings']}₺")