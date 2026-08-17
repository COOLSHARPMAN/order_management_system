"""
电商平台对接服务 - 淘宝/1688/拼多多 API
"""
import hashlib
import json
import time
from datetime import datetime
import requests
from models import db, Platform, Order, OrderItem, Product, SyncLog


class PlatformService:
    """平台对接服务"""
    
    @staticmethod
    def get_all_platforms():
        """获取所有平台配置"""
        return Platform.query.all()
    
    @staticmethod
    def save_platform_config(data):
        """保存平台配置"""
        platform = Platform.query.filter_by(code=data['code']).first()
        if not platform:
            platform = Platform(
                name=data['name'],
                code=data['code'],
                app_key=data.get('app_key', ''),
                app_secret=data.get('app_secret', ''),
                is_active=True
            )
            db.session.add(platform)
        else:
            platform.app_key = data.get('app_key', platform.app_key)
            platform.app_secret = data.get('app_secret', platform.app_secret)
        
        db.session.commit()
        return platform
    
    @staticmethod
    def sync_orders_from_taobao(platform_id):
        """从淘宝同步订单"""
        platform = Platform.query.get_or_404(platform_id)
        sync_log = SyncLog(
            platform='taobao',
            sync_type='orders',
            status='syncing',
            total_count=0,
            success_count=0,
            fail_count=0
        )
        db.session.add(sync_log)
        db.session.flush()
        
        try:
            # 这里需要接入淘宝API
            # 暂时用模拟数据演示
            mock_orders = PlatformService._mock_taobao_orders()
            
            success = 0
            failed = 0
            
            for order_data in mock_orders:
                try:
                    # 检查订单是否已存在
                    existing = Order.query.filter_by(
                        platform_order_id=order_data['platform_order_id']
                    ).first()
                    
                    if not existing:
                        order = Order(
                            order_no=f"TB{datetime.now().strftime('%Y%m%d%H%M%S')}{success}",
                            platform_order_id=order_data['platform_order_id'],
                            platform_id=platform_id,
                            platform_name='淘宝',
                            buyer_name=order_data.get('buyer_name', ''),
                            buyer_phone=order_data.get('buyer_phone', ''),
                            buyer_address=order_data.get('buyer_address', ''),
                            total_amount=order_data.get('total_amount', 0),
                            actual_amount=order_data.get('actual_amount', 0),
                            status='pending',
                            shipping_status='unshipped',
                            payment_status='paid',
                            order_time=datetime.utcnow(),
                        )
                        db.session.add(order)
                        success += 1
                except Exception as e:
                    failed += 1
            
            sync_log.status = 'success'
            sync_log.success_count = success
            sync_log.fail_count = failed
            sync_log.message = f'同步成功{success}条，失败{failed}条'
            platform.last_sync_time = datetime.utcnow()
            db.session.commit()
            
            return sync_log
            
        except Exception as e:
            sync_log.status = 'failed'
            sync_log.message = str(e)
            db.session.commit()
            return sync_log
    
    @staticmethod
    def sync_stock_to_platform(product_id):
        """同步库存到平台"""
        product = Product.query.get_or_404(product_id)
        total_stock = sum(s.available_quantity for s in product.stocks)
        
        # 这里调用各平台API更新库存
        # ...
        
        return {'product_id': product_id, 'synced_stock': total_stock}
    
    @staticmethod
    def _mock_taobao_orders():
        """模拟淘宝订单数据（演示用）"""
        return [
            {
                'platform_order_id': 'TB202401010001',
                'buyer_name': '张三',
                'buyer_phone': '13800138001',
                'buyer_address': '北京市朝阳区xxx路xx号',
                'total_amount': 299.00,
                'actual_amount': 269.10,
                'items': [
                    {'sku': 'SKU001', 'name': '商品A', 'quantity': 2, 'price': 99.50},
                    {'sku': 'SKU002', 'name': '商品B', 'quantity': 1, 'price': 100.00},
                ]
            },
            {
                'platform_order_id': 'TB202401010002',
                'buyer_name': '李四',
                'buyer_phone': '13900139002',
                'buyer_address': '上海市浦东新区xxx路xx号',
                'total_amount': 599.00,
                'actual_amount': 539.10,
                'items': [
                    {'sku': 'SKU003', 'name': '商品C', 'quantity': 1, 'price': 599.00},
                ]
            }
        ]


class TaobaoAPI:
    """淘宝开放平台 API"""
    
    def __init__(self, app_key, app_secret, access_token=''):
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = access_token
        self.gateway_url = 'https://eco.taobao.com/router/rest'
    
    def _sign(self, params):
        """淘宝API签名"""
        sorted_params = sorted(params.items())
        sign_str = self.app_secret + ''.join([f'{k}{v}' for k, v in sorted_params]) + self.app_secret
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
    
    def get_orders(self, start_time, end_time, page_no=1, page_size=100):
        """获取订单列表"""
        params = {
            'method': 'taobao.trades.sold.get',
            'app_key': self.app_key,
            'session': self.access_token,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'format': 'json',
            'v': '2.0',
            'sign_method': 'md5',
            'fields': 'tid,status,payment,orders.title,orders.num_iid,orders.price,orders.num,receiver_name,receiver_phone,receiver_address,created,pay_time',
            'start_created': start_time,
            'end_created': end_time,
            'page_no': page_no,
            'page_size': page_size
        }
        
        params['sign'] = self._sign(params)
        
        try:
            response = requests.post(self.gateway_url, data=params, timeout=30)
            return response.json()
        except Exception as e:
            return {'error_response': {'msg': str(e)}}


class Alibaba1688API:
    """1688 开放平台 API"""
    
    def __init__(self, app_key, app_secret, access_token=''):
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = access_token
        self.gateway_url = 'https://gw.open.1688.com/openapi/'
    
    def get_orders(self, create_start_time, page_no=1, page_size=100):
        """获取1688订单"""
        # 1688 API 实现
        pass
