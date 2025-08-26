"""
孕妇个人数据库服务层
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import date
from .models import MaternalInfo, get_db_engine, create_tables, get_session
from .repository import MaternalRepository
from .config import SQLALCHEMY_DATABASE_URL

class MaternalService:
    """
    孕妇信息服务类
    """
    
    def __init__(self):
        # 初始化数据库
        self.engine = get_db_engine()
        create_tables(self.engine)
    
    def _get_session(self) -> Session:
        """
        获取数据库会话
        """
        return get_session(self.engine)
    
    def create_maternal_info(
        self,
        maternal_name: Optional[str] = None,
        expected_delivery_date: Optional[date] = None,
        maternal_age: Optional[int] = None,
        pregnancy_history: Optional[str] = None,
        health_status: Optional[str] = None,
        baby_name: Optional[str] = None
    ) -> MaternalInfo:
        """
        创建孕妇信息记录
        """
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.create_maternal_info(
                maternal_name=maternal_name,
                expected_delivery_date=expected_delivery_date,
                maternal_age=maternal_age,
                pregnancy_history=pregnancy_history,
                health_status=health_status,
                baby_name=baby_name
            )
        finally:
            db_session.close()
    
    def get_maternal_info_by_id(self, info_id: int) -> Optional[MaternalInfo]:
        """
        根据ID获取孕妇信息
        """
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.get_maternal_info_by_id(info_id)
        finally:
            db_session.close()
    
    def get_all_maternal_infos(self) -> List[MaternalInfo]:
        """
        获取所有孕妇信息
        """
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.get_all_maternal_infos()
        finally:
            db_session.close()
    
    def update_maternal_info(
        self,
        info_id: int,
        maternal_name: Optional[str] = None,
        expected_delivery_date: Optional[date] = None,
        maternal_age: Optional[int] = None,
        pregnancy_history: Optional[str] = None,
        health_status: Optional[str] = None,
        baby_name: Optional[str] = None
    ) -> Optional[MaternalInfo]:
        """
        更新孕妇信息
        """
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.update_maternal_info(
                info_id=info_id,
                maternal_name=maternal_name,
                expected_delivery_date=expected_delivery_date,
                maternal_age=maternal_age,
                pregnancy_history=pregnancy_history,
                health_status=health_status,
                baby_name=baby_name
            )
        finally:
            db_session.close()
    
    def delete_maternal_info(self, info_id: int) -> bool:
        """
        删除孕妇信息
        """
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.delete_maternal_info(info_id)
        finally:
            db_session.close()