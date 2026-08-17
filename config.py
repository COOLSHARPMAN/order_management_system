"""
系统配置文件
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """应用配置"""
    
    # 基础配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # 数据库
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///shop_manager.db')
    
    # 管理员
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    # AI 配置
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'deepseek')
    AI_API_KEY = os.getenv('AI_API_KEY', '')
    AI_MODEL = os.getenv('AI_MODEL', 'deepseek-chat')
    
    # 淘宝 API
    TAOBAO_APP_KEY = os.getenv('TAOBAO_APP_KEY', '')
    TAOBAO_APP_SECRET = os.getenv('TAOBAO_APP_SECRET', '')


class PlatformConfig:
    """电商平台配置模板"""
    
    # 淘宝/天猫
    TAOBAO = {
        'name': '淘宝/天猫',
        'code': 'taobao',
        'api_url': 'https://eco.taobao.com/router/rest',
        'auth_url': 'https://oauth.taobao.com/authorize',
        'icon': 'taobao'
    }
    
    # 1688
    ALI1688 = {
        'name': '1688',
        'code': 'ali1688',
        'api_url': 'https://gw.open.1688.com/openapi/',
        'auth_url': 'https://auth.1688.com/oauth/authorize',
        'icon': 'ali1688'
    }
    
    # 拼多多
    PDD = {
        'name': '拼多多',
        'code': 'pdd',
        'api_url': 'https://gw-api.pinduoduo.com/api/router',
        'auth_url': 'https://mms.pinduoduo.com/open.html',
        'icon': 'pdd'
    }
    
    # 抖店
    DOUDIAN = {
        'name': '抖音小店',
        'code': 'doudian',
        'api_url': 'https://openapi-fxg.jinritemai.com/',
        'auth_url': 'https://fxg.jinritemai.com/',
        'icon': 'doudian'
    }
