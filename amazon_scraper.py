import requests
from bs4 import BeautifulSoup
import time
import re
from typing import List, Dict, Optional
import random
from urllib.parse import urljoin, quote_plus
from database import Database

class AmazonScraper:
    def __init__(self):
        self.base_url = "https://www.amazon.com.tr"
        self.session = requests.Session()
        
        # User-Agent rotasyonu için liste (bot tespitini engelle)
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
        # Ana kategoriler (gizli indirimleri bulacağız)
        self.categories = {
            'Bilgisayar & Tablet': {
                'url': '/s?k=laptop&rh=n:12601898031&pct-off=40-',
                'keywords': ['laptop', 'tablet', 'bilgisayar', 'pc']
            },
            'Elektronik': {
                'url': '/s?k=elektronik&rh=n:13709898031&pct-off=40-',
                'keywords': ['telefon', 'tv', 'kulaklık', 'speaker']
            },
            'Aksesuar': {
                'url': '/s?k=aksesuar&rh=n:13644327031&pct-off=40-',
                'keywords': ['mouse', 'klavye', 'şarj', 'kablo']
            }
        }
        
        # Ek arama terimleri (popüler ürünler)
        self.search_terms = [
            'gaming mouse',
            'mekanik klavye',
            'wireless kulaklık',
            'bluetooth speaker',
            'laptop stand',
            'phone case'
        ]
        
        # Fiyat aralığı
        self.min_price = 10.0
        self.max_price = 10000.0
        
        self.db = Database()
        self.found_asins = set()  # Duplicate kontrolü
    
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
            'Cache-Control': 'max-age=0',
            'DNT': '1'
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
                    print(f"503 Service Unavailable - {attempt + 1}. deneme")
                    time.sleep(random.uniform(10, 20))
                elif response.status_code == 429:
                    print(f"Rate limit - {attempt + 1}. deneme")
                    time.sleep(random.uniform(15, 30))
                else:
                    print(f"HTTP {response.status_code} hatası: {url}")
                    
            except Exception as e:
                print(f"Request hatası (deneme {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(random.uniform(5, 10))
        
        return None
    
    def extract_price(self, price_text: str) -> Optional[float]:
        """Fiyat metninden sayısal değer çıkar"""
        if not price_text:
            return None
        
        # Türkçe fiyat formatını temizle
        price_text = str(price_text).replace('₺', '').replace('TL', '').replace('\n', ' ').strip()
        
        # Sadece sayılar, virgül ve nokta bırak
        price_text = re.sub(r'[^\d,.]', '', price_text)
        
        if not price_text:
            return None
        
        try:
            # Virgül ile nokta karışıklığını düzelt
            if ',' in price_text and '.' in price_text:
                # 1.234,56 formatı
                price_text = price_text.replace('.', '').replace(',', '.')
            elif ',' in price_text:
                # 1234,56 formatı - eğer virgül sonrası 2 haneli ise ondalık
                parts = price_text.split(',')
                if len(parts) == 2 and len(parts[1]) == 2:
                    price_text = price_text.replace(',', '.')
                else:
                    price_text = price_text.replace(',', '')
            
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
            r'/([A-Z0-9]{10})(?:/|$)',
            r'product/([A-Z0-9]{10})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, product_url)
            if match:
                return match.group(1)
        
        return None
    
    def has_discount_badge(self, product_element) -> bool:
        """Ürünün indirim badge'i var mı kontrol et"""
        # İndirim badge'lerini ara
        discount_indicators = [
            '.a-badge-label',
            '.a-color-price',
            '.a-offscreen',
            'span[data-a-color="price"]',
            '.a-text-strike'
        ]
        
        for indicator in discount_indicators:
            elements = product_element.select(indicator)
            for element in elements:
                text = element.get_text().lower()
                if any(word in text for word in ['%', 'indirim', 'off', 'save', 'was']):
                    return True
        
        return False
    
    def extract_product_info(self, product_element) -> Optional[Dict]:
        """Tek bir ürün elementinden bilgileri çıkar"""
        try:
            product_data = {}
            
            # Ürün linkini bul
            link_element = product_element.select_one('h2 a, h3 a, .a-link-normal, a[data-component-type="s-product-image"]')
            if not link_element:
                return None
            
            href = link_element.get('href', '')
            if href.startswith('/'):
                product_url = urljoin(self.base_url, href)
            else:
                product_url = href
            
            product_data['product_url'] = product_url
            
            # ASIN çıkar
            asin = self.extract_asin(product_url)
            if not asin or asin in self.found_asins:
                return None
            
            product_data['asin'] = asin
            self.found_asins.add(asin)
            
            # Başlık
            title_element = product_element.select_one('h2 span, h3 span, .a-size-base-plus, .a-size-base')
            if title_element:
                title = title_element.get_text(strip=True)
                if len(title) < 10:  # Çok kısa başlıkları eleme
                    return None
                product_data['title'] = title
            else:
                return None
            
            # Fiyat bilgileri
            current_price = None
            list_price = None
            
            # Mevcut fiyat
            current_price_selectors = [
                '.a-price.a-text-price.a-size-medium.a-color-base .a-offscreen',
                '.a-price-whole',
                '.a-price .a-offscreen'
            ]
            
            for selector in current_price_selectors:
                price_element = product_element.select_one(selector)
                if price_element:
                    current_price = self.extract_price(price_element.get_text())
                    if current_price:
                        break
            
            # Liste fiyatı (eski fiyat)
            list_price_selectors = [
                '.a-price.a-text-price .a-offscreen',
                '.a-text-strike .a-offscreen', 
                '.a-price-was .a-offscreen',
                '.a-text-strike'
            ]
            
            for selector in list_price_selectors:
                price_element = product_element.select_one(selector)
                if price_element:
                    list_price = self.extract_price(price_element.get_text())
                    if list_price and list_price > (current_price or 0):
                        break
            
            # Fiyat kontrolü
            if not current_price or not list_price or list_price <= current_price:
                return None
            
            product_data['current_price'] = current_price
            product_data['list_price'] = list_price
            
            # İndirim yüzdesi hesapla
            discount_percent = int(((list_price - current_price) / list_price) * 100)
            if discount_percent < 40:  # Minimum %40 indirim
                return None
            
            product_data['discount_percent'] = discount_percent
            
            # İndirim badge'i kontrolü
            if not self.has_discount_badge(product_element):
                return None
            
            # Kategori belirleme
            category = self.determine_category(title)
            product_data['category'] = category
            
            # Resim URL
            img_element = product_element.select_one('img')
            if img_element:
                src = img_element.get('src') or img_element.get('data-src')
                product_data['image_url'] = src if src else ''
            else:
                product_data['image_url'] = ''
            
            return product_data
            
        except Exception as e:
            print(f"Ürün bilgisi çıkarma hatası: {e}")
            return None
    
    def determine_category(self, title: str) -> str:
        """Ürün başlığından kategori belirle"""
        title_lower = title.lower()
        
        # Kategori anahtar kelimeleri
        if any(word in title_lower for word in ['laptop', 'bilgisayar', 'pc', 'tablet', 'macbook']):
            return 'Bilgisayar & Tablet'
        elif any(word in title_lower for word in ['telefon', 'phone', 'tv', 'televizyon', 'kamera']):
            return 'Elektronik'
        elif any(word in title_lower for word in ['mouse', 'klavye', 'kulaklık', 'speaker', 'şarj', 'kablo']):
            return 'Aksesuar'
        else:
            return 'Elektronik'  # Varsayılan
    
    def scrape_category_page(self, category_name: str, category_url: str, page: int = 1) -> List[Dict]:
        """Kategori sayfasını scrape et"""
        products = []
        
        # Sayfa parametresi ekle
        if page > 1:
            separator = '&' if '?' in category_url else '?'
            url = f"{self.base_url}{category_url}{separator}page={page}"
        else:
            url = f"{self.base_url}{category_url}"
        
        print(f"Taranıyor: {category_name} - Sayfa {page}")
        print(f"URL: {url}")
        
        response = self.make_request(url)
        if not response:
            print(f"Sayfa yüklenemedi: {url}")
            return products
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ürün elementlerini bul
        product_selectors = [
            '[data-component-type="s-search-result"]',
            '.s-result-item[data-asin]',
            '.sg-col-inner .s-widget-container'
        ]
        
        product_elements = []
        for selector in product_selectors:
            elements = soup.select(selector)
            if elements:
                product_elements = elements
                print(f"Selector '{selector}' ile {len(elements)} ürün bulundu")
                break
        
        if not product_elements:
            print("Hiç ürün elementi bulunamadı")
            return products
        
        # Her ürünü işle
        for i, element in enumerate(product_elements[:20]):  # Sayfa başına max 20 ürün
            try:
                product_data = self.extract_product_info(element)
                if product_data:
                    products.append(product_data)
                    print(f"✓ Ürün bulundu: {product_data['title'][:50]}... - %{product_data['discount_percent']} indirim")
                
                # Rate limiting
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"Ürün {i+1} işlenirken hata: {e}")
                continue
        
        return products
    
    def scrape_search_term(self, search_term: str) -> List[Dict]:
        """Belirli bir arama terimini scrape et"""
        products = []
        
        # URL'yi oluştur (%40+ indirim filtresi ile)
        encoded_term = quote_plus(search_term)
        url = f"{self.base_url}/s?k={encoded_term}&pct-off=40-"
        
        print(f"Arama terimi taranıyor: {search_term}")
        
        response = self.make_request(url)
        if not response:
            return products
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ürün elementlerini bul
        product_elements = soup.select('[data-component-type="s-search-result"]')
        
        if not product_elements:
            return products
        
        # İlk 10 ürünü işle
        for element in product_elements[:10]:
            try:
                product_data = self.extract_product_info(element)
                if product_data:
                    products.append(product_data)
                
                time.sleep(random.uniform(2, 3))
                
            except Exception as e:
                print(f"Arama ürünü işleme hatası: {e}")
                continue
        
        return products
    
    def scrape_all_deals(self) -> List[Dict]:
        """Tüm gizli indirimleri scrape et"""
        print("🔍 Amazon.com.tr gizli indirim taraması başlıyor...")
        
        all_products = []
        self.found_asins.clear()
        
        # 1. Kategori taraması (3 sayfa)
        for category_name, category_info in self.categories.items():
            category_url = category_info['url']
            
            for page in range(1, 4):  # İlk 3 sayfa
                try:
                    products = self.scrape_category_page(category_name, category_url, page)
                    all_products.extend(products)
                    
                    # Sayfalar arası bekleme
                    time.sleep(random.uniform(5, 8))
                    
                except Exception as e:
                    print(f"Kategori tarama hatası ({category_name} - Sayfa {page}): {e}")
                    continue
        
        # 2. Popüler arama terimleri
        for search_term in self.search_terms:
            try:
                products = self.scrape_search_term(search_term)
                all_products.extend(products)
                
                time.sleep(random.uniform(5, 8))
                
            except Exception as e:
                print(f"Arama terimi hatası ({search_term}): {e}")
                continue
        
        # 3. Veritabanına kaydet
        saved_count = 0
        for product in all_products:
            try:
                if self.db.add_product(product):
                    # Fiyat geçmişine de ekle
                    self.db.add_price_history(product['asin'], product['current_price'])
                    saved_count += 1
            except Exception as e:
                print(f"Veritabanı kaydetme hatası: {e}")
        
        print(f"✅ Tarama tamamlandı: {len(all_products)} ürün bulundu, {saved_count} ürün kaydedildi")
        return all_products
    
    def get_deal_summary(self) -> Dict:
        """Bulunan fırsatların özetini döndür"""
        try:
            deals = self.db.get_big_deals(min_discount=40)
            
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
    
    print("🚀 Test scraping başlıyor...")
    deals = scraper.scrape_all_deals()
    summary = scraper.get_deal_summary()
    
    print("\n=== SCRAPING ÖZETI ===")
    print(f"Toplam fırsat: {summary['total_deals']}")
    print(f"En yüksek indirim: %{summary['best_discount']}")
    print(f"Ortalama indirim: %{summary['average_discount']:.1f}")
    print("Kategori dağılımı:")
    for category, count in summary['categories'].items():
        print(f"  {category}: {count} ürün")