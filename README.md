📦 掌柜系统 — 电商订单库存管理系统
AI + Python 驱动的中小电商管理工具，一站式管理订单、商品、库存、多平台同步与智能补货。

🚀 快速开始
环境要求
Python 3.10+（推荐 3.13）
pip 包管理器
安装依赖
pip install -r requirements.txt
配置环境变量
复制 .env.example 并按需修改：

cp .env.example .env
# 编辑 .env
启动服务
python app.py
或使用 Flask 命令：

python -m flask run --host=0.0.0.0 --port=5000

首次启动会自动创建演示数据（8 个商品 + 15 条订单），管理员账号为 admin / admin123。

📋 目录结构
order_management_system/
├── app.py                    # 应用入口 & 工厂函数
├── config.py                 # 全局配置（AI、平台、数据库）
├── models.py                 # SQLAlchemy 数据模型
├── requirements.txt          # Python 依赖
├── services/
│   ├── __init__.py
│   ├── order_service.py      # 订单 & 库存业务逻辑
│   ├── ai_service.py         # AI 智能服务（补货建议/销售分析/客服回复）
│   └── platform_service.py   # 电商平台对接（淘宝/1688/拼多多/抖音）
├── routes/
│   ├── __init__.py
│   └── main_routes.py        # Flask 路由 & API
├── templates/                # 前端页面（Bootstrap 5）
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── orders/               # 订单管理页面
│   ├── products/             # 商品管理页面
│   ├── inventory/            # 库存管理页面
│   ├── ai/                   # AI 补货建议页面
│   ├── platforms/            # 平台对接页面
│   └── settings/             # 系统设置页面
└── instance/                 # 数据库文件（运行时生成）
🎯 功能特性
1. 订单管理
📝 手动创建订单（支持多商品、买家信息、备注）
📊 订单列表（分页、状态筛选、关键词搜索）
🔄 实时更新订单状态（待处理 → 已付款 → 已发货 → 已完成）
📦 批量导出 Excel（支持自定义字段）
📋 订单详情查看（商品明细、金额、物流单号）
2. 商品 & 库存管理
🛒 商品 CRUD（SKU、条形码、分类、成本价/售价、库存预警线）
📥 入库 / 出库操作（支持多仓库、批次号、货位）
📊 库存概览（总库存量、低库存预警、库存总价值）
📝 完整库存变动日志（入库/出库/盘点/订单扣减/退货）
3. AI 智能补货
🧠 基于 LLM 的智能补货建议（分析近 30 天销量、库存水位）
📈 AI 销售数据分析（趋势、热销排行、经营建议）
💬 AI 客服自动回复
🔄 降级策略：无 AI 时自动切换为规则引擎
🌐 支持多模型：DeepSeek / OpenAI / 通义千问（OpenAI 兼容接口）
4. 多平台对接
🛒 淘宝 / 天猫
🏭 1688
🛍️ 拼多多
🎵 抖音小店
📥 订单同步（含 API 签名实现）
📤 库存同步到平台
5. 数据统计
📊 今日/本月订单 & 销售额
📈 近 7 天销售趋势
🏷️ 商品销量排行 TOP 10
📦 库存周转分析
6. 系统管理
🔐 用户认证（Flask-Login）
👤 个人信息修改（店铺名、邮箱）
🔑 密码修改 & 忘记密码重置
🗑️ 数据一键清除
⚙️ 仓库配置
⚙️ 配置说明
环境变量（.env）
变量	默认值	说明
SECRET_KEY	dev-secret-key-change-in-production	Flask 密钥，生产环境务必修改
DEBUG	True	调试模式，生产环境设为 False
HOST	0.0.0.0	监听地址
PORT	5000	监听端口
DATABASE_URL	sqlite:///shop_manager.db	数据库连接串
ADMIN_USERNAME	admin	管理员用户名
ADMIN_PASSWORD	admin123	管理员密码
AI_PROVIDER	deepseek	AI 模型提供商：deepseek / openai / qwen
AI_API_KEY	(空)	AI API Key
AI_MODEL	deepseek-chat	模型名称
TAOBAO_APP_KEY	(空)	淘宝开放平台 App Key
TAOBAO_APP_SECRET	(空)	淘宝开放平台 App Secret
AI 模型配置示例
# DeepSeek
AI_PROVIDER=deepseek
AI_API_KEY=sk-xxxxxxxx
AI_MODEL=deepseek-chat

# OpenAI
AI_PROVIDER=openai
AI_API_KEY=sk-xxxxxxxx
AI_MODEL=gpt-4o-mini

# 通义千问 (Qwen)
AI_PROVIDER=qwen
AI_API_KEY=sk-xxxxxxxx
AI_MODEL=qwen-plus
🧱 技术栈
层级	技术
后端框架	Flask 3.1.1
数据库	SQLAlchemy 2.0 + SQLite（默认）
模板引擎	Jinja2 + Bootstrap 5 + FontAwesome
认证	Flask-Login
AI 客户端	OpenAI Python SDK 1.68.2
Excel 导出	openpyxl
数据分析	pandas
定时任务	APScheduler
HTTP 客户端	requests + httpx
🛠️ 开发指南
添加新的 AI 模型 Provider
在 services/ai_service.py 的 _init_client 方法中添加：

elif self.provider == 'dots':
    from openai import OpenAI
    self.client = OpenAI(
        api_key=self.api_key,
        base_url='https://你的-dots-api-endpoint/v1'
    )
同时在 config.py 的环境变量说明中补充对应配置项。

添加新的电商平台
在 config.py 的 PlatformConfig 中添加平台配置模板
在 services/platform_service.py 中实现对应的 API 类
在 models.py 的 Platform 模型中注册平台代码
自定义库存预警规则
修改 services/ai_service.py 中的 _rule_based_replenishment 方法，或配置 AI 模型后使用 generate_replenishment_suggestions。

📝 许可
MIT License

🆘 常见问题
Q：启动后提示数据库错误？
A：首次运行会自动创建数据库。如遇权限问题，检查 instance/ 目录是否可写。

Q：AI 功能不可用？
A：确认 .env 中 AI_API_KEY 已配置且有效。未配置时系统自动降级为规则引擎。

Q：如何重置管理员密码？
A：访问 /reset-password 页面，或直接修改数据库中 users 表。

Q：如何连接小红书 dots 模型？
A：确认 dots API endpoint 和 Key 有效后，在 ai_service.py 中添加 dots provider 分支，并在 .env 中配置 AI_PROVIDER=dots。
