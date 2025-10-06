import os
import asyncio
import json
from typing import List, Dict, Optional
from aioapns import APNs, NotificationRequest, PushType
from datetime import datetime
from database import Database
from dotenv import load_dotenv

load_dotenv()

class APNSNotifier:
    def __init__(self):
        self.key_id = os.environ.get('APNS_KEY_ID')
        self.team_id = os.environ.get('APNS_TEAM_ID') 
        self.key_path = os.environ.get('APNS_KEY_PATH', './apns_key.p8')
        self.bundle_id = os.environ.get('BUNDLE_ID', 'com.yourname.amazonfirsat')
        
        self.db = Database()
        self.apns_client = None
        
        # Test mode kontrolü
        self.use_sandbox = os.environ.get('APNS_USE_SANDBOX', 'true').lower() == 'true'
        
        self._initialize_apns()
    
    def _initialize_apns(self):
        """APNS client'ı başlat"""
        try:
            if not all([self.key_id, self.team_id]):
                print("APNS yapılandırması eksik. Bildirimler devre dışı.")
                return
            
            if not os.path.exists(self.key_path):
                print(f"APNS key dosyası bulunamadı: {self.key_path}")
                return
            
            self.apns_client = APNs(
                key=self.key_path,
                key_id=self.key_id,
                team_id=self.team_id,
                use_sandbox=self.use_sandbox,
                use_alternative_port=False
            )
            
            print(f"APNS client başlatıldı ({'Sandbox' if self.use_sandbox else 'Production'} modu)")
            
        except Exception as e:
            print(f"APNS client başlatma hatası: {e}")
            self.apns_client = None
    
    def create_deal_notification(self, product_data: Dict) -> Dict:
        """Fırsat bildirimi payload'ı oluştur"""
        title = "🔥 Amazon Fırsatı!"
        
        # Ürün adını kısalt
        product_title = product_data['title']
        if len(product_title) > 40:
            product_title = product_title[:37] + "..."
        
        body = f"%{product_data['discount_percent']} indirim: {product_title}"
        
        # Fiyat bilgisi ekle
        current_price = product_data['current_price']
        list_price = product_data['list_price']
        
        subtitle = f"{current_price}₺ (Eski: {list_price}₺)"
        
        payload = {
            "aps": {
                "alert": {
                    "title": title,
                    "subtitle": subtitle,
                    "body": body
                },
                "sound": "default",
                "badge": 1,
                "category": "DEAL_CATEGORY",
                "thread-id": "amazon-deals"
            },
            "custom_data": {
                "asin": product_data['asin'],
                "product_url": product_data['product_url'],
                "current_price": current_price,
                "list_price": list_price,
                "discount_percent": product_data['discount_percent'],
                "category": product_data['category'],
                "image_url": product_data.get('image_url', ''),
                "notification_type": "deal_alert",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return payload
    
    def create_price_drop_notification(self, product_data: Dict, old_price: float) -> Dict:
        """Fiyat düşüşü bildirimi payload'ı oluştur"""
        title = "📉 Fiyat Düştü!"
        
        product_title = product_data['title']
        if len(product_title) > 40:
            product_title = product_title[:37] + "..."
        
        current_price = product_data['current_price']
        price_drop = old_price - current_price
        price_drop_percent = (price_drop / old_price) * 100
        
        body = f"{product_title} - {price_drop:.2f}₺ düştü"
        subtitle = f"{current_price}₺ (-%{price_drop_percent:.1f})"
        
        payload = {
            "aps": {
                "alert": {
                    "title": title,
                    "subtitle": subtitle,
                    "body": body
                },
                "sound": "default",
                "badge": 1,
                "category": "PRICE_DROP_CATEGORY",
                "thread-id": "price-drops"
            },
            "custom_data": {
                "asin": product_data['asin'],
                "product_url": product_data['product_url'],
                "current_price": current_price,
                "old_price": old_price,
                "price_drop": price_drop,
                "price_drop_percent": round(price_drop_percent, 1),
                "category": product_data['category'],
                "notification_type": "price_drop",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return payload
    
    async def send_notification_to_token(self, device_token: str, payload: Dict) -> bool:
        """Tek bir cihaza bildirim gönder"""
        if not self.apns_client:
            print("APNS client mevcut değil")
            return False
        
        try:
            request = NotificationRequest(
                device_token=device_token,
                message=payload,
                push_type=PushType.ALERT
            )
            
            await self.apns_client.send_notification(request)
            print(f"✓ Bildirim gönderildi: {device_token[:10]}...")
            return True
            
        except Exception as e:
            print(f"✗ Bildirim gönderme hatası ({device_token[:10]}...): {e}")
            return False
    
    async def send_deal_notification(self, product_data: Dict, device_tokens: List[str] = None) -> Dict:
        """Fırsat bildirimi gönder"""
        if not self.apns_client:
            return {
                'success': False,
                'message': 'APNS client mevcut değil',
                'sent_count': 0,
                'failed_count': 0
            }
        
        # Device token'ları al
        if not device_tokens:
            device_tokens = self.db.get_all_device_tokens()
        
        if not device_tokens:
            return {
                'success': False,
                'message': 'Kayıtlı cihaz bulunamadı',
                'sent_count': 0,
                'failed_count': 0
            }
        
        # Notification payload'ı oluştur
        payload = self.create_deal_notification(product_data)
        
        # Paralel olarak tüm cihazlara gönder
        tasks = []
        for token in device_tokens:
            task = self.send_notification_to_token(token, payload)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Sonuçları değerlendir
        sent_count = sum(1 for result in results if result is True)
        failed_count = len(results) - sent_count
        
        success = sent_count > 0
        
        print(f"Bildirim özeti: {sent_count} başarılı, {failed_count} başarısız")
        
        return {
            'success': success,
            'message': f'{sent_count} cihaza gönderildi',
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_devices': len(device_tokens)
        }
    
    async def send_price_drop_notification(self, product_data: Dict, old_price: float, device_tokens: List[str] = None) -> Dict:
        """Fiyat düşüşü bildirimi gönder"""
        if not self.apns_client:
            return {
                'success': False,
                'message': 'APNS client mevcut değil',
                'sent_count': 0,
                'failed_count': 0
            }
        
        if not device_tokens:
            device_tokens = self.db.get_all_device_tokens()
        
        if not device_tokens:
            return {
                'success': False,
                'message': 'Kayıtlı cihaz bulunamadı',
                'sent_count': 0,
                'failed_count': 0
            }
        
        payload = self.create_price_drop_notification(product_data, old_price)
        
        tasks = []
        for token in device_tokens:
            task = self.send_notification_to_token(token, payload)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        sent_count = sum(1 for result in results if result is True)
        failed_count = len(results) - sent_count
        
        return {
            'success': sent_count > 0,
            'message': f'{sent_count} cihaza fiyat düşüşü bildirimi gönderildi',
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_devices': len(device_tokens)
        }
    
    async def send_test_notification(self, device_token: str) -> Dict:
        """Test bildirimi gönder"""
        test_payload = {
            "aps": {
                "alert": {
                    "title": "🧪 Test Bildirimi",
                    "subtitle": "Amazon Fırsat Avcısı",
                    "body": "Bildirimler çalışıyor! 🎉"
                },
                "sound": "default",
                "badge": 1
            },
            "custom_data": {
                "notification_type": "test",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        success = await self.send_notification_to_token(device_token, test_payload)
        
        return {
            'success': success,
            'message': 'Test bildirimi gönderildi' if success else 'Test bildirimi gönderilemedi',
            'device_token': device_token[:10] + "..."
        }
    
    async def send_bulk_notifications(self, notifications: List[Dict]) -> Dict:
        """Toplu bildirim gönder"""
        if not self.apns_client or not notifications:
            return {
                'success': False,
                'message': 'APNS client mevcut değil veya bildirim listesi boş',
                'sent_count': 0,
                'failed_count': 0
            }
        
        device_tokens = self.db.get_all_device_tokens()
        
        if not device_tokens:
            return {
                'success': False,
                'message': 'Kayıtlı cihaz bulunamadı',
                'sent_count': 0,
                'failed_count': 0
            }
        
        total_sent = 0
        total_failed = 0
        
        for notification_data in notifications:
            if notification_data.get('type') == 'deal':
                result = await self.send_deal_notification(
                    notification_data['product_data'], 
                    device_tokens
                )
            elif notification_data.get('type') == 'price_drop':
                result = await self.send_price_drop_notification(
                    notification_data['product_data'],
                    notification_data['old_price'],
                    device_tokens
                )
            else:
                continue
            
            total_sent += result.get('sent_count', 0)
            total_failed += result.get('failed_count', 0)
            
            # Bildirimler arası kısa bekleme
            await asyncio.sleep(0.5)
        
        return {
            'success': total_sent > 0,
            'message': f'{len(notifications)} bildirim türü işlendi',
            'sent_count': total_sent,
            'failed_count': total_failed,
            'notification_count': len(notifications)
        }
    
    def get_notification_stats(self) -> Dict:
        """Bildirim istatistikleri"""
        device_count = len(self.db.get_all_device_tokens())
        
        return {
            'apns_configured': self.apns_client is not None,
            'use_sandbox': self.use_sandbox,
            'registered_devices': device_count,
            'bundle_id': self.bundle_id,
            'key_id': self.key_id[:4] + "..." if self.key_id else None,
            'team_id': self.team_id[:4] + "..." if self.team_id else None
        }

# Sync wrapper fonksiyonlar
class NotificationManager:
    def __init__(self):
        self.apns_notifier = APNSNotifier()
    
    def send_deal_notification_sync(self, product_data: Dict, device_tokens: List[str] = None) -> Dict:
        """Senkron fırsat bildirimi gönder"""
        return asyncio.run(self.apns_notifier.send_deal_notification(product_data, device_tokens))
    
    def send_test_notification_sync(self, device_token: str) -> Dict:
        """Senkron test bildirimi gönder"""
        return asyncio.run(self.apns_notifier.send_test_notification(device_token))
    
    def send_bulk_notifications_sync(self, notifications: List[Dict]) -> Dict:
        """Senkron toplu bildirim gönder"""
        return asyncio.run(self.apns_notifier.send_bulk_notifications(notifications))

# Test fonksiyonu
if __name__ == "__main__":
    notifier = NotificationManager()
    
    # İstatistikleri göster
    stats = notifier.apns_notifier.get_notification_stats()
    print("=== BILDIRIM SİSTEMİ DURUMU ===")
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Test ürün verisi
    test_product = {
        'asin': 'B123456789',
        'title': 'Test Ürünü - Çok Güzel Bir Ürün',
        'current_price': 99.99,
        'list_price': 299.99,
        'discount_percent': 75,
        'category': 'Elektronik',
        'product_url': 'https://amazon.com.tr/test',
        'image_url': 'https://example.com/image.jpg'
    }
    
    print("\nTest bildirimi örneği:")
    payload = notifier.apns_notifier.create_deal_notification(test_product)
    print(json.dumps(payload, indent=2, ensure_ascii=False))