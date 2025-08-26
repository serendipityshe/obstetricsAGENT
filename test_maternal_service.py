# tests/test_maternal_service.py
import pytest
from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.dataset.db.models import Base, MaternalInfo, MaternalPregnancyHistory, MaternalHealthCondition, MaternalMedicalFiles
from backend.dataset.db.repository import MaternalRepository
from backend.dataset.db.service import MaternalService

import sys
import os
# 将当前目录（项目根目录）加入Python路径
sys.path.append(os.path.abspath("."))

# 使用内存数据库进行测试，避免影响真实数据
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def db_session():
    """创建测试用数据库会话，每个测试函数独立执行"""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)  # 创建所有表
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)  # 清理测试数据

@pytest.fixture(scope="function")
def maternal_repository(db_session):
    """创建Repository测试实例"""
    return MaternalRepository(db_session)

@pytest.fixture(scope="function")
def maternal_service(monkeypatch):
    """创建Service测试实例，替换真实数据库连接"""
    # 猴子补丁替换数据库URL为测试URL
    monkeypatch.setattr("backend.config.settings.SQLALCHEMY_DATABASE_URL", TEST_DATABASE_URL)
    return MaternalService()

class TestMaternalRepository:
    """测试数据访问层"""
    
    def test_create_maternal_info(self, maternal_repository):
        """测试创建孕妇基本信息"""
        # 执行创建操作
        result = maternal_repository.create_maternal_info(
            id_card="110101199001011235",
            phone="13800138000",
            maternal_age=30,
            expected_delivery_date=date(2024, 12, 31)
        )
        
        # 验证结果
        assert result.id is not None  # 自增ID已生成
        assert result.id_card == "110101199001011235"
        assert result.phone == "13800138000"
        assert result.maternal_age == 30
    
    def test_get_maternal_info_by_id(self, maternal_repository):
        """测试通过ID查询孕妇信息"""
        # 先创建一条数据
        info = maternal_repository.create_maternal_info(id_card="110101199001011235")
        # 查询该数据
        result = maternal_repository.get_maternal_info_by_id(info.id)
        assert result is not None
        assert result.id_card == "110101199001011235"
    
    def test_get_maternal_info_by_id_card(self, maternal_repository):
        """测试通过身份证号查询孕妇信息"""
        # 先创建一条数据
        maternal_repository.create_maternal_info(id_card="110101199001011235")
        # 查询该数据
        result = maternal_repository.get_maternal_info_by_id_card("110101199001011235")
        assert result is not None
        assert result.id_card == "110101199001011235"
    
    def test_update_maternal_info(self, maternal_repository):
        """测试更新孕妇信息"""
        # 先创建一条数据
        info = maternal_repository.create_maternal_info(id_card="110101199001011235")
        # 执行更新操作
        updated = maternal_repository.update_maternal_info(
            info_id=info.id,
            phone="13900139000",
            current_gestational_week=24
        )
        # 验证更新结果
        assert updated.phone == "13900139000"
        assert updated.current_gestational_week == 24
    
    def test_delete_maternal_info(self, maternal_repository):
        """测试删除孕妇信息"""
        # 先创建一条数据
        info = maternal_repository.create_maternal_info(id_card="110101199001011235")
        # 执行删除操作
        result = maternal_repository.delete_maternal_info(info.id)
        assert result is True
        # 验证数据已删除
        deleted_info = maternal_repository.get_maternal_info_by_id(info.id)
        assert deleted_info is None
    
    def test_create_pregnancy_history(self, maternal_repository):
        """测试创建孕产史记录"""
        # 先创建孕妇信息
        info = maternal_repository.create_maternal_info(id_card="110101199001011235")
        # 创建孕产史
        history = maternal_repository.create_pregnancy_history(
            maternal_id=info.id,
            pregnancy_count=2,
            delivery_method="顺产"
        )
        # 验证结果
        assert history.id is not None
        assert history.maternal_id == info.id
        assert history.pregnancy_count == 2
    
    def test_create_health_condition(self, maternal_repository):
        """测试创建健康状况记录"""
        info = maternal_repository.create_maternal_info(id_card="110101199001011235")
        condition = maternal_repository.create_health_condition(
            maternal_id=info.id,
            has_hypertension=True,
            allergy_history="青霉素过敏"
        )
        assert condition.has_hypertension is True
        assert condition.allergy_history == "青霉素过敏"
    
    def test_create_medical_file(self, maternal_repository):
        """测试创建医疗文件记录"""
        info = maternal_repository.create_maternal_info(id_card="110101199001011235")
        file = maternal_repository.create_medical_file(
            maternal_id=info.id,
            file_name="B超报告.pdf",
            file_path="/data/files/123.pdf",
            file_type="pdf",
            file_size=102400,
            check_date=date(2024, 5, 1)
        )
        assert file.file_name == "B超报告.pdf"
        assert file.file_type == "pdf"
        assert file.check_date == date(2024, 5, 1)

class TestMaternalService:
    """测试服务层"""
    
    def test_service_create_and_get(self, maternal_service):
        """测试服务层的创建和查询功能"""
        # 创建孕妇信息
        info = maternal_service.create_maternal_info(
            id_card="310101199505055679",
            phone="13700137001",
            maternal_age=29
        )
        assert info.id is not None
        
        # 通过ID查询
        retrieved = maternal_service.get_maternal_info_by_id(info.id)
        assert retrieved is not None
        assert retrieved.phone == "13700137001"
        
        # 通过身份证号查询
        by_id_card = maternal_service.get_maternal_info_by_id_card("310101199505055679")
        assert by_id_card.id == info.id
    
    def test_service_associated_tables(self, maternal_service):
        """测试服务层对关联表的操作"""
        # 创建主表信息
        info = maternal_service.create_maternal_info(id_card="440101199203034568")
        
        # 创建关联表记录
        history = maternal_service.create_pregnancy_history(
            maternal_id=info.id,
            bad_pregnancy_history="无"
        )
        condition = maternal_service.create_health_condition(
            maternal_id=info.id,
            has_diabetes=False
        )
        
        # 查询关联表记录
        histories = maternal_service.get_pregnancy_histories(info.id)
        conditions = maternal_service.get_health_conditions(info.id)
        
        assert len(histories) == 1
        assert histories[0].id == history.id
        assert len(conditions) == 1
        assert conditions[0].has_diabetes is False
    
    def test_service_delete_cascade(self, maternal_service):
        """测试级联删除（删除主表记录后关联表记录也被删除）"""
        info = maternal_service.create_maternal_info(id_card="510101199807078901")
        # 创建关联记录
        maternal_service.create_pregnancy_history(maternal_id=info.id)
        maternal_service.create_medical_file(
            maternal_id=info.id,
            file_name="test.txt",
            file_path="/test",
            file_type="txt"
        )
        
        # 删除主表记录
        delete_result = maternal_service.delete_maternal_info(info.id)
        assert delete_result is True
        
        # 验证关联记录已被删除
        session = maternal_service._get_session()
        try:
            # 查询孕产史（应无结果）
            histories = session.query(MaternalPregnancyHistory).filter(
                MaternalPregnancyHistory.maternal_id == info.id
            ).all()
            assert len(histories) == 0
            
            # 查询医疗文件（应无结果）
            files = session.query(MaternalMedicalFiles).filter(
                MaternalMedicalFiles.maternal_id == info.id
            ).all()
            assert len(files) == 0
        finally:
            session.close()