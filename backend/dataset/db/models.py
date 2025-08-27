"""
孕妇个人数据库模型定义
"""

from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config.settings import SQLALCHEMY_DATABASE_URL
from datetime import datetime

Base = declarative_base()

class MaternalInfo(Base):
    """
    孕妇基本信息表（核心主表）
    使用自增ID作为主键
    """
    __tablename__ = 'maternal_info'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID（自增）')
    id_card = Column(String(18), unique=True, nullable=False, comment='身份证号（唯一标识）')
    phone = Column(String(20), unique=True, nullable=True, comment='手机号（可选）')
    current_gestational_week = Column(Integer, nullable=True, comment='当前孕周')
    expected_delivery_date = Column(Date, nullable=True, comment='预产期')
    maternal_age = Column(Integer, nullable=True, comment='准妈妈年龄')
    
    # 关联其他表
    pregnancy_histories = relationship("MaternalPregnancyHistory", back_populates="maternal", cascade="all, delete-orphan")
    health_conditions = relationship("MaternalHealthCondition", back_populates="maternal", cascade="all, delete-orphan")
    medical_files = relationship("MaternalMedicalFiles", back_populates="maternal", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MaternalInfo(id={self.id}, id_card='{self.id_card}')>"


class MaternalPregnancyHistory(Base):
    """
    孕产史表（一对多）
    外键关联孕妇基本信息表的自增ID
    """
    __tablename__ = 'maternal_pregnancy_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='记录ID')
    maternal_id = Column(Integer, ForeignKey('maternal_info.id'), nullable=False, comment='关联孕妇ID')
    pregnancy_count = Column(Integer, nullable=True, comment='既往妊娠次数')
    bad_pregnancy_history = Column(Text, nullable=True, comment='既往不良孕史（如流产、早产等）')
    delivery_method = Column(String(50), nullable=True, comment='既往分娩方式（顺产/剖宫产等）')
    
    # 关联主表
    maternal = relationship("MaternalInfo", back_populates="pregnancy_histories")
    
    def __repr__(self):
        return f"<MaternalPregnancyHistory(id={self.id}, maternal_id={self.maternal_id})>"

class MaternalHealthCondition(Base):
    """
    基础健康状况表（一对多）
    外键关联孕妇基本信息表的自增ID
    """
    __tablename__ = 'maternal_health_condition'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='记录ID')
    maternal_id = Column(Integer, ForeignKey('maternal_info.id'), nullable=False, comment='关联孕妇ID')
    has_hypertension = Column(Boolean, default=False, comment='是否有高血压')
    has_diabetes = Column(Boolean, default=False, comment='是否有糖尿病')
    has_thyroid_disease = Column(Boolean, default=False, comment='是否有甲状腺疾病')
    has_heart_disease = Column(Boolean, default=False, comment='是否有心脏病')
    has_liver_disease = Column(Boolean, default=False, comment='是否有肝脏疾病')
    allergy_history = Column(Text, nullable=True, comment='过敏史详情')
    
    # 关联主表
    maternal = relationship("MaternalInfo", back_populates="health_conditions")
    
    def __repr__(self):
        return f"<MaternalHealthCondition(id={self.id}, maternal_id={self.maternal_id})>"

class MaternalMedicalFiles(Base):
    """
    诊断报告/影像数据表
    外键关联孕妇基本信息表的自增ID
    """
    __tablename__ = 'maternal_medical_files'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='文件记录ID')
    maternal_id = Column(Integer, ForeignKey('maternal_info.id'), nullable=False, comment='关联孕妇ID')
    file_name = Column(String(255), nullable=False, comment='文件名')
    file_path = Column(String(512), nullable=False, comment='文件存储路径（服务器绝对路径或云存储URL）')
    file_type = Column(String(50), nullable=False, comment='文件类型（如：pdf、jpg、dcm、docx等）')
    file_size = Column(Integer, nullable=True, comment='文件大小（字节）')
    upload_time = Column(DateTime, default=datetime.now, comment='上传时间')
    file_desc = Column(Text, nullable=True, comment='文件描述（如：24周B超报告、唐筛结果等）')
    check_date = Column(Date, nullable=True, comment='检查日期')
    
    # 关联主表
    maternal = relationship("MaternalInfo", back_populates="medical_files")
    
    def __repr__(self):
        return f"<MaternalMedicalFiles(id={self.id}, file_name='{self.file_name}', maternal_id={self.maternal_id})>"

# 数据库引擎及会话工具
def get_db_engine():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)
    return engine

def create_tables(engine):
    """创建所有表结构"""
    Base.metadata.create_all(engine)

def get_session(engine):
    """获取数据库会话"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()