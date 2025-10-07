from .base_scraper import BaseScraper
from typing import List, Dict

class TrendyolScraper(BaseScraper):
    """Trendyol indirimli ürün scraper'ı"""
    
    def __init__(self):
        super().__init__()
        self.site_name = "Trendyol"
        self.base_url = "https://www.trendyol.com"
        self.found_urls = set()
    
    def scrape_page(self, page: int = 1) -> List[Dict]:
        """Trendyol indirimli ürünler sayfasını scrape et"""
        print(f"\n🛍️ {self.site_name} sayfa {page} taranıyor...")
        
        # İndirimli ürünler URL'i
        url = f"https://www.trendyol.com/sr?pi={page}&sst=DISCOUNTED"
        
        soup = self.get_html(url, "trendyol")
        if not soup:
            return []
        
        # Debug HTML kaydet
        self.save_debug_html(str(soup), "trendyol", page)
        
        # Ürün kartlarını bul
        product_selectors = [
            'div.p-card-wrppr',
            '.product-item',
            '[data-id]'
        ]
        
        product_cards = self.extract_multiple_selectors(soup, product_selectors, "ürün kartları")
        if not product_cards:
            return []
        
        found_products = []
        
        for i, card in enumerate(product_cards[:20]):  # Max 20 ürün/sayfa
            try:
                print(f"\n--- {self.site_name} Ürün {i+1} ---")
                
                # 1. Başlık
                title_selectors = [
                    'span.prdct-desc-cntnr-name',
                    '.product-name',
                    '.p-card-chldrn-cntnr span'
                ]
                title_elements = self.extract_multiple_selectors(card, title_selectors, "başlık")
                if not title_elements:
                    self.log_product_skipped(self.site_name, "Başlık bulunamadı")
                    continue
                
                title = self.extract_text_safe(title_elements[0])
                print(f"📝 Başlık: {title[:60]}...")
                
                # 2. Link
                link_selectors = [
                    'a.p-card-chldrn-cntnr',
                    'a'
                ]
                link_elements = self.extract_multiple_selectors(card, link_selectors, "link")
                product_url = ""
                if link_elements:
                    href = self.extract_attr_safe(link_elements[0], 'href')
                    product_url = self.build_full_url(self.base_url, href)
                
                # Duplicate kontrol
                if product_url in self.found_urls:
                    self.log_product_skipped(self.site_name, "Duplicate ürün")
                    continue
                
                # 3. Mevcut fiyat
                current_price = None
                price_selectors = [
                    'div.prc-box-dscntd',
                    '.discounted-price',
                    '.current-price'
                ]
                
                for selector in price_selectors:
                    price_elements = card.select(selector)
                    if price_elements:
                        price_text = self.extract_text_safe(price_elements[0])
                        current_price = self.parse_price(price_text)
                        if current_price:
                            print(f"💰 Mevcut fiyat: {current_price}₺")
                            break
                
                # 4. Eski fiyat
                old_price = None
                old_price_selectors = [
                    'div.prc-box-orgnl',
                    '.original-price',
                    '.old-price'
                ]
                
                for selector in old_price_selectors:
                    old_price_elements = card.select(selector)
                    if old_price_elements:
                        old_price_text = self.extract_text_safe(old_price_elements[0])
                        old_price = self.parse_price(old_price_text)
                        if old_price:
                            print(f"🏷️ Eski fiyat: {old_price}₺")
                            break
                
                # 5. İndirim hesaplama
                if not current_price:
                    self.log_product_skipped(self.site_name, "Mevcut fiyat bulunamadı")
                    continue
                
                if not old_price:
                    self.log_product_skipped(self.site_name, "Eski fiyat bulunamadı")
                    continue
                
                discount_percent = self.calculate_discount(old_price, current_price)
                
                if not self.is_valid_deal(discount_percent, min_discount=40):
                    self.log_product_skipped(self.site_name, f"İndirim yetersiz: %{discount_percent}")
                    continue
                
                # 6. Resim
                img_selectors = [
                    'img.p-card-img',
                    'img'
                ]
                img_elements = self.extract_multiple_selectors(card, img_selectors, "resim")
                image_url = ""
                if img_elements:
                    image_url = self.extract_attr_safe(img_elements[0], 'src') or \
                               self.extract_attr_safe(img_elements[0], 'data-src')
                
                # 7. Ürün verisi oluştur
                product_data = {
                    'asin': self.generate_product_id(self.site_name, product_url),
                    'title': title,
                    'current_price': current_price,
                    'list_price': old_price,
                    'discount_percent': discount_percent,
                    'product_url': product_url,
                    'image_url': image_url,
                    'category': 'Elektronik',
                    'site_name': self.site_name
                }
                
                found_products.append(product_data)
                self.found_urls.add(product_url)
                self.log_product_found(self.site_name, title, discount_percent, current_price)
                
                # Rate limiting
                self.wait_between_requests(2, 3)
                
            except Exception as e:
                self.log_error(self.site_name, f"Ürün {i+1} işleme hatası: {e}")
                continue
        
        print(f"\n🎯 {self.site_name} sayfa {page}: {len(found_products)} ürün bulundu")
        return found_products
    
    def scrape(self, max_pages: int = 2) -> List[Dict]:
        """Trendyol'dan tüm indirimleri scrape et"""
        print(f"\n🚀 {self.site_name} scraping başlıyor...")
        
        all_products = []
        self.found_urls.clear()
        
        for page in range(1, max_pages + 1):
            try:
                products = self.scrape_page(page)
                all_products.extend(products)
                
                # Sayfalar arası bekleme
                if page < max_pages:
                    self.wait_between_requests(3, 5)
                    
            except Exception as e:
                self.log_error(self.site_name, f"Sayfa {page} hatası: {e}")
                continue
        
        print(f"\n✅ {self.site_name} tamamlandı: {len(all_products)} ürün")
        return all_products