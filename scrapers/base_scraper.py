import requests
from bs4 import BeautifulSoup
import time
import re
import random
from typing import Dict, Optional, List
from urllib.parse import urljoin

class BaseScraper:
    """Tüm scraper'lar için ortak fonksiyonlar"""
    
    def __init__(self):
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
        ]
    
    def get_headers(self, site_name: str = "default") -> Dict[str, str]:
        """Site'e özel headers"""
        base_headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        }
        
        # Site özel ayarlar
        if site_name == "trendyol":
            base_headers['Referer'] = 'https://www.trendyol.com/'
        elif site_name == "hepsiburada":
            base_headers['Referer'] = 'https://www.hepsiburada.com/'
        
        return base_headers
    
    def get_html(self, url: str, site_name: str = "default", timeout: int = 30) -> Optional[BeautifulSoup]:
        """HTML içeriği çek ve parse et"""
        try:
            headers = self.get_headers(site_name)
            response = self.session.get(url, headers=headers, timeout=timeout)
            
            print(f"🌐 {site_name} - Status: {response.status_code}")
            
            if response.status_code == 200:
                return BeautifulSoup(response.content, 'html.parser')
            else:
                print(f"❌ HTTP {response.status_code}: {url}")
                return None
                
        except Exception as e:
            print(f"❌ Request hatası ({site_name}): {e}")
            return None
    
    def parse_price(self, price_str: str) -> Optional[float]:
        """Fiyat string'ini sayıya çevir: '1.299,99 TL' → 1299.99"""
        if not price_str:
            return None
        
        # Temizlik
        price_clean = price_str.replace('TL', '').replace('₺', '').strip()
        
        # Sayıları bul
        numbers = re.findall(r'[\d.,]+', price_clean)
        if not numbers:
            return None
        
        try:
            # En uzun sayı string'ini al
            price_text = max(numbers, key=len)
            
            # Türk formatını düzelt
            if ',' in price_text and '.' in price_text:
                # 1.299,99 formatı
                price_text = price_text.replace('.', '').replace(',', '.')
            elif ',' in price_text:
                # Virgül kontrol: ondalık mı binlik mi?
                parts = price_text.split(',')
                if len(parts) == 2 and len(parts[1]) == 2:
                    # 1299,99 - ondalık
                    price_text = price_text.replace(',', '.')
                else:
                    # 1,299 - binlik
                    price_text = price_text.replace(',', '')
            
            price = float(price_text)
            return price if 1 <= price <= 500000 else None
            
        except ValueError:
            return None
    
    def calculate_discount(self, old_price: float, new_price: float) -> int:
        """İndirim yüzdesini hesapla"""
        if not old_price or not new_price or old_price <= new_price:
            return 0
        
        discount = ((old_price - new_price) / old_price) * 100
        return int(discount)
    
    def is_valid_deal(self, discount_percent: int, min_discount: int = 40) -> bool:
        """Geçerli fırsat mı? (%40+ indirim)"""
        return discount_percent >= min_discount
    
    def extract_text_safe(self, element, default: str = "") -> str:
        """Element'ten güvenli text çıkarma"""
        if element:
            return element.get_text(strip=True)
        return default
    
    def extract_attr_safe(self, element, attr: str, default: str = "") -> str:
        """Element'ten güvenli attribute çıkarma"""
        if element:
            return element.get(attr, default)
        return default
    
    def build_full_url(self, base_url: str, href: str) -> str:
        """Tam URL oluştur"""
        if not href:
            return ""
        
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            return urljoin(base_url, href)
        else:
            return f"{base_url}/{href}"
    
    def generate_product_id(self, site_name: str, product_url: str) -> str:
        """Ürün ID oluştur"""
        url_hash = hash(product_url) % 100000
        prefix = site_name[:2].upper()
        return f"{prefix}{url_hash:05d}"
    
    def wait_between_requests(self, min_seconds: int = 2, max_seconds: int = 4):
        """İstekler arası bekleme (rate limiting)"""
        wait_time = random.uniform(min_seconds, max_seconds)
        time.sleep(wait_time)
    
    def log_product_found(self, site_name: str, title: str, discount: int, current_price: float):
        """Ürün bulundu logu"""
        print(f"✅ {site_name}: {title[:50]}... - %{discount} indirim ({current_price}₺)")
    
    def log_product_skipped(self, site_name: str, reason: str):
        """Ürün atlandı logu"""
        print(f"⏭️  {site_name}: {reason}")
    
    def log_error(self, site_name: str, error: str):
        """Hata logu"""
        print(f"❌ {site_name}: {error}")
    
    def save_debug_html(self, html_content: str, site_name: str, page: int = 1):
        """Debug için HTML kaydet"""
        try:
            filename = f"/tmp/{site_name}_page_{page}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"💾 Debug HTML kaydedildi: {filename}")
        except Exception as e:
            print(f"⚠️  HTML kaydetme hatası: {e}")
    
    def extract_multiple_selectors(self, soup, selectors: List[str], element_name: str = "element"):
        """Birden fazla selector dene"""
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                print(f"🎯 {element_name} bulundu: {selector} ({len(elements)} adet)")
                return elements
        
        print(f"❌ {element_name} bulunamadı (denenen: {len(selectors)} selector)")
        return []