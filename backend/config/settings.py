"""
孕妇个人数据库配置文件
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库配置
DATABASE_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'user': os.getenv('POSTGRES_USER', 'maternal_user'),
    'password': os.getenv('POSTGRES_PASSWORD', '021030'),
    'database': os.getenv('POSTGRES_DATABASE', 'maternal_db'),
    'charset': 'utf8'
}

# SQLAlchemy数据库URL
SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"