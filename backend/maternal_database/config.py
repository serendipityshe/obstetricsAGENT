"""
孕妇个人数据库配置文件
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库配置
DATABASE_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'maternal_db'),
    'charset': 'utf8mb4'
}

# SQLAlchemy数据库URL
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}?charset={DATABASE_CONFIG['charset']}"