from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import statistics
from database import Database

class PriceTracker:
    def __init__(self):
        self.db = Database()
    
    def analyze_price_pattern(self, asin: str, days: int = 30) -> Dict:
        """Fiyat desenini analiz et"""
        price_history = self.db.get_price_history(asin, days)
        
        if len(price_history) < 2:
            return {
                'status': 'insufficient_data',
                'price_changes': 0,
                'trend': 'unknown',
                'volatility': 0,
                'suspicious_activity': False
            }
        
        prices = [float(record['price']) for record in price_history]
        dates = [record['recorded_at'] for record in price_history]
        
        # Fiyat değişim sayısı
        price_changes = 0
        for i in range(1, len(prices)):
            if prices[i] != prices[i-1]:
                price_changes += 1
        
        # Genel trend (ilk ve son fiyat karşılaştırması)
        trend = 'stable'
        if prices[-1] > prices[0] * 1.1:
            trend = 'increasing'
        elif prices[-1] < prices[0] * 0.9:
            trend = 'decreasing'
        
        # Volatilite (standart sapma / ortalama)
        if len(prices) > 1:
            volatility = statistics.stdev(prices) / statistics.mean(prices)
        else:
            volatility = 0
        
        # Şüpheli aktivite tespiti
        suspicious_activity = self.detect_suspicious_activity(prices, dates)
        
        return {
            'status': 'analyzed',
            'price_changes': price_changes,
            'trend': trend,
            'volatility': round(volatility, 3),
            'suspicious_activity': suspicious_activity,
            'min_price': min(prices),
            'max_price': max(prices),
            'avg_price': round(statistics.mean(prices), 2),
            'current_price': prices[-1]
        }
    
    def detect_suspicious_activity(self, prices: List[float], dates: List[datetime]) -> bool:
        """Şüpheli fiyat aktivitesi tespit et"""
        if len(prices) < 3:
            return False
        
        # Son 7 günde ani fiyat artışı kontrolü
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_prices = []
        
        for i, date in enumerate(dates):
            if date >= recent_cutoff:
                recent_prices.append(prices[i])
        
        if len(recent_prices) >= 2:
            # %30'dan fazla ani artış var mı?
            for i in range(1, len(recent_prices)):
                increase_ratio = recent_prices[i] / recent_prices[i-1]
                if increase_ratio > 1.3:  # %30+ artış
                    return True
        
        # Fiyat manipülasyonu pattern'i: artış sonrası hemen düşüş
        for i in range(2, len(prices)):
            prev_price = prices[i-2]
            peak_price = prices[i-1]
            curr_price = prices[i]
            
            # Fiyat %40+ artıp sonra %50+ düştüyse şüpheli
            if (peak_price > prev_price * 1.4 and 
                curr_price < peak_price * 0.5):
                return True
        
        return False
    
    def is_genuine_discount(self, asin: str, current_price: float, list_price: float) -> Tuple[bool, str]:
        """Gerçek indirim mi yoksa sahte mi?"""
        if not list_price or list_price <= current_price:
            return False, "Liste fiyatı mevcut fiyattan düşük veya eşit"
        
        discount_percent = ((list_price - current_price) / list_price) * 100
        
        if discount_percent < 70:
            return False, f"İndirim yeterli değil: %{discount_percent:.1f}"
        
        # Liste fiyatı çok abartılı mı?
        if list_price > current_price * 4:
            return False, "Liste fiyatı çok abartılı (4x'den fazla)"
        
        # Fiyat geçmişi analizi
        analysis = self.analyze_price_pattern(asin, days=14)
        
        if analysis['status'] == 'insufficient_data':
            # Yeni ürün, liste fiyatı makul görünüyorsa kabul et
            return True, "Yeni ürün - liste fiyatı makul"
        
        if analysis['suspicious_activity']:
            return False, "Şüpheli fiyat aktivitesi tespit edildi"
        
        # Mevcut fiyat, son 14 günün en düşük fiyatından çok farklı mı?
        min_recent_price = analysis['min_price']
        
        if current_price > min_recent_price * 1.2:
            return False, f"Mevcut fiyat son dönemin minimum fiyatından %20+ yüksek"
        
        # Ortalama fiyat kontrolü
        avg_price = analysis['avg_price']
        if list_price < avg_price * 1.5:
            return False, "Liste fiyatı ortalama fiyattan yeteri kadar yüksek değil"
        
        return True, f"Gerçek indirim: %{discount_percent:.1f}"
    
    def track_price_change(self, asin: str, new_price: float) -> Dict:
        """Fiyat değişikliğini takip et ve analiz et"""
        # Fiyat geçmişine ekle
        success = self.db.add_price_history(asin, new_price)
        
        if not success:
            return {
                'status': 'error',
                'message': 'Fiyat geçmişi kaydedilemedi'
            }
        
        # Son fiyat ile karşılaştır
        recent_history = self.db.get_price_history(asin, days=1)
        
        if len(recent_history) < 2:
            return {
                'status': 'recorded',
                'message': 'İlk fiyat kaydı',
                'price_change': 0,
                'price_change_percent': 0
            }
        
        # Son iki fiyat karşılaştırması
        previous_price = float(recent_history[-2]['price'])
        current_price = float(recent_history[-1]['price'])
        
        price_change = current_price - previous_price
        price_change_percent = (price_change / previous_price) * 100 if previous_price > 0 else 0
        
        return {
            'status': 'recorded',
            'message': 'Fiyat değişikliği kaydedildi',
            'previous_price': previous_price,
            'current_price': current_price,
            'price_change': round(price_change, 2),
            'price_change_percent': round(price_change_percent, 2)
        }
    
    def get_trending_products(self, trend_type: str = 'decreasing', days: int = 7) -> List[Dict]:
        """Trend gösteren ürünleri getir"""
        try:
            # Tüm ürünleri al
            all_deals = self.db.get_big_deals(min_discount=50)  # Daha geniş aralık
            trending_products = []
            
            for product in all_deals:
                asin = product['asin']
                analysis = self.analyze_price_pattern(asin, days)
                
                if analysis['status'] == 'analyzed':
                    if trend_type == 'decreasing' and analysis['trend'] == 'decreasing':
                        product['trend_info'] = analysis
                        trending_products.append(product)
                    elif trend_type == 'increasing' and analysis['trend'] == 'increasing':
                        product['trend_info'] = analysis
                        trending_products.append(product)
                    elif trend_type == 'volatile' and analysis['volatility'] > 0.1:
                        product['trend_info'] = analysis
                        trending_products.append(product)
            
            # Trend gücüne göre sırala
            if trend_type == 'decreasing':
                trending_products.sort(key=lambda x: x['trend_info']['min_price'])
            elif trend_type == 'increasing':
                trending_products.sort(key=lambda x: x['trend_info']['max_price'], reverse=True)
            else:  # volatile
                trending_products.sort(key=lambda x: x['trend_info']['volatility'], reverse=True)
            
            return trending_products[:20]  # En iyi 20 ürün
            
        except Exception as e:
            print(f"Trend analizi hatası: {e}")
            return []
    
    def generate_price_alerts(self, user_preferences: Dict) -> List[Dict]:
        """Kullanıcı tercihlerine göre fiyat alarmları oluştur"""
        alerts = []
        
        try:
            # Kullanıcının istediği kategorilerdeki ürünler
            categories = user_preferences.get('categories', [])
            min_discount = user_preferences.get('min_discount', 70)
            min_price = user_preferences.get('min_price', 10)
            max_price = user_preferences.get('max_price', 10000)
            
            for category in categories:
                deals = self.db.get_big_deals(min_discount=min_discount, category=category)
                
                for deal in deals:
                    current_price = float(deal['current_price'])
                    
                    # Fiyat aralığı kontrolü
                    if min_price <= current_price <= max_price:
                        # Gerçek indirim kontrolü
                        is_genuine, reason = self.is_genuine_discount(
                            deal['asin'], 
                            current_price, 
                            float(deal['list_price'])
                        )
                        
                        if is_genuine:
                            alerts.append({
                                'asin': deal['asin'],
                                'title': deal['title'],
                                'current_price': current_price,
                                'list_price': float(deal['list_price']),
                                'discount_percent': deal['discount_percent'],
                                'category': deal['category'],
                                'product_url': deal['product_url'],
                                'image_url': deal['image_url'],
                                'reason': reason,
                                'alert_type': 'genuine_deal'
                            })
            
            return alerts
            
        except Exception as e:
            print(f"Fiyat alarm oluşturma hatası: {e}")
            return []
    
    def cleanup_old_price_history(self, days_to_keep: int = 90):
        """Eski fiyat geçmişi kayıtlarını temizle"""
        cursor = self.db.conn.cursor()
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            cursor.execute("""
                DELETE FROM price_history 
                WHERE recorded_at < %s
            """, (cutoff_date,))
            
            deleted_count = cursor.rowcount
            print(f"{deleted_count} eski fiyat kaydı silindi")
            
            return deleted_count
            
        except Exception as e:
            print(f"Eski kayıtları temizleme hatası: {e}")
            return 0
        finally:
            cursor.close()
    
    def get_price_statistics(self) -> Dict:
        """Genel fiyat istatistikleri"""
        cursor = self.db.conn.cursor()
        
        try:
            # Toplam fiyat kaydı sayısı
            cursor.execute("SELECT COUNT(*) FROM price_history")
            total_records = cursor.fetchone()[0]
            
            # Son 24 saatteki kayıt sayısı
            cursor.execute("""
                SELECT COUNT(*) FROM price_history 
                WHERE recorded_at >= %s
            """, (datetime.now() - timedelta(hours=24),))
            recent_records = cursor.fetchone()[0]
            
            # Ortalama indirim yüzdesi
            cursor.execute("SELECT AVG(discount_percent) FROM products")
            avg_discount = cursor.fetchone()[0] or 0
            
            # En yüksek indirim
            cursor.execute("SELECT MAX(discount_percent) FROM products")
            max_discount = cursor.fetchone()[0] or 0
            
            # Aktif ürün sayısı
            cursor.execute("SELECT COUNT(*) FROM products")
            active_products = cursor.fetchone()[0]
            
            return {
                'total_price_records': total_records,
                'recent_price_records': recent_records,
                'average_discount': round(float(avg_discount), 2),
                'max_discount': max_discount,
                'active_products': active_products,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"İstatistik oluşturma hatası: {e}")
            return {}
        finally:
            cursor.close()

# Test fonksiyonu
if __name__ == "__main__":
    tracker = PriceTracker()
    
    # İstatistikleri göster
    stats = tracker.get_price_statistics()
    print("=== FIYAT TRACKER İSTATİSTİKLERİ ===")
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Trend analizi örneği
    trending = tracker.get_trending_products('decreasing', days=7)
    print(f"\nFiyatı düşen {len(trending)} ürün bulundu")
    
    # Eski kayıtları temizle
    cleaned = tracker.cleanup_old_price_history(days_to_keep=60)
    print(f"{cleaned} eski kayıt temizlendi")