"""
孕妇个人数据库访问层
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from .models import (
    User,
    MaternalInfo,
    MaternalPregnancyHistory,
    MaternalHealthCondition,
    MaternalMedicalFiles,
    MaternalDialogue,
)
from datetime import date, datetime


class MaternalRepository:
    """
    孕妇信息数据访问仓库
    """
    
    def __init__(self, db_session: Session):
        self.db_session = db_session

    # ------------------------------
    # 用户基本信息操作
    # ------------------------------
    def create_user_info(
        self,
        user_name: str,
        password: str,
        user_type: str
    ) -> User:
        """创建用户基本信息"""
        user = User(
            user_name=user_name,
            password=password,
            user_type=user_type
        )
        self.db_session.add(user)
        self.db_session.commit()
        self.db_session.refresh(user)
        return user
    
    def get_user_info_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户信息"""
        return self.db_session.query(User).filter(
            User.username == username
        ).all()

    def get_user_info_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户信息"""
        return self.db_session.query(User).filter(
            User.id == user_id
        ).all()
    
    # ------------------------------
    # 孕妇基本信息操作
    # ------------------------------
    def create_maternal_info(
        self,
        id_card: str,  # 新增：身份证号（必填）
        phone: Optional[str] = None,
        current_gestational_week: Optional[int] = None,
        expected_delivery_date: Optional[date] = None,
        maternal_age: Optional[int] = None
    ) -> MaternalInfo:
        """创建孕妇基本信息记录（核心主表）"""
        maternal_info = MaternalInfo(
            id_card=id_card,
            phone=phone,
            current_gestational_week=current_gestational_week,
            expected_delivery_date=expected_delivery_date,
            maternal_age=maternal_age
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
        """根据ID获取孕妇基本信息（包含关联表数据）"""
        return self.db_session.query(MaternalInfo).filter(
            MaternalInfo.id == info_id
        ).all()
    
    def get_maternal_info_by_id_card(self, id_card: str) -> Optional[MaternalInfo]:
        """新增：根据身份证号获取孕妇信息（唯一标识）"""
        return self.db_session.query(MaternalInfo).filter(
            MaternalInfo.id_card == id_card
        ).first()

    def get_maternal_info_by_user_id(self, user_id: int) -> Optional[MaternalInfo]:
        """新增：根据用户ID获取孕妇信息"""
        return self.db_session.query(MaternalInfo).filter(
            MaternalInfo.user_id == user_id
        ).all()
    
    def get_all_maternal_infos(self) -> List[MaternalInfo]:
        """获取所有孕妇基本信息"""
        return self.db_session.query(MaternalInfo).all()
    
    def update_maternal_info(
        self,
        info_id: int,
        id_card: Optional[str] = None,  # 允许更新身份证号（需确保唯一性）
        phone: Optional[str] = None,
        current_gestational_week: Optional[int] = None,
        expected_delivery_date: Optional[date] = None,
        maternal_age: Optional[int] = None
    ) -> Optional[MaternalInfo]:
        """更新孕妇基本信息"""
        maternal_info = self.get_maternal_info_by_id(info_id)
        if not maternal_info:
            return None
        
        if id_card is not None:
            maternal_info.id_card = id_card
        if phone is not None:
            maternal_info.phone = phone
        if current_gestational_week is not None:
            maternal_info.current_gestational_week = current_gestational_week
        if expected_delivery_date is not None:
            maternal_info.expected_delivery_date = expected_delivery_date
        if maternal_age is not None:
            maternal_info.maternal_age = maternal_age
        
        try:
            self.db_session.commit()
            self.db_session.refresh(maternal_info)
            return maternal_info
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e
    
    def delete_maternal_info(self, info_id: int) -> bool:
        """删除孕妇基本信息（级联删除关联表数据）"""
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
    
    # ------------------------------
    # 孕产史操作（关联表）
    # ------------------------------
    def create_pregnancy_history(
        self,
        maternal_id: int,
        pregnancy_count: Optional[int] = None,
        bad_pregnancy_history: Optional[str] = None,
        delivery_method: Optional[str] = None
    ) -> MaternalPregnancyHistory:
        """为孕妇添加孕产史记录"""
        # 验证孕妇是否存在
        if not self.get_maternal_info_by_id(maternal_id):
            raise ValueError(f"孕妇ID {maternal_id} 不存在")
        
        history = MaternalPregnancyHistory(
            maternal_id=maternal_id,
            pregnancy_count=pregnancy_count,
            bad_pregnancy_history=bad_pregnancy_history,
            delivery_method=delivery_method
        )
        
        try:
            self.db_session.add(history)
            self.db_session.commit()
            self.db_session.refresh(history)
            return history
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e
    
    def get_pregnancy_histories(self, maternal_id: int) -> List[MaternalPregnancyHistory]:
        """获取指定孕妇的所有孕产史"""
        return self.db_session.query(MaternalPregnancyHistory).filter(
            MaternalPregnancyHistory.maternal_id == maternal_id
        ).all()
    
    # ------------------------------
    # 健康状况操作（关联表）
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
        """为孕妇添加健康状况记录"""
        if not self.get_maternal_info_by_id(maternal_id):
            raise ValueError(f"孕妇ID {maternal_id} 不存在")
        
        condition = MaternalHealthCondition(
            maternal_id=maternal_id,
            has_hypertension=has_hypertension,
            has_diabetes=has_diabetes,
            has_thyroid_disease=has_thyroid_disease,
            has_heart_disease=has_heart_disease,
            has_liver_disease=has_liver_disease,
            allergy_history=allergy_history
        )
        
        try:
            self.db_session.add(condition)
            self.db_session.commit()
            self.db_session.refresh(condition)
            return condition
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e
    
    def get_health_conditions(self, maternal_id: int) -> List[MaternalHealthCondition]:
        """获取指定孕妇的所有健康状况记录"""
        return self.db_session.query(MaternalHealthCondition).filter(
            MaternalHealthCondition.maternal_id == maternal_id
        ).all()
    
    # ------------------------------
    # 医疗文件操作（关联表）
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
        """为孕妇添加医疗文件记录"""
        if not self.get_maternal_info_by_id(maternal_id):
            raise ValueError(f"孕妇ID {maternal_id} 不存在")
        
        file = MaternalMedicalFiles(
            maternal_id=maternal_id,
            file_name=file_name,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
            upload_time=upload_time or datetime.now(),  # 默认当前时间
            file_desc=file_desc,
            check_date=check_date
        )
        
        try:
            self.db_session.add(file)
            self.db_session.commit()
            self.db_session.refresh(file)
            return file
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e
    
    def get_medical_files(self, maternal_id: int) -> List[MaternalMedicalFiles]:
        """获取指定孕妇的所有医疗文件记录"""
        return self.db_session.query(MaternalMedicalFiles).filter(
            MaternalMedicalFiles.maternal_id == maternal_id
        ).all()

    # ------------------------------
    # 对话记录服务
    # ------------------------------
    def create_dialogue(
        self, 
        maternal_id: int,
        dialogue_content: str,
        vector_store_path: Optional[str] = None
    ) -> MaternalDialogue:
        dialogue = MaternalDialogue(
            maternal_id=maternal_id,
            dialogue_content=dialogue_content,
            vector_store_path=vector_store_path
        )
        try:
            self.db_session.add(dialogue)
            self.db_session.commit()
            self.db_session.refresh(dialogue)
            return dialogue
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e

    def get_dialogues(self, maternal_id: int) -> List[MaternalDialogue]:
        """获取指定孕妇的所有对话记录"""
        return self.db_session.query(MaternalDialogue).filter(
            MaternalDialogue.maternal_id == maternal_id
        ).all()
