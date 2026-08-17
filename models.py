"""
数据库模型 - 订单、商品、库存管理
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """管理员用户"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120))
    shop_name = db.Column(db.String(200), default='我的店铺')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Platform(db.Model):
    """电商平台配置"""
    __tablename__ = 'platforms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # 平台名称
    code = db.Column(db.String(20), unique=True, nullable=False)  # 平台代码
    app_key = db.Column(db.String(100))
    app_secret = db.Column(db.String(100))
    access_token = db.Column(db.String(200))
    refresh_token = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    last_sync_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Product(db.Model):
    """商品表"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), unique=True, index=True)  # SKU编码
    name = db.Column(db.String(300), nullable=False)  # 商品名称
    barcode = db.Column(db.String(100))  # 条形码
    category = db.Column(db.String(100))  # 分类
    unit = db.Column(db.String(20), default='件')  # 单位
    cost_price = db.Column(db.Float, default=0)  # 成本价
    sell_price = db.Column(db.Float, default=0)  # 售价
    supplier = db.Column(db.String(200))  # 供应商
    min_stock = db.Column(db.Integer, default=10)  # 最低库存预警
    max_stock = db.Column(db.Integer, default=200)  # 最高库存
    image_url = db.Column(db.String(500))  # 商品图片
    status = db.Column(db.String(20), default='active')  # active/inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    stocks = db.relationship('Stock', backref='product', lazy=True, cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='product', lazy=True)


class Stock(db.Model):
    """库存表（按仓库/批次）"""
    __tablename__ = 'stocks'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse = db.Column(db.String(100), default='主仓库')  # 仓库名称
    batch_no = db.Column(db.String(100))  # 批次号
    quantity = db.Column(db.Integer, default=0)  # 当前库存量
    locked_quantity = db.Column(db.Integer, default=0)  # 锁定库存（已下单未发货）
    available_quantity = db.Column(db.Integer, default=0)  # 可用库存
    location = db.Column(db.String(100))  # 货位
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(db.Model):
    """订单表"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(100), unique=True, index=True)  # 订单号
    platform_order_id = db.Column(db.String(100))  # 平台订单ID
    platform_id = db.Column(db.Integer, db.ForeignKey('platforms.id'))  # 所属平台
    platform_name = db.Column(db.String(50))  # 平台名称冗余
    
    # 订单信息
    buyer_name = db.Column(db.String(100))  # 买家
    buyer_phone = db.Column(db.String(20))  # 买家电话
    buyer_address = db.Column(db.String(500))  # 收货地址
    buyer_note = db.Column(db.Text)  # 买家备注
    seller_note = db.Column(db.Text)  # 卖家备注
    
    # 金额
    total_amount = db.Column(db.Float, default=0)  # 总金额
    discount_amount = db.Column(db.Float, default=0)  # 优惠金额
    freight_amount = db.Column(db.Float, default=0)  # 运费
    actual_amount = db.Column(db.Float, default=0)  # 实付金额
    
    # 状态
    status = db.Column(db.String(30), default='pending')  # pending/paid/shipped/completed/cancelled
    shipping_status = db.Column(db.String(30), default='unshipped')  # unshipped/shipped/signed
    payment_status = db.Column(db.String(30), default='unpaid')  # unpaid/paid/refund
    shipping_method = db.Column(db.String(100))  # 配送方式
    tracking_no = db.Column(db.String(100))  # 快递单号
    
    # 时间
    order_time = db.Column(db.DateTime)  # 下单时间
    pay_time = db.Column(db.DateTime)  # 付款时间
    ship_time = db.Column(db.DateTime)  # 发货时间
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    platform = db.relationship('Platform', backref='orders')


class OrderItem(db.Model):
    """订单商品明细"""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(300))  # 商品名称冗余
    product_sku = db.Column(db.String(100))  # SKU冗余
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, default=0)  # 单价
    total_price = db.Column(db.Float, default=0)  # 小计


class InventoryLog(db.Model):
    """库存变动日志"""
    __tablename__ = 'inventory_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(300))
    change_type = db.Column(db.String(30))  # 入库/出库/盘点/订单扣减/退货
    quantity_change = db.Column(db.Integer)  # 变动数量（正数入库，负数出库）
    before_quantity = db.Column(db.Integer)
    after_quantity = db.Column(db.Integer)
    order_no = db.Column(db.String(100))  # 关联订单号
    operator = db.Column(db.String(100))  # 操作人
    remark = db.Column(db.Text)  # 备注
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ReplenishmentSuggestion(db.Model):
    """AI智能补货建议"""
    __tablename__ = 'replenishment_suggestions'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(300))
    current_stock = db.Column(db.Integer)
    suggested_quantity = db.Column(db.Integer)  # 建议补货量
    reason = db.Column(db.Text)  # AI生成的理由
    status = db.Column(db.String(20), default='pending')  # pending/applied/ignored
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SyncLog(db.Model):
    """平台同步日志"""
    __tablename__ = 'sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50))  # 平台
    sync_type = db.Column(db.String(30))  # orders/products/shipping
    status = db.Column(db.String(20))  # success/failed
    message = db.Column(db.Text)
    total_count = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    fail_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
