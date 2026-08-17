"""
AI 智能服务 - 补货建议、销售分析、智能回复
"""
import json
from datetime import datetime, timedelta
from models import db, Product, Stock, Order, OrderItem, ReplenishmentSuggestion
from config import Config


class AIService:
    """AI 服务封装"""
    
    def __init__(self):
        self.provider = Config.AI_PROVIDER
        self.api_key = Config.AI_API_KEY
        self.model = Config.AI_MODEL
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化 AI 客户端"""
        if not self.api_key:
            print("[AI] 未配置 API Key，AI 功能不可用")
            return
        
        try:
            if self.provider == 'deepseek':
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url='https://api.deepseek.com/v1'
                )
            elif self.provider == 'openai':
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            elif self.provider == 'qwen':
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url='https://dashscope.aliyuncs.com/compatible-mode/v1'
                )
            print(f"[AI] 已连接 {self.provider}，模型: {self.model}")
        except Exception as e:
            print(f"[AI] 初始化失败: {e}")
    
    def is_available(self):
        """检查 AI 是否可用"""
        return self.client is not None
    
    def generate_replenishment_suggestions(self):
        """AI 智能生成补货建议"""
        if not self.is_available():
            return self._rule_based_replenishment()
        
        products = Product.query.filter_by(status='active').all()
        suggestions = []
        
        for product in products:
            # 收集商品数据
            total_stock = sum(s.quantity for s in product.stocks)
            recent_sales = self._get_recent_sales(product.id, days=30)
            
            if total_stock <= product.min_stock:
                prompt = f"""
                你是一位电商库存管理专家。请分析以下商品数据，给出补货建议：

                商品名称：{product.name}
                SKU：{product.sku}
                当前库存：{total_stock}
                最低库存预警：{product.min_stock}
                最高库存：{product.max_stock}
                近30天销量：{recent_sales}
                售价：{product.sell_price}元
                成本价：{product.cost_price}元

                请回答：
                1. 建议补货数量是多少？
                2. 补货理由是什么？
                
                只返回 JSON 格式：{{"suggested_quantity": 数字, "reason": "理由"}}
                """
                
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=300
                    )
                    
                    result = json.loads(response.choices[0].message.content)
                    
                    suggestion = ReplenishmentSuggestion(
                        product_id=product.id,
                        product_name=product.name,
                        current_stock=total_stock,
                        suggested_quantity=result['suggested_quantity'],
                        reason=result['reason']
                    )
                    db.session.add(suggestion)
                    suggestions.append(suggestion)
                    
                except Exception as e:
                    print(f"[AI] 生成建议失败({product.name}): {e}")
                    # 降级到规则判断
                    suggest_qty = max(product.min_stock * 2 - total_stock, 10)
                    suggestion = ReplenishmentSuggestion(
                        product_id=product.id,
                        product_name=product.name,
                        current_stock=total_stock,
                        suggested_quantity=suggest_qty,
                        reason=f'库存低于预警线，近30天销量{recent_sales}件，建议补货{suggest_qty}件'
                    )
                    db.session.add(suggestion)
                    suggestions.append(suggestion)
        
        db.session.commit()
        return suggestions
    
    def _rule_based_replenishment(self):
        """基于规则的补货建议（无 AI 时的降级方案）"""
        products = Product.query.filter_by(status='active').all()
        suggestions = []
        
        for product in products:
            total_stock = sum(s.quantity for s in product.stocks)
            recent_sales = self._get_recent_sales(product.id, days=30)
            
            if total_stock <= product.min_stock:
                # 根据日均销量计算建议补货量
                daily_avg = recent_sales / 30 if recent_sales > 0 else 1
                suggested = max(int(daily_avg * 14 - total_stock), 10)  # 建议补14天销量
                suggested = min(suggested, product.max_stock)
                
                suggestion = ReplenishmentSuggestion(
                    product_id=product.id,
                    product_name=product.name,
                    current_stock=total_stock,
                    suggested_quantity=suggested,
                    reason=f'规则判断：库存{total_stock}低于预警线{product.min_stock}，'
                           f'日均销量{daily_avg:.1f}件，建议补货{suggested}件保障14天销售'
                )
                db.session.add(suggestion)
                suggestions.append(suggestion)
        
        db.session.commit()
        return suggestions
    
    def analyze_sales(self, days=30):
        """AI 销售数据分析"""
        if not self.is_available():
            return self._basic_sales_analysis(days)
        
        # 收集销售数据
        start_date = datetime.utcnow() - timedelta(days=days)
        orders = Order.query.filter(
            Order.order_time >= start_date,
            Order.status != 'cancelled'
        ).all()
        
        total_sales = sum(o.actual_amount for o in orders)
        total_orders = len(orders)
        
        # 商品销量排行
        sales_data = db.session.query(
            Product.name,
            db.func.sum(OrderItem.quantity).label('total_qty'),
            db.func.sum(OrderItem.total_price).label('total_amount')
        ).join(OrderItem).join(Order).filter(
            Order.order_time >= start_date,
            Order.status != 'cancelled'
        ).group_by(Product.id).order_by(db.text('total_qty DESC')).limit(10).all()
        
        prompt = f"""
        你是一位电商数据分析师。请分析以下销售数据：

        分析周期：近{days}天
        总销售额：{total_sales:.2f}元
        总订单数：{total_orders}
        客单价：{total_sales / total_orders:.2f}元 if total_orders > 0 else 0

        热销商品TOP5：
        {chr(10).join([f'{i+1}. {s.name} - 销量{s.total_qty}件 - 销售额{s.total_amount:.2f}元' 
                       for i, s in enumerate(sales_data[:5])])}

        请给出：
        1. 销售趋势分析
        2. 哪些商品需要重点关注（补货/促销/清仓）
        3. 具体的经营建议（3-5条）

        返回 JSON 格式分析报告。
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as e:
            return self._basic_sales_analysis(days)
    
    def _basic_sales_analysis(self, days):
        """基础销售分析"""
        start_date = datetime.utcnow() - timedelta(days=days)
        orders = Order.query.filter(
            Order.order_time >= start_date,
            Order.status != 'cancelled'
        ).all()
        
        total_sales = sum(o.actual_amount for o in orders)
        total_orders = len(orders)
        avg_order = total_sales / total_orders if total_orders > 0 else 0
        
        return json.dumps({
            'period': f'近{days}天',
            'total_sales': round(total_sales, 2),
            'total_orders': total_orders,
            'avg_order_amount': round(avg_order, 2),
            'analysis': '基础数据统计完成，建议配置AI API获取更深入分析'
        }, ensure_ascii=False)
    
    def _get_recent_sales(self, product_id, days=30):
        """获取商品近N天销量"""
        start_date = datetime.utcnow() - timedelta(days=days)
        result = db.session.query(db.func.sum(OrderItem.quantity)).filter(
            OrderItem.product_id == product_id,
            OrderItem.order.has(Order.order_time >= start_date),
            OrderItem.order.has(Order.status != 'cancelled')
        ).scalar()
        return result or 0
    
    def auto_reply_customer(self, question, product_name=''):
        """AI 自动回复客户咨询"""
        if not self.is_available():
            return "AI回复功能需要配置API Key"
        
        prompt = f"""
        你是一位电商客服，请专业、友好地回答客户问题。
        
        商品：{product_name if product_name else '通用'}
        客户问题：{question}
        
        要求：
        - 回答简短专业（50字以内）
        - 友好热情
        - 如果是售后问题，引导联系人工客服
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content
        except Exception as e:
            return "您好，感谢您的咨询！请稍等，客服正在为您服务。"
