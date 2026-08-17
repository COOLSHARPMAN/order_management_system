"""
主路由 - 页面和API接口
"""
import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Product, Stock, Order, OrderItem, InventoryLog, ReplenishmentSuggestion
from services.order_service import OrderService, InventoryService
from services.ai_service import AIService
from services.platform_service import PlatformService

main_bp = Blueprint('main', __name__)
order_service = OrderService()
inventory_service = InventoryService()
ai_service = AIService()
platform_service = PlatformService()


# ==================== 登录页面 ====================

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        
        return render_template('login.html', error='用户名或密码错误')
    
    return render_template('login.html')


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))


# ==================== 首页/仪表盘 ====================

@main_bp.route('/')
@login_required
def dashboard():
    """控制台首页"""
    stats = order_service.get_order_stats()
    stock_status = inventory_service.get_stock_status()
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         stock_status=stock_status,
                         ai_available=ai_service.is_available())


@main_bp.route('/api/stats')
@login_required
def api_stats():
    """API - 获取统计数据"""
    stats = order_service.get_order_stats()
    return jsonify(stats)


# ==================== 订单管理 ====================

@main_bp.route('/orders')
@login_required
def order_list():
    """订单列表页"""
    status = request.args.get('status', '')
    keyword = request.args.get('keyword', '')
    page = int(request.args.get('page', 1))
    per_page = 20
    
    query = Order.query
    
    if status:
        query = query.filter(Order.status == status)
    if keyword:
        query = query.filter(
            db.or_(
                Order.order_no.contains(keyword),
                Order.buyer_name.contains(keyword),
                Order.buyer_phone.contains(keyword)
            )
        )
    
    orders = query.order_by(Order.order_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('orders/list.html', orders=orders, status=status, keyword=keyword)


@main_bp.route('/api/orders', methods=['GET'])
@login_required
def api_orders():
    """API - 获取订单列表"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    status = request.args.get('status', '')
    
    query = Order.query
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(Order.order_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'orders': [{
            'id': o.id,
            'order_no': o.order_no,
            'platform_name': o.platform_name,
            'buyer_name': o.buyer_name,
            'total_amount': o.total_amount,
            'actual_amount': o.actual_amount,
            'status': o.status,
            'shipping_status': o.shipping_status,
            'order_time': o.order_time.strftime('%Y-%m-%d %H:%M') if o.order_time else '',
            'items_count': len(o.items)
        } for o in orders.items],
        'total': orders.total,
        'pages': orders.pages,
        'current_page': page
    })


@main_bp.route('/orders/create', methods=['GET', 'POST'])
@login_required
def order_create():
    """创建订单"""
    if request.method == 'POST':
        data = request.form.to_dict()
        items = json.loads(request.form.get('items', '[]'))
        data['items'] = items
        
        order = order_service.create_order(data)
        return redirect(url_for('main.order_detail', order_id=order.id))
    
    products = Product.query.filter_by(status='active').all()
    return render_template('orders/create.html', products=products)


@main_bp.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    """订单详情"""
    order = Order.query.get_or_404(order_id)
    return render_template('orders/detail.html', order=order)


@main_bp.route('/api/orders/<int:order_id>/status', methods=['PUT'])
@login_required
def api_update_order_status(order_id):
    """API - 更新订单状态"""
    data = request.get_json()
    order = order_service.update_order_status(
        order_id,
        status=data.get('status', ''),
        shipping_status=data.get('shipping_status', ''),
        tracking_no=data.get('tracking_no', '')
    )
    return jsonify({'success': True, 'order_no': order.order_no})


@main_bp.route('/orders/export', methods=['POST'])
@login_required
def order_export():
    """导出订单"""
    order_ids = request.get_json().get('order_ids', [])
    file_data = order_service.batch_export_orders(order_ids)
    return send_file(
        file_data,
        as_attachment=True,
        download_name=f'orders_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ==================== 商品管理 ====================

@main_bp.route('/products')
@login_required
def product_list():
    """商品列表"""
    category = request.args.get('category', '')
    keyword = request.args.get('keyword', '')
    page = int(request.args.get('page', 1))
    per_page = 20
    
    query = Product.query
    
    if category:
        query = query.filter(Product.category == category)
    if keyword:
        query = query.filter(
            db.or_(
                Product.name.contains(keyword),
                Product.sku.contains(keyword),
                Product.barcode.contains(keyword)
            )
        )
    
    products = query.order_by(Product.updated_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    return render_template('products/list.html', products=products, categories=categories)


@main_bp.route('/products/create', methods=['GET', 'POST'])
@login_required
def product_create():
    """添加商品"""
    if request.method == 'POST':
        product = Product(
            sku=request.form.get('sku'),
            name=request.form.get('name'),
            barcode=request.form.get('barcode'),
            category=request.form.get('category'),
            unit=request.form.get('unit', '件'),
            cost_price=float(request.form.get('cost_price', 0)),
            sell_price=float(request.form.get('sell_price', 0)),
            supplier=request.form.get('supplier'),
            min_stock=int(request.form.get('min_stock', 10)),
            max_stock=int(request.form.get('max_stock', 200)),
            status='active'
        )
        db.session.add(product)
        db.session.flush()
        
        # 同时创建库存记录
        stock = Stock(
            product_id=product.id,
            warehouse='主仓库',
            quantity=int(request.form.get('initial_stock', 0)),
            available_quantity=int(request.form.get('initial_stock', 0))
        )
        db.session.add(stock)
        db.session.commit()
        
        return redirect(url_for('main.product_list'))
    
    return render_template('products/create.html')


@main_bp.route('/api/products/<int:product_id>/stock', methods=['PUT', 'POST'])
@login_required
def api_update_stock(product_id):
    """API - 更新库存"""
    data = request.get_json()
    
    if request.method == 'POST' or data.get('action') == 'add':
        inventory_service.add_stock(
            product_id, 
            data['quantity'], 
            data.get('warehouse', '主仓库'),
            data.get('remark', '')
        )
    elif data.get('action') == 'deduct':
        inventory_service.deduct_stock(
            product_id, 
            data['quantity'],
            data.get('warehouse', '主仓库'),
            data.get('order_no', '')
        )
    
    return jsonify({'success': True})


# ==================== 库存管理 ====================

@main_bp.route('/inventory')
@login_required
def inventory():
    """库存管理页面"""
    stock_status = inventory_service.get_stock_status()
    products = Product.query.filter_by(status='active').all()
    
    stocks = db.session.query(
        Product.id, Product.name, Product.sku, Product.min_stock, Product.max_stock,
        db.func.coalesce(db.func.sum(Stock.quantity), 0).label('total_quantity'),
        db.func.coalesce(db.func.sum(Stock.locked_quantity), 0).label('total_locked'),
        db.func.coalesce(db.func.sum(Stock.available_quantity), 0).label('total_available')
    ).outerjoin(Stock).group_by(Product.id).order_by(Product.name).all()
    
    return render_template('inventory/list.html', 
                         stock_status=stock_status, 
                         stocks=stocks)


@main_bp.route('/inventory/logs')
@login_required
def inventory_logs():
    """库存变动日志"""
    page = int(request.args.get('page', 1))
    logs = InventoryLog.query.order_by(
        InventoryLog.created_at.desc()
    ).paginate(page=page, per_page=50, error_out=False)
    
    return render_template('inventory/logs.html', logs=logs)


# ==================== AI 补货建议 ====================

@main_bp.route('/ai/replenish')
@login_required
def ai_replenish():
    """AI 补货建议页面"""
    suggestions = ReplenishmentSuggestion.query.order_by(
        ReplenishmentSuggestion.created_at.desc()
    ).all()
    
    return render_template('ai/replenish.html', 
                         suggestions=suggestions,
                         ai_available=ai_service.is_available())


@main_bp.route('/api/ai/generate_suggestions', methods=['POST'])
@login_required
def api_generate_suggestions():
    """API - 生成AI补货建议"""
    suggestions = ai_service.generate_replenishment_suggestions()
    return jsonify({
        'success': True, 
        'count': len(suggestions),
        'message': f'成功生成{len(suggestions)}条补货建议'
    })


@main_bp.route('/api/ai/analyze_sales', methods=['GET'])
@login_required
def api_analyze_sales():
    """API - AI销售分析"""
    days = int(request.args.get('days', 30))
    result = ai_service.analyze_sales(days)
    return jsonify({'result': result})


# ==================== 平台对接 ====================

@main_bp.route('/platforms')
@login_required
def platforms():
    """平台管理页面"""
    platforms = platform_service.get_all_platforms()
    return render_template('platforms/list.html', platforms=platforms)


@main_bp.route('/api/platforms/save', methods=['POST'])
@login_required
def api_save_platform():
    """API - 保存平台配置"""
    data = request.get_json()
    platform = platform_service.save_platform_config(data)
    return jsonify({'success': True, 'platform_id': platform.id})


@main_bp.route('/api/platforms/<int:platform_id>/sync_orders', methods=['POST'])
@login_required
def api_sync_orders(platform_id):
    """API - 同步平台订单"""
    sync_log = platform_service.sync_orders_from_taobao(platform_id)
    return jsonify({
        'success': sync_log.status == 'success',
        'message': sync_log.message
    })


# ==================== 仓库设置 ====================

@main_bp.route('/settings')
@login_required
def settings():
    """系统设置"""
    warehouses = ['主仓库', '备用仓库', '退货仓']  # 可从数据库读取
    return render_template('settings/index.html', warehouses=warehouses)


# ==================== 初始化管理员 ====================

def init_admin():
    """初始化管理员账号"""
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', shop_name='我的店铺')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('[系统] 管理员账号已创建：admin / admin123')
