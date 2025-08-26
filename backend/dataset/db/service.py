"""
孕妇个人数据库服务层
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import date, datetime
from .models import (
    MaternalInfo,
    MaternalPregnancyHistory,
    MaternalHealthCondition,
    MaternalMedicalFiles,
    get_db_engine,
    create_tables,
    get_session
)
from .repository import MaternalRepository


class MaternalService:
    """
    孕妇信息服务类
    """
    
    def __init__(self):
        # 初始化数据库（自动创建表结构）
        self.engine = get_db_engine()
        create_tables(self.engine)
    
    def _get_session(self) -> Session:
        """获取数据库会话（内部工具方法）"""
        return get_session(self.engine)
    
    # ------------------------------
    # 孕妇基本信息服务
    # ------------------------------
    def create_maternal_info(
        self,
        id_card: str,
        phone: Optional[str] = None,
        current_gestational_week: Optional[int] = None,
        expected_delivery_date: Optional[date] = None,
        maternal_age: Optional[int] = None
    ) -> MaternalInfo:
        """创建孕妇基本信息"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.create_maternal_info(
                id_card=id_card,
                phone=phone,
                current_gestational_week=current_gestational_week,
                expected_delivery_date=expected_delivery_date,
                maternal_age=maternal_age
            )
        finally:
            db_session.close()
    
    def get_maternal_info_by_id(self, info_id: int) -> Optional[MaternalInfo]:
        """根据ID获取孕妇信息"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.get_maternal_info_by_id(info_id)
        finally:
            db_session.close()
    
    def get_maternal_info_by_id_card(self, id_card: str) -> Optional[MaternalInfo]:
        """根据身份证号获取孕妇信息"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.get_maternal_info_by_id_card(id_card)
        finally:
            db_session.close()
    
    def get_all_maternal_infos(self) -> List[MaternalInfo]:
        """获取所有孕妇信息"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.get_all_maternal_infos()
        finally:
            db_session.close()
    
    def update_maternal_info(
        self,
        info_id: int,
        id_card: Optional[str] = None,
        phone: Optional[str] = None,
        current_gestational_week: Optional[int] = None,
        expected_delivery_date: Optional[date] = None,
        maternal_age: Optional[int] = None
    ) -> Optional[MaternalInfo]:
        """更新孕妇基本信息"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.update_maternal_info(
                info_id=info_id,
                id_card=id_card,
                phone=phone,
                current_gestational_week=current_gestational_week,
                expected_delivery_date=expected_delivery_date,
                maternal_age=maternal_age
            )
        finally:
            db_session.close()
    
    def delete_maternal_info(self, info_id: int) -> bool:
        """删除孕妇信息（级联删除关联数据）"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.delete_maternal_info(info_id)
        finally:
            db_session.close()
    
    # ------------------------------
    # 孕产史服务
    # ------------------------------
    def create_pregnancy_history(
        self,
        maternal_id: int,
        pregnancy_count: Optional[int] = None,
        bad_pregnancy_history: Optional[str] = None,
        delivery_method: Optional[str] = None
    ) -> MaternalPregnancyHistory:
        """添加孕产史记录"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.create_pregnancy_history(
                maternal_id=maternal_id,
                pregnancy_count=pregnancy_count,
                bad_pregnancy_history=bad_pregnancy_history,
                delivery_method=delivery_method
            )
        finally:
            db_session.close()
    
    def get_pregnancy_histories(self, maternal_id: int) -> List[MaternalPregnancyHistory]:
        """获取指定孕妇的孕产史"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.get_pregnancy_histories(maternal_id)
        finally:
            db_session.close()
    
    # ------------------------------
    # 健康状况服务
    # ------------------------------
    def create_health_condition(
        self,
        maternal_id: int,
        has_hypertension: bool = False,
        has_diabetes: bool = False,
        has_thyroid_disease: bool = False,
        has_heart_disease: bool = False,
        has_liver_disease: bool = False,
        allergy_history: Optional[str] = None
    ) -> MaternalHealthCondition:
        """添加健康状况记录"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.create_health_condition(
                maternal_id=maternal_id,
                has_hypertension=has_hypertension,
                has_diabetes=has_diabetes,
                has_thyroid_disease=has_thyroid_disease,
                has_heart_disease=has_heart_disease,
                has_liver_disease=has_liver_disease,
                allergy_history=allergy_history
            )
        finally:
            db_session.close()
    
    def get_health_conditions(self, maternal_id: int) -> List[MaternalHealthCondition]:
        """获取指定孕妇的健康状况"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.get_health_conditions(maternal_id)
        finally:
            db_session.close()
    
    # ------------------------------
    # 医疗文件服务
    # ------------------------------
    def create_medical_file(
        self,
        maternal_id: int,
        file_name: str,
        file_path: str,
        file_type: str,
        file_size: Optional[int] = None,
        upload_time: Optional[datetime] = None,
        file_desc: Optional[str] = None,
        check_date: Optional[date] = None
    ) -> MaternalMedicalFiles:
        """添加医疗文件记录"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.create_medical_file(
                maternal_id=maternal_id,
                file_name=file_name,
                file_path=file_path,
                file_type=file_type,
                file_size=file_size,
                upload_time=upload_time,
                file_desc=file_desc,
                check_date=check_date
            )
        finally:
            db_session.close()
    
    def get_medical_files(self, maternal_id: int) -> List[MaternalMedicalFiles]:
        """获取指定孕妇的医疗文件"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.get_medical_files(maternal_id)
        finally:
            db_session.close()