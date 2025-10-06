import requests
from bs4 import BeautifulSoup
import time
import re
from typing import List, Dict, Optional
import random
from urllib.parse import urljoin, urlparse
from database import Database

class AmazonScraper:
    def __init__(self):
        self.base_url = "https://www.amazon.com.tr"
        self.deals_url = "https://www.amazon.com.tr/gp/goldbox"
        self.session = requests.Session()
        
        # User-Agent rotasyonu için liste
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
        ]
        
        # İzin verilen kategoriler
        self.allowed_categories = [
            'Bilgisayarlar',
            'Elektronik', 
            'Ev & Mutfak',
            'Spor',
            'Oyun'
        ]
        
        # Fiyat aralığı
        self.min_price = 10.0
        self.max_price = 10000.0
        
        self.db = Database()
    
    def get_random_headers(self) -> Dict[str, str]:
        """Random User-Agent ve headers döndür"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
    
    def make_request(self, url: str, retries: int = 3) -> Optional[requests.Response]:
        """Güvenli HTTP request yap"""
        for attempt in range(retries):
            try:
                headers = self.get_random_headers()
                response = self.session.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 503:
                    print(f"503 hatası, {attempt + 1}. deneme...")
                    time.sleep(random.uniform(5, 10))
                else:
                    print(f"HTTP {response.status_code} hatası: {url}")
                    
            except Exception as e:
                print(f"Request hatası (deneme {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(random.uniform(3, 7))
        
        return None
    
    def extract_price(self, price_text: str) -> Optional[float]:
        """Fiyat metninden sayısal değer çıkar"""
        if not price_text:
            return None
        
        # Türkçe fiyat formatını temizle
        price_text = price_text.replace('₺', '').replace('TL', '').replace('.', '').replace(',', '.')
        price_text = re.sub(r'[^\d,.]', '', price_text)
        
        try:
            # Virgül ile nokta karışıklığını düzelt
            if ',' in price_text and '.' in price_text:
                # 1.234,56 formatı
                price_text = price_text.replace('.', '').replace(',', '.')
            elif ',' in price_text:
                # 1234,56 formatı
                price_text = price_text.replace(',', '.')
            
            price = float(price_text)
            return price if self.min_price <= price <= self.max_price else None
            
        except ValueError:
            return None
    
    def extract_asin(self, product_url: str) -> Optional[str]:
        """Ürün URL'sinden ASIN çıkar"""
        if not product_url:
            return None
        
        # ASIN pattern'leri
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'asin=([A-Z0-9]{10})',
            r'/([A-Z0-9]{10})(?:/|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, product_url)
            if match:
                return match.group(1)
        
        return None
    
    def categorize_product(self, title: str, breadcrumb: str = "") -> Optional[str]:
        """Ürün başlığı ve breadcrumb'dan kategori belirle"""
        text = (title + " " + breadcrumb).lower()
        
        # Kategori anahtar kelimeleri
        category_keywords = {
            'Bilgisayarlar': ['laptop', 'bilgisayar', 'pc', 'masaüstü', 'notebook', 'ultrabook', 'macbook', 'imac'],
            'Elektronik': ['telefon', 'tablet', 'tv', 'televizyon', 'kulaklık', 'speaker', 'bluetooth', 'şarj', 'kamera', 'fotoğraf', 'ses', 'müzik'],
            'Ev & Mutfak': ['mutfak', 'ev', 'banyo', 'yatak', 'masa', 'sandalye', 'dolap', 'dekorasyon', 'aydınlatma', 'temizlik'],
            'Spor': ['spor', 'fitness', 'koşu', 'futbol', 'basketbol', 'yoga', 'gym', 'antrenman', 'bisiklet'],
            'Oyun': ['oyun', 'game', 'playstation', 'xbox', 'nintendo', 'ps5', 'ps4', 'konsol', 'joystick']
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return None
    
    def calculate_discount_percent(self, current_price: float, list_price: float) -> int:
        """İndirim yüzdesini hesapla"""
        if not list_price or list_price <= current_price:
            return 0
        
        discount = ((list_price - current_price) / list_price) * 100
        return int(discount)
    
    def scrape_product_details(self, product_element) -> Optional[Dict]:
        """Tek bir ürün elementinden detayları çıkar"""
        try:
            product_data = {}
            
            # Başlık
            title_element = product_element.find(['h3', 'h4', 'h5'], class_=re.compile(r'.*title.*|.*name.*'))
            if not title_element:
                title_element = product_element.find('a', {'data-testid': re.compile(r'.*title.*')})
            
            if title_element:
                product_data['title'] = title_element.get_text(strip=True)
            else:
                return None
            
            # Ürün linki
            link_element = product_element.find('a', href=True)
            if link_element:
                href = link_element['href']
                if href.startswith('/'):
                    product_data['product_url'] = urljoin(self.base_url, href)
                else:
                    product_data['product_url'] = href
            else:
                return None
            
            # ASIN çıkar
            asin = self.extract_asin(product_data['product_url'])
            if not asin:
                return None
            product_data['asin'] = asin
            
            # Fiyatlar
            current_price = None
            list_price = None
            
            # Mevcut fiyat
            price_elements = product_element.find_all(string=re.compile(r'[₺TL]'))
            prices = []
            
            for price_element in price_elements:
                price = self.extract_price(price_element)
                if price:
                    prices.append(price)
            
            if len(prices) >= 2:
                # İki fiyat varsa, küçük olanı mevcut, büyük olanı liste fiyatı
                prices.sort()
                current_price = prices[0]
                list_price = prices[-1]
            elif len(prices) == 1:
                # Tek fiyat varsa liste fiyatını CSS selector'larla ara
                current_price = prices[0]
                
                # Liste fiyatı için farklı selector'lar dene
                list_price_selectors = [
                    '.a-price.a-text-price .a-offscreen',
                    '.a-text-strike .a-offscreen',
                    '[data-testid="list-price"] .a-offscreen',
                    '.a-text-strike',
                    '.a-price-was'
                ]
                
                for selector in list_price_selectors:
                    list_price_element = product_element.select_one(selector)
                    if list_price_element:
                        list_price = self.extract_price(list_price_element.get_text())
                        if list_price and list_price > current_price:
                            break
            
            if not current_price or not list_price:
                return None
            
            product_data['current_price'] = current_price
            product_data['list_price'] = list_price
            
            # İndirim yüzdesi hesapla
            discount_percent = self.calculate_discount_percent(current_price, list_price)
            if discount_percent < 70:  # Minimum %70 indirim
                return None
            
            product_data['discount_percent'] = discount_percent
            
            # Kategori belirle
            category = self.categorize_product(product_data['title'])
            if not category:
                return None
            
            product_data['category'] = category
            
            # Resim URL
            img_element = product_element.find('img')
            if img_element:
                src = img_element.get('src') or img_element.get('data-src')
                if src:
                    product_data['image_url'] = src
                else:
                    product_data['image_url'] = ''
            else:
                product_data['image_url'] = ''
            
            return product_data
            
        except Exception as e:
            print(f"Ürün detay çıkarma hatası: {e}")
            return None
    
    def scrape_deals_page(self, page_url: str = None) -> List[Dict]:
        """Günün fırsatları sayfasını scrape et"""
        if not page_url:
            page_url = self.deals_url
        
        print(f"Scraping: {page_url}")
        
        response = self.make_request(page_url)
        if not response:
            print("Sayfa yüklenemedi")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        products = []
        
        # Farklı deal formatları için selector'lar
        deal_selectors = [
            'div[data-testid="deal-card"]',
            '.DealCard-module__card',
            '.a-section.octopus-dlp-asin-stream',
            '.dealContainer',
            '.a-section.dealTile',
            '.sx-deal-card'
        ]
        
        product_elements = []
        for selector in deal_selectors:
            elements = soup.select(selector)
            if elements:
                product_elements.extend(elements)
                print(f"Selector '{selector}' ile {len(elements)} ürün bulundu")
        
        # Alternatif: tüm deal kartlarını bul
        if not product_elements:
            # Genel deal kartı arama
            all_divs = soup.find_all('div')
            for div in all_divs:
                # Deal kartı özelliklerini kontrol et
                classes = div.get('class', [])
                if any('deal' in str(cls).lower() for cls in classes):
                    product_elements.append(div)
        
        print(f"Toplam {len(product_elements)} ürün elementi bulundu")
        
        for i, element in enumerate(product_elements):
            try:
                product_data = self.scrape_product_details(element)
                if product_data:
                    products.append(product_data)
                    print(f"✓ Ürün {i+1}: {product_data['title'][:50]}... - %{product_data['discount_percent']} indirim")
                
                # Rate limiting
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"Ürün {i+1} işlenirken hata: {e}")
                continue
        
        print(f"Toplam {len(products)} geçerli ürün bulundu")
        return products
    
    def scrape_all_deals(self) -> List[Dict]:
        """Tüm fırsatları scrape et ve veritabanına kaydet"""
        print("Amazon.com.tr fırsat taraması başlıyor...")
        
        all_products = []
        
        # Ana günün fırsatları sayfası
        main_deals = self.scrape_deals_page()
        all_products.extend(main_deals)
        
        # Kategori bazlı sayfalar (varsa)
        category_urls = [
            f"{self.deals_url}?categoryFilter=electronics",
            f"{self.deals_url}?categoryFilter=computers",
            f"{self.deals_url}?categoryFilter=home",
            f"{self.deals_url}?categoryFilter=sports"
        ]
        
        for url in category_urls:
            time.sleep(random.uniform(5, 10))  # Sayfalar arası bekleme
            category_deals = self.scrape_deals_page(url)
            
            # Duplicate kontrolü
            existing_asins = {p['asin'] for p in all_products}
            new_deals = [p for p in category_deals if p['asin'] not in existing_asins]
            all_products.extend(new_deals)
        
        # Veritabanına kaydet
        saved_count = 0
        for product in all_products:
            try:
                if self.db.add_product(product):
                    # Fiyat geçmişine de ekle
                    self.db.add_price_history(product['asin'], product['current_price'])
                    saved_count += 1
            except Exception as e:
                print(f"Veritabanına kaydetme hatası: {e}")
        
        print(f"✓ {saved_count} ürün veritabanına kaydedildi")
        return all_products
    
    def get_deal_summary(self) -> Dict:
        """Mevcut fırsatların özetini döndür"""
        try:
            deals = self.db.get_big_deals()
            
            summary = {
                'total_deals': len(deals),
                'categories': {},
                'best_discount': 0,
                'average_discount': 0
            }
            
            if deals:
                # Kategori dağılımı
                for deal in deals:
                    category = deal['category']
                    if category not in summary['categories']:
                        summary['categories'][category] = 0
                    summary['categories'][category] += 1
                
                # En yüksek indirim
                summary['best_discount'] = max(deal['discount_percent'] for deal in deals)
                
                # Ortalama indirim
                summary['average_discount'] = sum(deal['discount_percent'] for deal in deals) / len(deals)
            
            return summary
            
        except Exception as e:
            print(f"Özet oluşturma hatası: {e}")
            return {'total_deals': 0, 'categories': {}, 'best_discount': 0, 'average_discount': 0}

# Test fonksiyonu
if __name__ == "__main__":
    scraper = AmazonScraper()
    deals = scraper.scrape_all_deals()
    summary = scraper.get_deal_summary()
    
    print("\n=== SCRAPING ÖZETI ===")
    print(f"Toplam fırsat: {summary['total_deals']}")
    print(f"En yüksek indirim: %{summary['best_discount']}")
    print(f"Ortalama indirim: %{summary['average_discount']:.1f}")
    print("Kategori dağılımı:")
    for category, count in summary['categories'].items():
        print(f"  {category}: {count} ürün")