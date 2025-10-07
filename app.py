import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
from database import Database
from amazon_scraper import AmazonScraper
from scrapers.main_scraper import MainScraper
from price_tracker import PriceTracker
from notifier import NotificationManager
from scheduler import init_scheduler, get_scheduler
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Tüm origin'lere izin ver

# Global instances
db = Database()
scraper = AmazonScraper()
main_scraper = MainScraper()
price_tracker = PriceTracker()
notification_manager = NotificationManager()

# Scheduler'ı başlat
scheduler = init_scheduler()

@app.route('/health', methods=['GET'])
def health_check():
    """Sağlık kontrolü endpoint'i"""
    try:
        # Veritabanı bağlantısını test et
        cursor = db.conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "version": "1.0.0"
    })

@app.route('/products', methods=['GET'])
def get_products():
    """Tüm ürünleri getir"""
    try:
        # Query parametreleri
        limit = request.args.get('limit', 100, type=int)
        category = request.args.get('category')
        
        deals = db.get_big_deals(min_discount=70, category=category)
        
        # Format edilmiş sonuçlar
        formatted_products = []
        for deal in deals[:limit]:
            # Datetime'ları string'e çevir
            deal['first_seen'] = deal['first_seen'].isoformat() if deal['first_seen'] else None
            deal['last_updated'] = deal['last_updated'].isoformat() if deal['last_updated'] else None
            
            # Decimal'ları float'a çevir
            deal['current_price'] = float(deal['current_price'])
            deal['list_price'] = float(deal['list_price'])
            
            formatted_products.append(deal)
        
        return jsonify({
            "success": True,
            "count": len(formatted_products),
            "products": formatted_products
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/products/new', methods=['GET'])
def get_new_products():
    """Son 1 saatteki yeni ürünleri getir"""
    try:
        hours = request.args.get('hours', 1, type=int)
        
        new_deals = db.get_new_deals(hours=hours)
        
        # Format edilmiş sonuçlar
        formatted_products = []
        for deal in new_deals:
            deal['first_seen'] = deal['first_seen'].isoformat() if deal['first_seen'] else None
            deal['last_updated'] = deal['last_updated'].isoformat() if deal['last_updated'] else None
            deal['current_price'] = float(deal['current_price'])
            deal['list_price'] = float(deal['list_price'])
            formatted_products.append(deal)
        
        return jsonify({
            "success": True,
            "count": len(formatted_products),
            "new_products": formatted_products,
            "time_range_hours": hours
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/scrape-now', methods=['POST'])
def scrape_now():
    """Multi-site scraping tetikle"""
    try:
        # Multi-site scraping başlat
        all_products, results = main_scraper.scrape_all_sites()
        
        # Site istatistikleri
        stats = main_scraper.get_site_statistics()
        
        return jsonify({
            "success": True,
            "message": "Multi-site scraping tamamlandı",
            "results": {
                "total_products": results['total_products'],
                "total_saved": results['total_saved'],
                "scrape_time": results['scrape_time'],
                "by_site": {
                    "trendyol": {
                        "count": results['trendyol']['count'],
                        "success": results['trendyol']['success']
                    },
                    "hepsiburada": {
                        "count": results['hepsiburada']['count'], 
                        "success": results['hepsiburada']['success']
                    }
                },
                "errors": results['errors']
            },
            "statistics": stats
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/register-device', methods=['POST'])
def register_device():
    """Device token kaydet"""
    try:
        data = request.get_json()
        
        if not data or 'device_token' not in data:
            return jsonify({
                "success": False,
                "error": "device_token gerekli"
            }), 400
        
        device_token = data['device_token']
        preferences = data.get('preferences', {})
        
        # Varsayılan tercihler
        default_preferences = {
            'min_discount': 70,
            'categories': ['Bilgisayarlar', 'Elektronik', 'Ev & Mutfak', 'Spor', 'Oyun'],
            'min_price': 10.0,
            'max_price': 10000.0
        }
        
        # Tercihleri birleştir
        final_preferences = {**default_preferences, **preferences}
        
        # Veritabanına kaydet
        success = db.save_device_token(device_token, final_preferences)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Cihaz başarıyla kaydedildi",
                "preferences": final_preferences
            })
        else:
            return jsonify({
                "success": False,
                "error": "Cihaz kaydedilemedi"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/deals', methods=['GET'])
def get_deals():
    """Fırsatları getir"""
    try:
        # Query parametreleri
        min_discount = request.args.get('min_discount', 70, type=int)
        category = request.args.get('category')
        limit = request.args.get('limit', 50, type=int)
        
        # Fırsatları getir (sahte olmayan)
        deals = db.get_big_deals(min_discount=min_discount, category=category)
        
        # Sahte indirimleri filtrele
        real_deals = []
        for deal in deals:
            if not db.is_fake_discount(deal['asin']):
                # Datetime'ları string'e çevir
                deal['first_seen'] = deal['first_seen'].isoformat() if deal['first_seen'] else None
                deal['last_updated'] = deal['last_updated'].isoformat() if deal['last_updated'] else None
                
                # Decimal'ları float'a çevir
                deal['current_price'] = float(deal['current_price'])
                deal['list_price'] = float(deal['list_price'])
                
                real_deals.append(deal)
        
        # Limit uygula
        real_deals = real_deals[:limit]
        
        return jsonify({
            "success": True,
            "count": len(real_deals),
            "deals": real_deals,
            "filters": {
                "min_discount": min_discount,
                "category": category,
                "limit": limit
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/deals/new', methods=['GET'])
def get_new_deals():
    """Son 1 saatte bulunan yeni fırsatlar"""
    try:
        hours = request.args.get('hours', 1, type=int)
        
        new_deals = db.get_new_deals(hours=hours)
        
        # Format edilmiş sonuçlar
        formatted_deals = []
        for deal in new_deals:
            deal['first_seen'] = deal['first_seen'].isoformat() if deal['first_seen'] else None
            deal['last_updated'] = deal['last_updated'].isoformat() if deal['last_updated'] else None
            deal['current_price'] = float(deal['current_price'])
            deal['list_price'] = float(deal['list_price'])
            formatted_deals.append(deal)
        
        return jsonify({
            "success": True,
            "count": len(formatted_deals),
            "new_deals": formatted_deals,
            "time_range_hours": hours
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/product/<asin>/history', methods=['GET'])
def get_product_history(asin):
    """Ürün fiyat geçmişi"""
    try:
        days = request.args.get('days', 30, type=int)
        
        price_history = db.get_price_history(asin, days=days)
        
        # Datetime'ları string'e çevir
        formatted_history = []
        for record in price_history:
            formatted_record = {
                'price': float(record['price']),
                'recorded_at': record['recorded_at'].isoformat()
            }
            formatted_history.append(formatted_record)
        
        # Fiyat analizi ekle
        analysis = price_tracker.analyze_price_pattern(asin, days)
        
        return jsonify({
            "success": True,
            "asin": asin,
            "price_history": formatted_history,
            "analysis": analysis,
            "days": days
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/test-notification', methods=['POST'])
def test_notification():
    """Test bildirimi gönder"""
    try:
        data = request.get_json()
        
        if not data or 'device_token' not in data:
            return jsonify({
                "success": False,
                "error": "device_token gerekli"
            }), 400
        
        device_token = data['device_token']
        
        # Test bildirimi gönder
        result = notification_manager.send_test_notification_sync(device_token)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/categories', methods=['GET'])
def get_categories():
    """Mevcut kategorileri getir"""
    try:
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT category, COUNT(*) as product_count, AVG(discount_percent) as avg_discount
            FROM products 
            WHERE discount_percent >= 70
            GROUP BY category
            ORDER BY product_count DESC
        """)
        
        categories = []
        for row in cursor.fetchall():
            categories.append({
                'category': row[0],
                'product_count': row[1],
                'avg_discount': round(float(row[2]), 1)
            })
        
        cursor.close()
        
        return jsonify({
            "success": True,
            "categories": categories
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Genel istatistikler"""
    try:
        # Fiyat tracker istatistikleri
        price_stats = price_tracker.get_price_statistics()
        
        # Bildirim istatistikleri
        notification_stats = notification_manager.apns_notifier.get_notification_stats()
        
        # Scraper özeti
        scraper_summary = scraper.get_deal_summary()
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "price_tracking": price_stats,
            "notifications": notification_stats,
            "deals_summary": scraper_summary
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """Scheduler durumunu getir"""
    try:
        scheduler_instance = get_scheduler()
        if scheduler_instance:
            status = scheduler_instance.get_status()
            return jsonify({
                "success": True,
                "scheduler": status
            })
        else:
            return jsonify({
                "success": False,
                "error": "Scheduler başlatılmamış"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/trending', methods=['GET'])
def get_trending():
    """Trend gösteren ürünler"""
    try:
        trend_type = request.args.get('type', 'decreasing')  # decreasing, increasing, volatile
        days = request.args.get('days', 7, type=int)
        
        trending_products = price_tracker.get_trending_products(trend_type, days)
        
        # Format et
        formatted_products = []
        for product in trending_products:
            # Datetime'ları string'e çevir
            product['first_seen'] = product['first_seen'].isoformat() if product['first_seen'] else None
            product['last_updated'] = product['last_updated'].isoformat() if product['last_updated'] else None
            
            # Decimal'ları float'a çevir
            product['current_price'] = float(product['current_price'])
            product['list_price'] = float(product['list_price'])
            
            formatted_products.append(product)
        
        return jsonify({
            "success": True,
            "trend_type": trend_type,
            "days": days,
            "count": len(formatted_products),
            "trending_products": formatted_products
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/scrape', methods=['POST'])
def manual_scrape():
    """Manuel scraping tetikle (test için)"""
    try:
        # Sadece development modunda izin ver
        if os.environ.get('FLASK_ENV') != 'development':
            return jsonify({
                "success": False,
                "error": "Bu endpoint sadece development modunda kullanılabilir"
            }), 403
        
        # Scraping başlat
        deals = scraper.scrape_all_deals()
        summary = scraper.get_deal_summary()
        
        return jsonify({
            "success": True,
            "message": "Manuel scraping tamamlandı",
            "scraped_deals": len(deals),
            "summary": summary
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/product/<asin>', methods=['GET'])
def get_product_detail(asin):
    """Tek ürün detayı"""
    try:
        cursor = db.conn.cursor()
        cursor.execute("SELECT * FROM products WHERE asin = %s", (asin,))
        
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            return jsonify({
                "success": False,
                "error": "Ürün bulunamadı"
            }), 404
        
        # Tuple'ı dict'e çevir
        columns = [desc[0] for desc in cursor.description]
        product = dict(zip(columns, row))
        
        # Datetime ve decimal formatla
        product['first_seen'] = product['first_seen'].isoformat() if product['first_seen'] else None
        product['last_updated'] = product['last_updated'].isoformat() if product['last_updated'] else None
        product['current_price'] = float(product['current_price'])
        product['list_price'] = float(product['list_price'])
        
        # Sahte indirim kontrolü
        is_fake = db.is_fake_discount(asin)
        
        # Fiyat analizi
        analysis = price_tracker.analyze_price_pattern(asin)
        
        return jsonify({
            "success": True,
            "product": product,
            "is_fake_discount": is_fake,
            "price_analysis": analysis
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/scrape-site/<site_name>', methods=['POST'])
def scrape_single_site(site_name):
    """Tek site scraping"""
    try:
        products, results = main_scraper.scrape_single_site(site_name)
        
        return jsonify({
            "success": results['success'],
            "site": results['site'],
            "message": f"{site_name} scraping tamamlandı",
            "count": results['count'],
            "saved_count": results.get('saved_count', 0),
            "scrape_time": results['scrape_time'],
            "error": results['error']
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/site-stats', methods=['GET'])
def get_site_stats():
    """Site bazlı istatistikler"""
    try:
        stats = main_scraper.get_site_statistics()
        
        return jsonify({
            "success": True,
            "statistics": stats
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/test-html', methods=['GET'])
def test_html():
    """Amazon HTML'ini döndür (debug için)"""
    import requests
    url = "https://www.amazon.com.tr/s?k=mouse"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        return f"""
        <h1>Amazon HTML Debug</h1>
        <p>Status Code: {response.status_code}</p>
        <p>URL: {url}</p>
        <hr>
        <pre>{response.text}</pre>
        """
    except Exception as e:
        return f"Error: {str(e)}"

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint bulunamadı"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Sunucu hatası"
    }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    print("🚀 Amazon Fırsat Avcısı Backend başlatılıyor...")
    print(f"Port: {port}")
    print(f"Debug mode: {debug}")
    
    app.run(host="0.0.0.0", port=port, debug=False)