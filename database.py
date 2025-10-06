import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.database_url = os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.conn = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """PostgreSQL veritabanına bağlan"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.conn.autocommit = True
            print("PostgreSQL veritabanına başarıyla bağlanıldı")
        except Exception as e:
            print(f"Veritabanı bağlantı hatası: {e}")
            raise
    
    def create_tables(self):
        """Gerekli tabloları oluştur"""
        cursor = self.conn.cursor()
        
        try:
            # Products tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    asin VARCHAR(20) UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    current_price DECIMAL(10,2) NOT NULL,
                    list_price DECIMAL(10,2) NOT NULL,
                    discount_percent INTEGER NOT NULL,
                    image_url TEXT,
                    product_url TEXT NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Price history tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id SERIAL PRIMARY KEY,
                    asin VARCHAR(20) NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (asin) REFERENCES products(asin) ON DELETE CASCADE
                )
            """)
            
            # User preferences tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id SERIAL PRIMARY KEY,
                    device_token VARCHAR(255) UNIQUE NOT NULL,
                    min_discount INTEGER DEFAULT 70,
                    categories JSONB DEFAULT '[]',
                    min_price DECIMAL(10,2) DEFAULT 10.00,
                    max_price DECIMAL(10,2) DEFAULT 10000.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index'ler oluştur
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_asin ON products(asin)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_discount ON products(discount_percent)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_asin ON price_history(asin)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(recorded_at)")
            
            print("Veritabanı tabloları başarıyla oluşturuldu")
            
        except Exception as e:
            print(f"Tablo oluşturma hatası: {e}")
            raise
        finally:
            cursor.close()
    
    def add_product(self, product_data: Dict) -> bool:
        """Yeni ürün ekle veya mevcut ürünü güncelle"""
        cursor = self.conn.cursor()
        
        try:
            # Önce ürün var mı kontrol et
            cursor.execute("SELECT id FROM products WHERE asin = %s", (product_data['asin'],))
            existing = cursor.fetchone()
            
            if existing:
                # Mevcut ürünü güncelle
                cursor.execute("""
                    UPDATE products SET 
                        title = %s,
                        current_price = %s,
                        list_price = %s,
                        discount_percent = %s,
                        image_url = %s,
                        product_url = %s,
                        category = %s,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE asin = %s
                """, (
                    product_data['title'],
                    product_data['current_price'],
                    product_data['list_price'],
                    product_data['discount_percent'],
                    product_data['image_url'],
                    product_data['product_url'],
                    product_data['category'],
                    product_data['asin']
                ))
                print(f"Ürün güncellendi: {product_data['asin']}")
            else:
                # Yeni ürün ekle
                cursor.execute("""
                    INSERT INTO products (asin, title, current_price, list_price, 
                                        discount_percent, image_url, product_url, category)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    product_data['asin'],
                    product_data['title'],
                    product_data['current_price'],
                    product_data['list_price'],
                    product_data['discount_percent'],
                    product_data['image_url'],
                    product_data['product_url'],
                    product_data['category']
                ))
                print(f"Yeni ürün eklendi: {product_data['asin']}")
            
            return True
            
        except Exception as e:
            print(f"Ürün ekleme/güncelleme hatası: {e}")
            return False
        finally:
            cursor.close()
    
    def add_price_history(self, asin: str, price: float) -> bool:
        """Fiyat geçmişine yeni kayıt ekle"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO price_history (asin, price)
                VALUES (%s, %s)
            """, (asin, price))
            
            return True
            
        except Exception as e:
            print(f"Fiyat geçmişi ekleme hatası: {e}")
            return False
        finally:
            cursor.close()
    
    def get_price_history(self, asin: str, days: int = 30) -> List[Dict]:
        """Belirtilen ASIN için son X günlük fiyat geçmişi"""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT price, recorded_at
                FROM price_history
                WHERE asin = %s AND recorded_at >= %s
                ORDER BY recorded_at ASC
            """, (asin, datetime.now() - timedelta(days=days)))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            print(f"Fiyat geçmişi getirme hatası: {e}")
            return []
        finally:
            cursor.close()
    
    def is_fake_discount(self, asin: str) -> bool:
        """Sahte indirim tespiti - son 7 günde fiyat artmış mı?"""
        cursor = self.conn.cursor()
        
        try:
            # Son 7 günlük fiyat geçmişini al
            cursor.execute("""
                SELECT price, recorded_at
                FROM price_history
                WHERE asin = %s AND recorded_at >= %s
                ORDER BY recorded_at ASC
            """, (asin, datetime.now() - timedelta(days=7)))
            
            prices = cursor.fetchall()
            
            if len(prices) < 2:
                return False
            
            # Fiyat artışı var mı kontrol et
            for i in range(1, len(prices)):
                prev_price = float(prices[i-1][0])
                curr_price = float(prices[i][0])
                
                # %20'den fazla artış varsa şüpheli
                if curr_price > prev_price * 1.2:
                    return True
            
            # Liste fiyatı mantıklı mı kontrol et
            cursor.execute("""
                SELECT current_price, list_price
                FROM products
                WHERE asin = %s
            """, (asin,))
            
            product = cursor.fetchone()
            if product:
                current_price = float(product[0])
                list_price = float(product[1])
                
                # Liste fiyatı, mevcut fiyatın 3 katından fazlaysa şüpheli
                if list_price > current_price * 3:
                    return True
            
            return False
            
        except Exception as e:
            print(f"Sahte indirim tespiti hatası: {e}")
            return False
        finally:
            cursor.close()
    
    def get_big_deals(self, min_discount: int = 70, category: str = None) -> List[Dict]:
        """Büyük indirimleri getir (sahte olmayan)"""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            query = """
                SELECT * FROM products
                WHERE discount_percent >= %s
            """
            params = [min_discount]
            
            if category:
                query += " AND category = %s"
                params.append(category)
            
            query += " ORDER BY discount_percent DESC, last_updated DESC"
            
            cursor.execute(query, params)
            products = [dict(row) for row in cursor.fetchall()]
            
            # Sahte indirimleri filtrele
            real_deals = []
            for product in products:
                if not self.is_fake_discount(product['asin']):
                    real_deals.append(product)
            
            return real_deals
            
        except Exception as e:
            print(f"Fırsatları getirme hatası: {e}")
            return []
        finally:
            cursor.close()
    
    def get_new_deals(self, hours: int = 1) -> List[Dict]:
        """Son X saatte bulunan yeni fırsatlar"""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT * FROM products
                WHERE first_seen >= %s AND discount_percent >= 70
                ORDER BY discount_percent DESC
            """, (datetime.now() - timedelta(hours=hours),))
            
            products = [dict(row) for row in cursor.fetchall()]
            
            # Sahte indirimleri filtrele
            real_deals = []
            for product in products:
                if not self.is_fake_discount(product['asin']):
                    real_deals.append(product)
            
            return real_deals
            
        except Exception as e:
            print(f"Yeni fırsatları getirme hatası: {e}")
            return []
        finally:
            cursor.close()
    
    def save_device_token(self, device_token: str, preferences: Dict = None) -> bool:
        """Cihaz token'ı ve tercihlerini kaydet"""
        cursor = self.conn.cursor()
        
        try:
            # Varsayılan tercihler
            if not preferences:
                preferences = {
                    'min_discount': 70,
                    'categories': ['Bilgisayarlar', 'Elektronik', 'Ev & Mutfak', 'Spor', 'Oyun'],
                    'min_price': 10.0,
                    'max_price': 10000.0
                }
            
            # Token zaten var mı kontrol et
            cursor.execute("SELECT id FROM user_preferences WHERE device_token = %s", (device_token,))
            existing = cursor.fetchone()
            
            if existing:
                # Mevcut tercihleri güncelle
                cursor.execute("""
                    UPDATE user_preferences SET
                        min_discount = %s,
                        categories = %s,
                        min_price = %s,
                        max_price = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE device_token = %s
                """, (
                    preferences['min_discount'],
                    json.dumps(preferences['categories']),
                    preferences['min_price'],
                    preferences['max_price'],
                    device_token
                ))
            else:
                # Yeni kullanıcı ekle
                cursor.execute("""
                    INSERT INTO user_preferences (device_token, min_discount, categories, min_price, max_price)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    device_token,
                    preferences['min_discount'],
                    json.dumps(preferences['categories']),
                    preferences['min_price'],
                    preferences['max_price']
                ))
            
            return True
            
        except Exception as e:
            print(f"Device token kaydetme hatası: {e}")
            return False
        finally:
            cursor.close()
    
    def get_all_device_tokens(self) -> List[str]:
        """Tüm kayıtlı cihaz token'larını getir"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("SELECT device_token FROM user_preferences")
            tokens = [row[0] for row in cursor.fetchall()]
            return tokens
            
        except Exception as e:
            print(f"Device token'ları getirme hatası: {e}")
            return []
        finally:
            cursor.close()
    
    def close(self):
        """Veritabanı bağlantısını kapat"""
        if self.conn:
            self.conn.close()
            print("Veritabanı bağlantısı kapatıldı")