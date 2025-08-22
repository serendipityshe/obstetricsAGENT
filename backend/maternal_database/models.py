"""
孕妇个人数据库模型定义
"""

from sqlalchemy import Column, Integer, String, Date, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import SQLALCHEMY_DATABASE_URL

Base = declarative_base()

class MaternalInfo(Base):
    """
    孕妇个人信息表
    """
    __tablename__ = 'maternal_info'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')
    maternal_name = Column(String(100), nullable=True, comment='孕妇姓名')
    expected_delivery_date = Column(Date, nullable=True, comment='预产期')
    maternal_age = Column(Integer, nullable=True, comment='准妈妈年龄')
    pregnancy_history = Column(Text, nullable=True, comment='孕产史')
    health_status = Column(Text, nullable=True, comment='基础健康状况')
    baby_name = Column(String(100), nullable=True, comment='宝宝名称')
    
    def __repr__(self):
        return f"<MaternalInfo(id={self.id}, baby_name='{self.baby_name}')>"

def get_db_engine():
    """
    获取数据库引擎
    """
    engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)
    return engine

def create_tables(engine):
    """
    创建所有表
    """
    Base.metadata.create_all(engine)

def get_session(engine):
    """
    获取数据库会话
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()