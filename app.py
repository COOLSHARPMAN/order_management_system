"""
电商订单库存管理系统 - 主程序入口
AI + Python 驱动的中小电商管理工具

功能：
- 订单管理（创建/查询/导出/打印）
- 商品/库存管理（入库/出库/预警）
- AI 智能补货建议（支持 DeepSeek/OpenAI/通义千问）
- 多平台对接（淘宝/1688/拼多多/抖音）
- 数据统计与销售分析

启动方式：
    python app.py
        或
    python -m flask run
"""
import os
import sys

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_login import LoginManager
from models import db, User
from routes.main_routes import main_bp, init_admin
from config import Config


def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 数据库配置
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    # 初始化扩展
    db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # 注册蓝图
    app.register_blueprint(main_bp)
    
    # 创建数据库和初始数据
    with app.app_context():
        db.create_all()
        init_admin()
        
        # 如果没有任何数据，添加演示数据
        from models import Product, Stock
        if Product.query.count() == 0:
            print("[系统] 首次运行，添加演示数据...")
            _add_demo_data()
    
    print(f"""
    ╔══════════════════════════════════════════╗
    ║     📦 掌柜系统 - 电商订单库存管理系统    ║
    ╠══════════════════════════════════════════╣
    ║  地址: http://localhost:{Config.PORT}          ║
    ║  账号: {Config.ADMIN_USERNAME} / {Config.ADMIN_PASSWORD}            ║
    ║  AI:  {'✅ 已配置' if Config.AI_API_KEY else '⚠️ 未配置（规则模式）'}             ║
    ╚══════════════════════════════════════════╝
    """)
    
    return app


def _add_demo_data():
    """添加演示数据"""
    from models import Product, Stock, Order, OrderItem
    from datetime import datetime, timedelta
    import random
    
    # 示例商品
    demo_products = [
        {'sku': 'TSH001', 'name': '纯棉T恤（白色）', 'category': '服装', 
         'cost_price': 25, 'sell_price': 59.9, 'min_stock': 20, 'max_stock': 200},
        {'sku': 'TSH002', 'name': '纯棉T恤（黑色）', 'category': '服装',
         'cost_price': 25, 'sell_price': 59.9, 'min_stock': 20, 'max_stock': 200},
        {'sku': 'JEAN001', 'name': '直筒牛仔裤', 'category': '服装',
         'cost_price': 55, 'sell_price': 129, 'min_stock': 15, 'max_stock': 100},
        {'sku': 'CAP001', 'name': '棒球帽', 'category': '配饰',
         'cost_price': 12, 'sell_price': 39.9, 'min_stock': 30, 'max_stock': 300},
        {'sku': 'MUG001', 'name': '创意马克杯', 'category': '家居',
         'cost_price': 8, 'sell_price': 25.9, 'min_stock': 50, 'max_stock': 500},
        {'sku': 'BAG001', 'name': '帆布手提袋', 'category': '配饰',
         'cost_price': 15, 'sell_price': 49.9, 'min_stock': 20, 'max_stock': 200},
        {'sku': 'SOC001', 'name': '棉袜（3双装）', 'category': '服装',
         'cost_price': 10, 'sell_price': 29.9, 'min_stock': 50, 'max_stock': 500},
        {'sku': 'KEY001', 'name': '金属钥匙扣', 'category': '配饰',
         'cost_price': 3, 'sell_price': 9.9, 'min_stock': 100, 'max_stock': 1000},
    ]
    
    products = []
    for p_data in demo_products:
        product = Product(**p_data, unit='件', status='active')
        db.session.add(product)
        db.session.flush()
        
        # 添加随机库存
        stock = Stock(
            product_id=product.id,
            warehouse='主仓库',
            quantity=random.randint(5, 50),
            available_quantity=random.randint(5, 50)
        )
        db.session.add(stock)
        products.append(product)
    
    db.session.flush()
    
    # 示例订单（过去7天）
    buyer_names = ['王小明', '李美丽', '张大山', '赵小燕', '刘老板']
    addresses = [
        '北京市海淀区中关村大街1号',
        '上海市浦东新区张江高科技园区',
        '广州市天河区体育西路100号',
        '深圳市南山区科技园南区',
        '杭州市西湖区文三路500号',
    ]
    
    for i in range(15):
        days_ago = random.randint(0, 6)
        order_time = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 12))
        
        # 随机选1-3个商品
        order_products = random.sample(products, random.randint(1, 3))
        total = 0
        items = []
        
        for p in order_products:
            qty = random.randint(1, 3)
            price = p.sell_price
            total += price * qty
            items.append({
                'product_id': p.id,
                'product_name': p.name,
                'product_sku': p.sku,
                'quantity': qty,
                'price': price,
                'total_price': price * qty
            })
        
        statuses = ['completed', 'completed', 'shipped', 'paid', 'pending']
        status = random.choice(statuses)
        
        order = Order(
            order_no=f"DEMO{datetime.now().strftime('%Y%m%d')}{i+1:04d}",
            platform_name='手动录入',
            buyer_name=random.choice(buyer_names),
            buyer_phone=f"138{random.randint(10000000, 99999999)}",
            buyer_address=random.choice(addresses),
            total_amount=total,
            actual_amount=round(total * random.uniform(0.85, 0.98), 2),
            status=status,
            shipping_status='shipped' if status == 'shipped' else ('unshipped' if status in ['paid', 'pending'] else 'shipped'),
            payment_status='paid',
            order_time=order_time,
            pay_time=order_time + timedelta(minutes=random.randint(1, 60)),
            ship_time=order_time + timedelta(hours=random.randint(2, 24)) if status in ['shipped', 'completed'] else None,
            tracking_no=f"SF{random.randint(1000000000, 9999999999)}" if status in ['shipped', 'completed'] else ''
        )
        db.session.add(order)
        db.session.flush()
        
        for item_data in items:
            item = OrderItem(order_id=order.id, **item_data)
            db.session.add(item)
    
    db.session.commit()
    print(f"[系统] 已添加 {len(demo_products)} 个演示商品，15 条演示订单")


if __name__ == '__main__':
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
