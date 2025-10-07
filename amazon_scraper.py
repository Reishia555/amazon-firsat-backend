import requests
from bs4 import BeautifulSoup
import time
import re
from typing import List, Dict, Optional
import random
from urllib.parse import urljoin
from database import Database

class AmazonScraper:
    def __init__(self):
        self.base_url = "https://www.amazon.com.tr"
        self.session = requests.Session()
        self.db = Database()
    
    def get_headers(self) -> Dict[str, str]:
        """Basit User-Agent header"""
        return {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
    
    def extract_price(self, price_text: str) -> Optional[float]:
        """Fiyat metninden sayısal değer çıkar"""
        if not price_text:
            return None
        
        # Sadece sayıları al
        numbers = re.findall(r'[\d,]+', price_text.replace('₺', '').replace('TL', ''))
        if not numbers:
            return None
        
        try:
            # Virgülü nokta yap
            price_str = numbers[0].replace(',', '.')
            price = float(price_str)
            return price if 1 <= price <= 50000 else None
        except:
            return None
    
    def simple_mouse_test(self) -> List[Dict]:
        """ÇOK BASİT TEST: Sadece mouse ara"""
        print("🐭 Basit mouse testi başlıyor...")
        
        # Çok basit URL
        url = "https://www.amazon.com.tr/s?k=mouse"
        print(f"URL: {url}")
        
        try:
            response = self.session.get(url, headers=self.get_headers(), timeout=30)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ HTTP Error: {response.status_code}")
                return []
            
            # HTML'i kaydet (debug için)
            with open('/tmp/amazon_response.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("💾 HTML response kaydedildi: /tmp/amazon_response.html")
            
        except Exception as e:
            print(f"❌ Request hatası: {e}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ürün kartlarını bul
        product_cards = soup.select('div[data-component-type="s-search-result"]')
        print(f"🔍 {len(product_cards)} ürün kartı bulundu")
        
        if len(product_cards) == 0:
            print("❌ Hiç ürün kartı bulunamadı")
            # Alternative selectors
            alt_cards = soup.select('.s-result-item')
            print(f"🔍 Alternative: {len(alt_cards)} .s-result-item bulundu")
            
            # Tüm div'leri say
            all_divs = soup.select('div')
            print(f"🔍 Toplam {len(all_divs)} div elementi var")
            
            return []
        
        found_products = []
        
        for i, card in enumerate(product_cards[:5]):  # İlk 5 ürün
            print(f"\n--- ÜRÜN {i+1} ANALİZİ ---")
            
            try:
                # 1. Başlık bul
                title_element = card.select_one('h2 a span, h2 span')
                if not title_element:
                    print("❌ Başlık bulunamadı")
                    continue
                
                title = title_element.get_text(strip=True)
                print(f"📝 Başlık: {title[:80]}...")
                
                # 2. Link bul
                link_element = card.select_one('h2 a')
                product_url = ""
                if link_element:
                    href = link_element.get('href', '')
                    if href.startswith('/'):
                        product_url = urljoin(self.base_url, href)
                    print(f"🔗 Link: {href[:50]}...")
                
                # 3. Tüm fiyat elementlerini bul
                print("💰 Fiyat arama...")
                
                # Mevcut fiyat araması
                current_price = None
                price_selectors = [
                    'span.a-price-whole',
                    '.a-price .a-offscreen',
                    'span.a-color-price'
                ]
                
                for selector in price_selectors:
                    price_elements = card.select(selector)
                    print(f"   {selector}: {len(price_elements)} element")
                    
                    for pe in price_elements:
                        price_text = pe.get_text(strip=True)
                        price = self.extract_price(price_text)
                        if price:
                            current_price = price
                            print(f"   ✅ Mevcut fiyat: {price}₺ (selector: {selector})")
                            break
                    
                    if current_price:
                        break
                
                # Liste fiyatı araması (çizili/strike)
                list_price = None
                strike_selectors = [
                    'span.a-price[data-a-strike="true"] .a-offscreen',
                    '.a-text-strike .a-offscreen',
                    'span.a-text-strike',
                    '.a-price-was'
                ]
                
                for selector in strike_selectors:
                    strike_elements = card.select(selector)
                    print(f"   {selector}: {len(strike_elements)} element")
                    
                    for se in strike_elements:
                        strike_text = se.get_text(strip=True)
                        price = self.extract_price(strike_text)
                        if price:
                            list_price = price
                            print(f"   ✅ Liste fiyatı: {price}₺ (selector: {selector})")
                            break
                    
                    if list_price:
                        break
                
                # 4. Resim URL
                img_element = card.select_one('img.s-image, img')
                image_url = ""
                if img_element:
                    image_url = img_element.get('src', '')
                
                # 5. İndirim hesaplama
                if current_price and list_price and list_price > current_price:
                    discount_percent = int(((list_price - current_price) / list_price) * 100)
                    
                    print(f"🎉 İNDİRİM BULUNDU!")
                    print(f"   Mevcut: {current_price}₺")
                    print(f"   Liste: {list_price}₺")
                    print(f"   İndirim: %{discount_percent}")
                    
                    if discount_percent >= 40:  # %40+ indirim
                        # ASIN çıkar (basit)
                        asin = f"MOUSE{i+1:03d}"
                        if '/dp/' in product_url:
                            asin_match = re.search(r'/dp/([A-Z0-9]{10})', product_url)
                            if asin_match:
                                asin = asin_match.group(1)
                        
                        product_data = {
                            'asin': asin,
                            'title': title,
                            'current_price': current_price,
                            'list_price': list_price,
                            'discount_percent': discount_percent,
                            'product_url': product_url,
                            'image_url': image_url,
                            'category': 'Elektronik'
                        }
                        
                        found_products.append(product_data)
                        print(f"✅ Ürün kaydedildi (%{discount_percent} indirim)")
                    else:
                        print(f"❌ İndirim yetersiz: %{discount_percent} (min: %40)")
                
                elif current_price and not list_price:
                    print(f"ℹ️  Sadece mevcut fiyat: {current_price}₺ (liste fiyatı yok)")
                elif not current_price:
                    print(f"❌ Hiçbir fiyat bulunamadı")
                else:
                    print(f"❌ İndirim yok: mevcut={current_price}₺, liste={list_price}₺")
                
            except Exception as e:
                print(f"❌ Ürün {i+1} hatası: {e}")
                continue
        
        print(f"\n🎯 Test sonucu: {len(found_products)} indirimli mouse bulundu")
        return found_products
    
    def scrape_all_deals(self) -> List[Dict]:
        """Ana scraping fonksiyonu - şimdilik sadece mouse testi"""
        products = self.simple_mouse_test()
        
        # Veritabanına kaydet
        saved_count = 0
        for product in products:
            try:
                if self.db.add_product(product):
                    self.db.add_price_history(product['asin'], product['current_price'])
                    saved_count += 1
            except Exception as e:
                print(f"DB kaydetme hatası: {e}")
        
        print(f"💾 {saved_count} ürün veritabanına kaydedildi")
        return products
    
    def get_deal_summary(self) -> Dict:
        """Özet bilgiler"""
        try:
            deals = self.db.get_big_deals(min_discount=40)
            
            return {
                'total_deals': len(deals),
                'categories': {'Elektronik': len(deals)} if deals else {},
                'best_discount': max([d['discount_percent'] for d in deals], default=0),
                'average_discount': sum([d['discount_percent'] for d in deals]) / len(deals) if deals else 0
            }
        except Exception as e:
            print(f"Özet hatası: {e}")
            return {'total_deals': 0, 'categories': {}, 'best_discount': 0, 'average_discount': 0}

# Test
if __name__ == "__main__":
    scraper = AmazonScraper()
    
    print("🚀 BASİT MOUSE TESTİ")
    print("=" * 50)
    
    products = scraper.simple_mouse_test()
    
    print("\n📊 SONUÇLAR:")
    if products:
        for i, p in enumerate(products, 1):
            print(f"{i}. {p['title'][:60]}...")
            print(f"   %{p['discount_percent']} indirim: {p['current_price']}₺ → {p['list_price']}₺")
    else:
        print("❌ Hiçbir indirimli mouse bulunamadı")
    
    print(f"\n✅ Test tamamlandı: {len(products)} ürün")