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
        username: str,
        password: str,
        user_type: str
    ) -> User:
        """创建用户基本信息"""
        user = User(
            username=username,
            password_hash=password,
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
        ).first()

    def get_user_info_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户信息"""
        return self.db_session.query(User).filter(
            User.id == user_id
        ).first()
    
    # ------------------------------
    # 孕妇基本信息操作
    # ------------------------------
    def create_maternal_info(
        self,
        user_id: int,
        id_card: Optional[str] = None,
        phone: Optional[str] = None,
        current_gestational_week: Optional[int] = None,
        expected_delivery_date: Optional[date] = None,
        maternal_age: Optional[int] = None
    ) -> MaternalInfo:
        """创建孕妇基本信息（关联用户ID）"""
        maternal_info = MaternalInfo(
            user_id=user_id,
            id_card=id_card,
            phone=phone,
            current_gestational_week=current_gestational_week,
            expected_delivery_date=expected_delivery_date,
            maternal_age=maternal_age
        )
        try:
            self.db_session.add(maternal_info)
            self.db_session.flush()  # 触发数据库插入，捕获约束错误
            return maternal_info
        except Exception as e:
            # 关键：打印详细错误（包含数据库具体约束错误）
            print(f"插入maternal_info失败！详细原因：{str(e)}")
            self.db_session.rollback()
            raise e  # 重新抛出，让上层能捕获
    
    def get_maternal_info_by_id(self, id: int) -> Optional[MaternalInfo]:
        """根据ID获取孕妇基本信息（包含关联表数据）"""
        return self.db_session.query(MaternalInfo).filter(
            MaternalInfo.id == id
        ).first()
    
    def get_maternal_info_by_id_card(self, id_card: str) -> Optional[MaternalInfo]:
        """新增：根据身份证号获取孕妇信息（唯一标识）"""
        return self.db_session.query(MaternalInfo).filter(
            MaternalInfo.id_card == id_card
        ).first()

    def get_maternal_info_by_user_id(self, user_id: int) -> Optional[MaternalInfo]:
        """新增：根据用户ID获取孕妇信息"""
        return self.db_session.query(MaternalInfo).filter(
            MaternalInfo.user_id == user_id
        ).first()
    
    def get_all_maternal_infos(self) -> List[MaternalInfo]:
        """获取所有孕妇基本信息"""
        return self.db_session.query(MaternalInfo).all()
    
    def update_maternal_info(
        self,
        user_id: int,
        id_card: Optional[str] = None,  # 允许更新身份证号（需确保唯一性）
        phone: Optional[str] = None,
        current_gestational_week: Optional[int] = None,
        expected_delivery_date: Optional[date] = None,
        maternal_age: Optional[int] = None
    ) -> Optional[MaternalInfo]:
        """更新孕妇基本信息"""
        maternal_info = self.get_maternal_info_by_user_id(user_id)
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
    
    def delete_maternal_info(self, user_id: int) -> bool:
        """删除孕妇基本信息（级联删除关联表数据）"""
        maternal_info = self.get_maternal_info_by_id(user_id)
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

    def update_pregnancy_history(
        self,
        maternal_id: int,
        pregnancy_count: Optional[int] = None,
        bad_pregnancy_history: Optional[str] = None,
        delivery_method: Optional[str] = None
    ) -> Optional[MaternalPregnancyHistory]:
        """更新孕产史记录"""
        history = self.get_pregnancy_histories(maternal_id)
        if not history:
            return None
        
        if pregnancy_count is not None:
            history.pregnancy_count = pregnancy_count
        if bad_pregnancy_history is not None:
            history.bad_pregnancy_history = bad_pregnancy_history
        if delivery_method is not None:
            history.delivery_method = delivery_method
        
        try:
            self.db_session.commit()
            self.db_session.refresh(history)
            return history
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e
    
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

    def update_health_condition(
        self,
        maternal_id: int,
        has_hypertension: Optional[bool] = None,
        has_diabetes: Optional[bool] = None,
        has_thyroid_disease: Optional[bool] = None,
        has_heart_disease: Optional[bool] = None,
        has_liver_disease: Optional[bool] = None,
        allergy_history: Optional[str] = None
    ) -> Optional[MaternalHealthCondition]:
        """更新健康状况记录"""
        condition = self.get_health_conditions(maternal_id)
        if not condition:
            return None
        
        if has_hypertension is not None:
            condition.has_hypertension = has_hypertension
        if has_diabetes is not None:
            condition.has_diabetes = has_diabetes
        if has_thyroid_disease is not None:
            condition.has_thyroid_disease = has_thyroid_disease
        if has_heart_disease is not None:
            condition.has_heart_disease = has_heart_disease
        if has_liver_disease is not None:
            condition.has_liver_disease = has_liver_disease
        if allergy_history is not None:
            condition.allergy_history = allergy_history
        
        try:
            self.db_session.commit()
            self.db_session.refresh(condition)
            return condition
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e
    
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
    
    def get_medical_files(self, maternal_id: int, file_name: str) -> List[MaternalMedicalFiles]:
        """获取指定孕妇的所有医疗文件记录"""
        return self.db_session.query(MaternalMedicalFiles).filter(
            MaternalMedicalFiles.maternal_id == maternal_id,
            MaternalMedicalFiles.file_name == file_name
        ).all()

    def get_medical_file_by_id(
        self,
        maternal_id: int,
        file_id: int,
    ) -> Optional[MaternalMedicalFiles]:
        """
        通过file_id和maternal_id查询单个医疗文件
        """
        return self.db_session.query(MaternalMedicalFiles).filter(
            MaternalMedicalFiles.maternal_id == maternal_id,
            MaternalMedicalFiles.id == file_id
        ).all()

    def update_medical_file(
        self,
        file_id: int,
        file_name: Optional[str] = None,
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None,
        upload_time: Optional[datetime] = None,
        file_desc: Optional[str] = None,
        check_date: Optional[date] = None
    ) -> Optional[MaternalMedicalFiles]:
        """更新医疗文件记录"""
        file = self.get_medical_files(file_id)
        if not file:
            return None
        
        if file_name is not None:
            file.file_name = file_name
        if file_path is not None:
            file.file_path = file_path
        if file_type is not None:
            file.file_type = file_type
        if file_size is not None:
            file.file_size = file_size
        if upload_time is not None:
            file.upload_time = upload_time
        if file_desc is not None:
            file.file_desc = file_desc
        if check_date is not None:
            file.check_date = check_date
        
        try:
            self.db_session.commit()
            self.db_session.refresh(file)
            return file
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e

    # ------------------------------
    # 对话记录服务
    # ------------------------------
    def create_dialogue(
        self, 
        maternal_id: int,
        dialogue_content: str,
        chat_id: Optional[str] = None,
        vector_store_path: Optional[str] = None
    ) -> MaternalDialogue:
        dialogue = MaternalDialogue(
            maternal_id=maternal_id,
            chat_id=chat_id,
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

    def get_maternal_info_by_id(self, maternal_id: int):
        """通过maternal_id获取孕妇信息"""
        return self.db_session.query(MaternalInfo).filter(
            MaternalInfo.id == maternal_id
        ).first()

    def get_dialogues(self, maternal_id: int, chat_id: str) -> List[MaternalDialogue]:
        """获取指定孕妇的所有对话记录"""
        try:
            dialogues = self.db_session.query(MaternalDialogue).filter(
                MaternalDialogue.maternal_id == maternal_id,
                MaternalDialogue.chat_id == chat_id
            ).all()
            return dialogues
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e

    def create_chat_record(
        self, 
        maternal_id: int,
        chat_id: str,
        json_file_path: str
    ) -> MaternalDialogue:
        """创建对话记录"""
        maternal_info = self.get_maternal_info_by_id(maternal_id)
        if not maternal_info:
            raise ValueError("孕妇不存在")
        
        dialogue = self.create_dialogue(
            maternal_id=maternal_id,
            chat_id=chat_id,
            dialogue_content=json_file_path,
            created_at = datetime.now()
        )
        try:
            self.db_session.add(dialogue)
            self.db_session.commit()
            self.db_session.refresh(dialogue)
            return dialogue
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise Exception(f"存储chat记录到数据库失败: {str(e)}")

    def update_dialogue(
        self,
        maternal_id: int,
        chat_id: str,
        dialogue_content: Optional[str] = None,
    ) -> Optional[MaternalDialogue]:
        """更新对话记录"""
        dialogue = self.get_dialogues(maternal_id)
        if not dialogue:
            return None
        
        if dialogue_content is not None:
            dialogue.dialogue_content = dialogue_content
        if vector_store_path is not None:
            dialogue.vector_store_path = vector_store_path
        
        try:
            self.db_session.commit()
            self.db_session.refresh(dialogue)
            return dialogue
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e
