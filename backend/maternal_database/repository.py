"""
孕妇个人数据库访问层
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from .models import MaternalInfo
from datetime import date

class MaternalRepository:
    """
    孕妇信息数据访问仓库
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
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
        maternal_info = MaternalInfo(
            maternal_name=maternal_name,
            expected_delivery_date=expected_delivery_date,
            maternal_age=maternal_age,
            pregnancy_history=pregnancy_history,
            health_status=health_status,
            baby_name=baby_name
        )
        
        try:
            self.db_session.add(maternal_info)
            self.db_session.commit()
            self.db_session.refresh(maternal_info)
            return maternal_info
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e
    
    def get_maternal_info_by_id(self, info_id: int) -> Optional[MaternalInfo]:
        """
        根据ID获取孕妇信息
        """
        return self.db_session.query(MaternalInfo).filter(MaternalInfo.id == info_id).first()
    
    def get_all_maternal_infos(self) -> List[MaternalInfo]:
        """
        获取所有孕妇信息
        """
        return self.db_session.query(MaternalInfo).all()
    
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
        maternal_info = self.get_maternal_info_by_id(info_id)
        if not maternal_info:
            return None
        
        if maternal_name is not None:
            maternal_info.maternal_name = maternal_name
        if expected_delivery_date is not None:
            maternal_info.expected_delivery_date = expected_delivery_date
        if maternal_age is not None:
            maternal_info.maternal_age = maternal_age
        if pregnancy_history is not None:
            maternal_info.pregnancy_history = pregnancy_history
        if health_status is not None:
            maternal_info.health_status = health_status
        if baby_name is not None:
            maternal_info.baby_name = baby_name
        
        try:
            self.db_session.commit()
            self.db_session.refresh(maternal_info)
            return maternal_info
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e
    
    def delete_maternal_info(self, info_id: int) -> bool:
        """
        删除孕妇信息
        """
        maternal_info = self.get_maternal_info_by_id(info_id)
        if not maternal_info:
            return False
        
        try:
            self.db_session.delete(maternal_info)
            self.db_session.commit()
            return True
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e