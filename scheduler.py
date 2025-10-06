import os
import time
import threading
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from amazon_scraper import AmazonScraper
from price_tracker import PriceTracker
from notifier import NotificationManager
from database import Database
from dotenv import load_dotenv

load_dotenv()

class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scraper = AmazonScraper()
        self.price_tracker = PriceTracker()
        self.notification_manager = NotificationManager()
        self.db = Database()
        
        # Son çalışma zamanları
        self.last_scrape_time = None
        self.last_notification_time = None
        self.last_cleanup_time = None
        
        # Çalışma durumu
        self.is_running = False
        
        self.setup_jobs()
    
    def log_message(self, message: str, level: str = "INFO"):
        """Log mesajı yazdır"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def scrape_amazon_deals(self):
        """Amazon fırsatlarını scrape et"""
        try:
            self.log_message("Amazon fırsat taraması başlıyor...")
            start_time = time.time()
            
            # Scraping yap
            deals = self.scraper.scrape_all_deals()
            
            end_time = time.time()
            duration = end_time - start_time
            
            self.log_message(f"✓ Scraping tamamlandı: {len(deals)} fırsat, {duration:.1f} saniye")
            self.last_scrape_time = datetime.now()
            
            # Yeni büyük fırsatları kontrol et ve bildirim gönder
            self.check_and_notify_new_deals()
            
        except Exception as e:
            self.log_message(f"✗ Scraping hatası: {e}", "ERROR")
    
    def check_and_notify_new_deals(self):
        """Yeni fırsatları kontrol et ve bildirim gönder"""
        try:
            self.log_message("Yeni fırsatlar kontrol ediliyor...")
            
            # Son 2 saatte bulunan yeni fırsatlar
            new_deals = self.db.get_new_deals(hours=2)
            
            if not new_deals:
                self.log_message("Yeni fırsat bulunamadı")
                return
            
            # Gerçek fırsatları filtrele
            genuine_deals = []
            for deal in new_deals:
                if not self.db.is_fake_discount(deal['asin']):
                    genuine_deals.append(deal)
            
            if not genuine_deals:
                self.log_message(f"{len(new_deals)} yeni fırsat bulundu ancak hepsi sahte")
                return
            
            self.log_message(f"{len(genuine_deals)} gerçek yeni fırsat bulundu")
            
            # En iyi fırsatları seç (en yüksek indirimli ilk 5)
            top_deals = sorted(genuine_deals, key=lambda x: x['discount_percent'], reverse=True)[:5]
            
            # Bildirimleri hazırla ve gönder
            notifications = []
            for deal in top_deals:
                notifications.append({
                    'type': 'deal',
                    'product_data': {
                        'asin': deal['asin'],
                        'title': deal['title'],
                        'current_price': float(deal['current_price']),
                        'list_price': float(deal['list_price']),
                        'discount_percent': deal['discount_percent'],
                        'category': deal['category'],
                        'product_url': deal['product_url'],
                        'image_url': deal['image_url']
                    }
                })
            
            # Toplu bildirim gönder
            if notifications:
                result = self.notification_manager.send_bulk_notifications_sync(notifications)
                
                if result['success']:
                    self.log_message(f"✓ {result['sent_count']} bildirim gönderildi")
                    self.last_notification_time = datetime.now()
                else:
                    self.log_message(f"✗ Bildirim gönderme hatası: {result['message']}", "ERROR")
            
        except Exception as e:
            self.log_message(f"✗ Yeni fırsat kontrol hatası: {e}", "ERROR")
    
    def track_price_changes(self):
        """Fiyat değişikliklerini takip et"""
        try:
            self.log_message("Fiyat değişiklikleri takip ediliyor...")
            
            # Son 24 saatte güncellenmiş tüm ürünler
            cursor = self.db.conn.cursor()
            cursor.execute("""
                SELECT asin, current_price, title, category, product_url, image_url
                FROM products 
                WHERE last_updated >= %s
                ORDER BY last_updated DESC
            """, (datetime.now() - timedelta(hours=24),))
            
            updated_products = cursor.fetchall()
            cursor.close()
            
            price_drop_notifications = []
            
            for product in updated_products:
                asin = product[0]
                current_price = float(product[1])
                
                # Son 2 fiyat kaydını al
                price_history = self.db.get_price_history(asin, days=2)
                
                if len(price_history) >= 2:
                    # Önceki fiyat ile karşılaştır
                    previous_price = float(price_history[-2]['price'])
                    
                    # %10'dan fazla düşüş varsa bildirim hazırla
                    if current_price < previous_price * 0.9:
                        price_drop_notifications.append({
                            'type': 'price_drop',
                            'product_data': {
                                'asin': asin,
                                'title': product[2],
                                'current_price': current_price,
                                'category': product[3],
                                'product_url': product[4],
                                'image_url': product[5]
                            },
                            'old_price': previous_price
                        })
            
            if price_drop_notifications:
                # En büyük düşüşleri seç (ilk 3)
                price_drop_notifications.sort(
                    key=lambda x: (x['old_price'] - x['product_data']['current_price']) / x['old_price'], 
                    reverse=True
                )
                top_drops = price_drop_notifications[:3]
                
                result = self.notification_manager.send_bulk_notifications_sync(top_drops)
                
                if result['success']:
                    self.log_message(f"✓ {len(top_drops)} fiyat düşüşü bildirimi gönderildi")
                else:
                    self.log_message(f"✗ Fiyat düşüşü bildirimi hatası: {result['message']}", "ERROR")
            else:
                self.log_message("Önemli fiyat düşüşü bulunamadı")
                
        except Exception as e:
            self.log_message(f"✗ Fiyat takip hatası: {e}", "ERROR")
    
    def cleanup_old_data(self):
        """Eski verileri temizle"""
        try:
            self.log_message("Eski veriler temizleniyor...")
            
            # 90 günden eski fiyat geçmişini sil
            cleaned_count = self.price_tracker.cleanup_old_price_history(days_to_keep=90)
            
            # 30 günden eski olan ve hiç güncellenmeyen ürünleri sil
            cursor = self.db.conn.cursor()
            cursor.execute("""
                DELETE FROM products 
                WHERE last_updated < %s
            """, (datetime.now() - timedelta(days=30),))
            
            deleted_products = cursor.rowcount
            cursor.close()
            
            self.log_message(f"✓ Temizlik tamamlandı: {cleaned_count} fiyat kaydı, {deleted_products} eski ürün silindi")
            self.last_cleanup_time = datetime.now()
            
        except Exception as e:
            self.log_message(f"✗ Veri temizleme hatası: {e}", "ERROR")
    
    def health_check(self):
        """Sistem sağlık kontrolü"""
        try:
            # Veritabanı bağlantısını test et
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM products")
            product_count = cursor.fetchone()[0]
            cursor.close()
            
            # Bildirim sistemini test et
            notification_stats = self.notification_manager.apns_notifier.get_notification_stats()
            
            self.log_message(f"Sağlık kontrolü: {product_count} ürün, APNS: {notification_stats['apns_configured']}")
            
        except Exception as e:
            self.log_message(f"✗ Sağlık kontrolü hatası: {e}", "ERROR")
    
    def get_status(self) -> dict:
        """Scheduler durumunu döndür"""
        running_jobs = [job.id for job in self.scheduler.get_jobs()]
        
        return {
            'is_running': self.is_running,
            'jobs': running_jobs,
            'last_scrape_time': self.last_scrape_time.isoformat() if self.last_scrape_time else None,
            'last_notification_time': self.last_notification_time.isoformat() if self.last_notification_time else None,
            'last_cleanup_time': self.last_cleanup_time.isoformat() if self.last_cleanup_time else None,
            'next_run_time': {
                job.id: job.next_run_time.isoformat() if job.next_run_time else None 
                for job in self.scheduler.get_jobs()
            }
        }
    
    def setup_jobs(self):
        """Zamanlanmış görevleri ayarla"""
        # Ana scraping görevi - her saat başı
        self.scheduler.add_job(
            func=self.scrape_amazon_deals,
            trigger=CronTrigger(minute=0),  # Her saat başında
            id='scrape_deals',
            name='Amazon Fırsat Taraması',
            max_instances=1,
            replace_existing=True
        )
        
        # Fiyat değişikliği takibi - her 30 dakikada
        self.scheduler.add_job(
            func=self.track_price_changes,
            trigger=IntervalTrigger(minutes=30),
            id='track_prices',
            name='Fiyat Değişikliği Takibi',
            max_instances=1,
            replace_existing=True
        )
        
        # Veri temizleme - her gün gece 02:00'da
        self.scheduler.add_job(
            func=self.cleanup_old_data,
            trigger=CronTrigger(hour=2, minute=0),
            id='cleanup_data',
            name='Veri Temizleme',
            max_instances=1,
            replace_existing=True
        )
        
        # Sağlık kontrolü - her 15 dakikada
        self.scheduler.add_job(
            func=self.health_check,
            trigger=IntervalTrigger(minutes=15),
            id='health_check',
            name='Sağlık Kontrolü',
            max_instances=1,
            replace_existing=True
        )
        
        self.log_message("Zamanlanmış görevler ayarlandı")
    
    def start(self):
        """Scheduler'ı başlat"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            self.log_message("🚀 Scheduler başlatıldı")
            
            # İlk scraping'i hemen yap
            threading.Thread(target=self.scrape_amazon_deals, daemon=True).start()
        else:
            self.log_message("Scheduler zaten çalışıyor")
    
    def stop(self):
        """Scheduler'ı durdur"""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            self.log_message("🛑 Scheduler durduruldu")
        else:
            self.log_message("Scheduler zaten durmuş")
    
    def restart(self):
        """Scheduler'ı yeniden başlat"""
        self.log_message("Scheduler yeniden başlatılıyor...")
        self.stop()
        time.sleep(2)
        self.start()

