"""
订单管理服务
"""
from datetime import datetime, timedelta
from models import db, Order, OrderItem, Product, Stock, InventoryLog


class OrderService:
    """订单业务处理"""
    
    @staticmethod
    def get_order_stats():
        """获取订单统计概览"""
        today = datetime.utcnow().date()
        today_start = datetime(today.year, today.month, today.day)
        
        stats = {
            'today_orders': Order.query.filter(Order.order_time >= today_start).count(),
            'pending_orders': Order.query.filter_by(status='pending').count(),
            'unshipped_orders': Order.query.filter_by(shipping_status='unshipped').count(),
            'total_orders': Order.query.count(),
            'today_amount': db.session.query(db.func.sum(Order.actual_amount))
                .filter(Order.order_time >= today_start).scalar() or 0,
            'month_amount': db.session.query(db.func.sum(Order.actual_amount))
                .filter(Order.order_time >= today_start - timedelta(days=30)).scalar() or 0,
        }
        
        # 最近7天趋势
        daily_stats = []
        for i in range(7):
            day = today - timedelta(days=6 - i)
            day_start = datetime(day.year, day.month, day.day)
            day_end = day_start + timedelta(days=1)
            
            count = Order.query.filter(
                Order.order_time >= day_start,
                Order.order_time < day_end
            ).count()
            amount = db.session.query(db.func.sum(Order.actual_amount)).filter(
                Order.order_time >= day_start,
                Order.order_time < day_end
            ).scalar() or 0
            
            daily_stats.append({
                'date': day.strftime('%m-%d'),
                'count': count,
                'amount': float(amount)
            })
        
        stats['daily_stats'] = daily_stats
        return stats
    
    @staticmethod
    def create_order(data):
        """创建订单（手动录入）"""
        order = Order(
            order_no=data.get('order_no', OrderService._generate_order_no()),
            buyer_name=data.get('buyer_name'),
            buyer_phone=data.get('buyer_phone'),
            buyer_address=data.get('buyer_address'),
            buyer_note=data.get('buyer_note'),
            seller_note=data.get('seller_note'),
            total_amount=data.get('total_amount', 0),
            freight_amount=data.get('freight_amount', 0),
            discount_amount=data.get('discount_amount', 0),
            actual_amount=data.get('actual_amount', 0),
            status='pending',
            shipping_status='unshipped',
            payment_status='unpaid',
            order_time=datetime.utcnow(),
            platform_name='manual'
        )
        db.session.add(order)
        db.session.flush()
        
        # 添加订单商品
        for item_data in data.get('items', []):
            product = Product.query.get(item_data['product_id'])
            item = OrderItem(
                order_id=order.id,
                product_id=item_data['product_id'],
                product_name=product.name if product else item_data.get('product_name'),
                product_sku=product.sku if product else '',
                quantity=item_data.get('quantity', 1),
                price=item_data.get('price', 0),
                total_price=item_data.get('quantity', 1) * item_data.get('price', 0)
            )
            db.session.add(item)
        
        db.session.commit()
        return order
    
    @staticmethod
    def update_order_status(order_id, status, shipping_status=None, tracking_no=None):
        """更新订单状态"""
        order = Order.query.get_or_404(order_id)
        order.status = status
        
        if shipping_status:
            order.shipping_status = shipping_status
            if shipping_status == 'shipped':
                order.ship_time = datetime.utcnow()
        
        if tracking_no:
            order.tracking_no = tracking_no
        
        db.session.commit()
        return order
    
    @staticmethod
    def batch_export_orders(order_ids, format='excel'):
        """批量导出订单"""
        from io import BytesIO
        import openpyxl
        
        orders = Order.query.filter(Order.id.in_(order_ids)).all()
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '订单列表'
        
        # 表头
        headers = ['订单号', '平台', '买家', '电话', '地址', '商品', '数量', 
                   '总金额', '实付', '订单状态', '发货状态', '下单时间']
        ws.append(headers)
        
        for order in orders:
            items_str = '; '.join([f"{item.product_name}x{item.quantity}" for item in order.items])
            ws.append([
                order.order_no,
                order.platform_name,
                order.buyer_name,
                order.buyer_phone,
                order.buyer_address,
                items_str,
                sum(item.quantity for item in order.items),
                order.total_amount,
                order.actual_amount,
                order.status,
                order.shipping_status,
                order.order_time.strftime('%Y-%m-%d %H:%M') if order.order_time else ''
            ])
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output
    
    @staticmethod
    def _generate_order_no():
        """生成订单号"""
        import random
        now = datetime.now()
        date_str = now.strftime('%Y%m%d%H%M%S')
        rand_str = str(random.randint(1000, 9999))
        return f"ORD{date_str}{rand_str}"


