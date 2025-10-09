#!/usr/bin/env python3
"""Quick debug test for scrapers"""

import requests
from bs4 import BeautifulSoup

def test_trendyol():
    """Test Trendyol response"""
    print("🛍️ Testing Trendyol...")
    
    url = "https://www.trendyol.com/sr?sst=DISCOUNTED"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
        'Referer': 'https://www.trendyol.com/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Content length: {len(response.text)}")
        
        # Save first 2000 chars
        with open("/tmp/trendyol_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for product selectors
        selectors = [
            'div.p-card-wrppr',
            '.product-item',
            '[data-id]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            print(f"  {selector}: {len(elements)} found")
        
        # Check page title
        title = soup.find('title')
        if title:
            print(f"  Page title: {title.get_text()[:100]}...")
        
        # Check for bot protection
        if 'captcha' in response.text.lower() or 'robot' in response.text.lower():
            print("  ⚠️ Possible bot protection detected")
        
        print(f"  First 500 chars: {response.text[:500]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def test_hepsiburada():
    """Test Hepsiburada response"""
    print("\n🛒 Testing Hepsiburada...")
    
    url = "https://www.hepsiburada.com/kampanyalar"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
        'Referer': 'https://www.hepsiburada.com/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Content length: {len(response.text)}")
        
        # Save first 2000 chars
        with open("/tmp/hepsiburada_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for product selectors
        selectors = [
            'li.productListContent-item',
            '.product-item',
            '.product-card',
            '[data-test-id="product-card"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            print(f"  {selector}: {len(elements)} found")
        
        # Check page title
        title = soup.find('title')
        if title:
            print(f"  Page title: {title.get_text()[:100]}...")
        
        # Check for bot protection
        if 'captcha' in response.text.lower() or 'robot' in response.text.lower():
            print("  ⚠️ Possible bot protection detected")
        
        print(f"  First 500 chars: {response.text[:500]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 SCRAPER DEBUG TEST")
    print("=" * 50)
    
    test_trendyol()
    test_hepsiburada()
    
    print("\n✅ Debug completed. Check /tmp/ for HTML files.")