import pytest
import requests
import json
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.dataset.db.models import Base, MaternalInfo
from backend.dataset.db.repository import MaternalRepository
from backend.dataset.db.service import MaternalService

# 配置基础URL（服务器API地址）
BASE_URL = "http://223.109.239.11:26159"  # 已修改为服务器API地址

# 数据库测试相关配置（修改为服务器数据库信息）
# 格式：数据库类型+驱动://用户名:密码@服务器IP:端口/数据库名
TEST_DATABASE_URL = "postgresql+psycopg2://maternal_user:021030@223.109.239.11:26160/maternal_db"
# 示例（请替换为实际信息）：
# TEST_DATABASE_URL = "postgresql://maternal_user:secure_password@192.168.122.2:5432/maternal_db"

@pytest.fixture(scope="function")
def db_session():
    """创建测试用数据库会话，连接服务器数据库"""
    # 连接服务器数据库（禁用池化避免连接复用问题）
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,  # 检测连接有效性
        pool_recycle=300     # 连接超时回收（秒）
    )
    
    # 仅在测试环境创建表（生产环境请谨慎）
    # 注意：如果服务器数据库已有表结构，可注释掉create_all()
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    
    # 测试结束后清理测试数据（保留表结构）
    session.rollback()  # 回滚未提交的事务
    # 可选：删除测试生成的数据（根据实际表名调整）
    session.query(MaternalInfo).delete()
    session.commit()
    
    session.close()
    # 生产环境服务器请不要执行drop_all()！
    # Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def maternal_repository(db_session):
    """创建Repository测试实例（连接服务器数据库）"""
    return MaternalRepository(db_session)

@pytest.fixture(scope="function")
def maternal_service(monkeypatch):
    """创建Service测试实例，指向服务器数据库"""
    # 替换配置中的数据库地址为服务器地址
    monkeypatch.setattr("backend.config.settings.SQLALCHEMY_DATABASE_URL", TEST_DATABASE_URL)
    return MaternalService()

class TestMaternalDatabaseCRUD:
    """测试服务器数据库的CRUD操作"""
    
    # 数据库Repository层测试（操作服务器数据库）
    def test_create_maternal(self, maternal_repository):
        """测试在服务器创建孕妇信息"""
        result = maternal_repository.create_maternal_info(
            id_card="110101199001011235",
            phone="13800138000",
            maternal_age=30,
            expected_delivery_date=date(2024, 12, 31)
        )
        assert result.id is not None
        assert result.id_card == "110101199001011235"
    
    def test_get_maternal_by_id(self, maternal_repository):
        """测试从服务器查询孕妇信息"""
        info = maternal_repository.create_maternal_info(id_card="110101199001011235")
        result = maternal_repository.get_maternal_info_by_id(info.id)
        assert result is not None
        assert result.id == info.id
    
    def test_update_maternal(self, maternal_repository):
        """测试更新服务器上的孕妇信息"""
        info = maternal_repository.create_maternal_info(id_card="110101199001011235")
        updated = maternal_repository.update_maternal_info(
            info_id=info.id,
            phone="13900139000"
        )
        assert updated.phone == "13900139000"
    
    def test_delete_maternal(self, maternal_repository):
        """测试删除服务器上的孕妇信息"""
        info = maternal_repository.create_maternal_info(id_card="110101199001011235")
        result = maternal_repository.delete_maternal_info(info.id)
        assert result is True
        assert maternal_repository.get_maternal_info_by_id(info.id) is None
    
    # 数据库Service层测试（操作服务器数据库）
    def test_service_crud_operations(self, maternal_service):
        """测试服务层对服务器数据库的CRUD操作"""
        # 创建
        info = maternal_service.create_maternal_info(
            id_card="310101199505055679",
            phone="13700137001"
        )
        assert info.id is not None
        
        # 查询
        retrieved = maternal_service.get_maternal_info_by_id(info.id)
        assert retrieved.phone == "13700137001"
        
        # 更新
        updated = maternal_service.update_maternal_info(
            info_id=info.id,
            maternal_age=29
        )
        assert updated.maternal_age == 29
        
        # 删除
        delete_result = maternal_service.delete_maternal_info(info.id)
        assert delete_result is True

class TestChatQAApi:
    """测试服务器上的问答接口功能"""
    
    def test_create_chat_session(self):
        """测试创建对话会话（服务器接口）"""
        url = f"{BASE_URL}/api/v1/chat/new_session"
        response = requests.post(url)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "session_id" in data
    
    def test_medical_qa_basic(self):
        """测试基础问答功能（服务器接口）"""
        # 1. 先创建会话（这一步没问题）
        session_response = requests.post(f"{BASE_URL}/api/v1/chat/new_session")
        assert session_response.status_code == 200  # 先确保会话创建成功
        session_id = session_response.json()["session_id"]

        # 2. 发送问答请求（关键修改：用data=data传递form-data参数）
        url = f"{BASE_URL}/api/v1/chat/qa"
        data = {
            "query": "孕期血糖高怎么办？",       # 必须让接口读到这个query
            "user_type": "pregnant_mother",
            "session_id": session_id
        }
        # 关键修改：将json=data 改为 data=data（传递form-data格式）
        response = requests.post(url, data=data)
        
        # 3. 断言验证
        assert response.status_code == 200
        qa_data = response.json()
        assert qa_data["status"] == "success"
        assert "answer" in qa_data
        assert len(qa_data["answer"]) > 0
    
    def test_get_chat_history(self):
        """测试获取对话历史（服务器接口）"""
        # 1. 创建会话
        session_response = requests.post(f"{BASE_URL}/api/v1/chat/new_session")
        assert session_response.status_code == 200  # 确保会话创建成功
        session_id = session_response.json()["session_id"]

        # 2. 发送消息（关键修改：用data参数传递form-data格式）
        qa_response = requests.post(
            f"{BASE_URL}/api/v1/chat/qa",
            data={  # 改为data参数，而非json
                "query": "胎动频繁正常吗？", 
                "session_id": session_id,
                "user_type": "pregnant_mother"  # 补充user_type参数（可选，默认是doctor）
            }
        )
        # 新增断言：确保消息发送成功（避免因发送失败导致历史为空）
        assert qa_response.status_code == 200, f"消息发送失败：{qa_response.text}"

        # 3. 获取历史记录
        url = f"{BASE_URL}/api/v1/chat/session/{session_id}/history"
        response = requests.get(url)
        assert response.status_code == 200
        history_data = response.json()
        assert history_data["status"] == "success"
        assert len(history_data["history"]) >= 2  # 现在应该能满足预期