# Uygulama başlatıldığında scheduler'ı başlat
scheduler_instance = None

def init_scheduler():
    """Global scheduler instance'ını oluştur ve başlat"""
    global scheduler_instance
    if scheduler_instance is None:
        scheduler_instance = TaskScheduler()
        scheduler_instance.start()
    return scheduler_instance

def get_scheduler():
    """Global scheduler instance'ını döndür"""
    global scheduler_instance
    return scheduler_instance

# Test fonksiyonu
if __name__ == "__main__":
    scheduler = TaskScheduler()
    
    try:
        scheduler.start()
        
        print("Scheduler çalışıyor. Durdurmak için Ctrl+C'ye basın...")
        
        # Durum bilgilerini periyodik göster
        while True:
            time.sleep(60)  # 1 dakika bekle
            status = scheduler.get_status()
            print(f"\n=== SCHEDULER DURUMU ===")
            print(f"Çalışıyor: {status['is_running']}")
            print(f"Aktif görevler: {', '.join(status['jobs'])}")
            if status['last_scrape_time']:
                print(f"Son scraping: {status['last_scrape_time']}")
            if status['last_notification_time']:
                print(f"Son bildirim: {status['last_notification_time']}")
            
    except KeyboardInterrupt:
        print("\nÇıkış yapılıyor...")
        scheduler.stop()
        print("Scheduler durduruldu")