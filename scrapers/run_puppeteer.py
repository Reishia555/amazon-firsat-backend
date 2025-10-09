import subprocess
import json
import os
import sys
from datetime import datetime

class PuppeteerScraper:
    def __init__(self):
        self.script_path = os.path.join(os.path.dirname(__file__), 'puppeteer_scraper.js')
        
    def scrape_trendyol(self):
        """Run Puppeteer scraper and return parsed results"""
        try:
            result = subprocess.run(
                ['node', self.script_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                print(f"Puppeteer script error: {result.stderr}", file=sys.stderr)
                return {
                    'success': False,
                    'error': f'Script execution failed: {result.stderr}',
                    'products': [],
                    'count': 0
                }
            
            response = json.loads(result.stdout)
            
            if response.get('success', False):
                products = response.get('products', [])
                
                for product in products:
                    product['scraped_at'] = datetime.now().isoformat()
                    product['source'] = 'puppeteer'
                
                return {
                    'success': True,
                    'products': products,
                    'count': len(products),
                    'scraped_at': datetime.now().isoformat()
                }
            else:
                return response
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Scraping timeout after 5 minutes',
                'products': [],
                'count': 0
            }
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'Failed to parse JSON response: {str(e)}',
                'products': [],
                'count': 0
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'products': [],
                'count': 0
            }
    
    def save_to_database(self, products):
        """Save products to database using existing database module"""
        try:
            from database import Database
            
            db = Database()
            saved_count = 0
            
            for product in products:
                try:
                    success = db.save_product(
                        title=product['title'],
                        current_price=product['current_price'],
                        original_price=product['original_price'],
                        discount_percent=product['discount_percent'],
                        url=product['url'],
                        image_url=product.get('image_url', ''),
                        site=product['site']
                    )
                    if success:
                        saved_count += 1
                except Exception as e:
                    print(f"Error saving product {product['title']}: {str(e)}", file=sys.stderr)
                    continue
            
            return {
                'success': True,
                'saved_count': saved_count,
                'total_count': len(products)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Database error: {str(e)}',
                'saved_count': 0,
                'total_count': len(products)
            }

def main():
    """Command line interface for testing"""
    scraper = PuppeteerScraper()
    result = scraper.scrape_trendyol()
    
    if result['success']:
        print(f"Successfully scraped {result['count']} products")
        
        if result['products']:
            save_result = scraper.save_to_database(result['products'])
            if save_result['success']:
                print(f"Saved {save_result['saved_count']} products to database")
            else:
                print(f"Database save failed: {save_result['error']}")
    else:
        print(f"Scraping failed: {result['error']}")
    
    return result

if __name__ == "__main__":
    main()