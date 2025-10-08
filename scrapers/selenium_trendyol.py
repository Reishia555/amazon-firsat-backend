from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import os

def scrape_trendyol_with_selenium():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except Exception as e:
        print(f"Chrome driver failed: {e}")
        print("Chrome may not be installed. Selenium scraper requires Chrome browser.")
        return []
    
    try:
        url = "https://www.trendyol.com/sr?sst=DISCOUNTED"
        driver.get(url)
        time.sleep(5)
        
        products = driver.find_elements(By.CSS_SELECTOR, 'div.p-card-wrppr')
        
        results = []
        for product in products[:20]:
            try:
                title = product.find_element(By.CSS_SELECTOR, 'span.prdct-desc-cntnr-name').text
                current_price = product.find_element(By.CSS_SELECTOR, 'div.prc-box-dscntd').text
                old_price = product.find_element(By.CSS_SELECTOR, 'div.prc-box-orgnl').text
                discount = product.find_element(By.CSS_SELECTOR, 'span.prc-box-dscnt-prcnt').text
                link = product.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                image = product.find_element(By.CSS_SELECTOR, 'img').get_attribute('src')
                
                current = float(current_price.replace('.', '').replace(',', '.').replace('TL', '').strip())
                old = float(old_price.replace('.', '').replace(',', '.').replace('TL', '').strip())
                disc_pct = int(discount.replace('%', '').strip())
                
                if disc_pct >= 20:
                    results.append({
                        'title': title,
                        'current_price': current,
                        'list_price': old,
                        'discount_percent': disc_pct,
                        'product_url': f"https://www.trendyol.com{link}",
                        'image_url': image,
                        'site_name': 'Trendyol'
                    })
            except:
                continue
        
        return results
        
    finally:
        driver.quit()

if __name__ == "__main__":
    products = scrape_trendyol_with_selenium()
    print(f"Found {len(products)} products with 20%+ discount:")
    for product in products:
        print(f"- {product['title']} - {product['current_price']}TL ({product['discount_percent']}% off)")