class InventoryService:
    """库存管理服务"""
    
    @staticmethod
    def get_stock_status():
        """获取库存概览"""
        total_products = Product.query.count()
        total_stock = db.session.query(db.func.sum(Stock.quantity)).scalar() or 0
        
        # 低库存预警
        low_stock_products = db.session.query(Product).join(Stock).filter(
            Stock.quantity <= Product.min_stock
        ).all()
        
        # 总库存价值
        total_value = db.session.query(
            db.func.sum(Stock.quantity * Product.cost_price)
        ).join(Product).scalar() or 0
        
        return {
            'total_products': total_products,
            'total_stock': int(total_stock),
            'low_stock_count': len(low_stock_products),
            'low_stock_products': [
                {'id': p.id, 'name': p.name, 'sku': p.sku, 'stock': sum(s.quantity for s in p.stocks)}
                for p in low_stock_products[:20]  # 最多显示20个
            ],
            'total_value': float(total_value)
        }
    
    @staticmethod
    def add_stock(product_id, quantity, warehouse='主仓库', remark=''):
        """入库操作"""
        product = Product.query.get_or_404(product_id)
        
        stock = Stock.query.filter_by(
            product_id=product_id, warehouse=warehouse
        ).first()
        
        before_qty = stock.quantity if stock else 0
        
        if not stock:
            stock = Stock(
                product_id=product_id,
                warehouse=warehouse,
                quantity=0,
                locked_quantity=0,
                available_quantity=0
            )
            db.session.add(stock)
        
        stock.quantity += quantity
        stock.available_quantity = stock.quantity - stock.locked_quantity
        
        # 记录日志
        log = InventoryLog(
            product_id=product_id,
            product_name=product.name,
            change_type='入库',
            quantity_change=quantity,
            before_quantity=before_qty,
            after_quantity=stock.quantity,
            operator='admin',
            remark=remark
        )
        db.session.add(log)
        db.session.commit()
        return stock
    
    @staticmethod
    def deduct_stock(product_id, quantity, warehouse='主仓库', order_no=''):
        """出库/扣减库存"""
        product = Product.query.get_or_404(product_id)
        stock = Stock.query.filter_by(
            product_id=product_id, warehouse=warehouse
        ).first()
        
        if not stock or stock.available_quantity < quantity:
            raise ValueError(f"库存不足！商品: {product.name}, 可用库存: {stock.available_quantity if stock else 0}")
        
        before_qty = stock.quantity
        stock.quantity -= quantity
        stock.available_quantity = stock.quantity - stock.locked_quantity
        
        log = InventoryLog(
            product_id=product_id,
            product_name=product.name,
            change_type='出库',
            quantity_change=-quantity,
            before_quantity=before_qty,
            after_quantity=stock.quantity,
            order_no=order_no,
            operator='system',
            remark=f'订单{order_no}出库'
        )
        db.session.add(log)
        db.session.commit()
    
    @staticmethod
    def check_stock(order_id):
        """检查订单库存是否充足"""
        order = Order.query.get_or_404(order_id)
        shortage_items = []
        
        for item in order.items:
            total_available = db.session.query(
                db.func.coalesce(db.func.sum(Stock.available_quantity), 0)
            ).filter(
                Stock.product_id == item.product_id
            ).scalar()
            
            if total_available < item.quantity:
                shortage_items.append({
                    'product_name': item.product_name,
                    'required': item.quantity,
                    'available': int(total_available),
                    'shortage': item.quantity - int(total_available)
                })
        
        return shortage_items
