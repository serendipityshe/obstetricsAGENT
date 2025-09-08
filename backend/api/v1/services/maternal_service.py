"""数据库操作封装"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from backend.dataset.db.service import MaternalService as DatasetMaternalService
from backend.dataset.db.models import (
    User,
    MaternalInfo,
    MaternalPregnancyHistory,
    MaternalHealthCondition,
    MaternalMedicalFiles,
    MaternalDialogue
)


class MaternalService:
    def __init__(self):
        self.dataset_service = DatasetMaternalService()

    # ------------------------------
    # 用户信息相关服务
    # ------------------------------
    def create_user_info(self, username: str, password: str, user_type: str) -> Dict[str, Any]:
        """创建用户信息"""
        try:
            result = self.dataset_service.create_user_info(
                username=username,
                password=password,
                user_type=user_type
            )

            return self._user_to_dict(result)
        except Exception as e:
            raise Exception(f"创建用户信息失败: {str(e)}")

    def get_user_info_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户信息"""
        try:
            result = self.dataset_service.get_user_info_by_username(username)
            return self._user_to_dict(result) if result else None
        except Exception as e:
            raise Exception(f"获取用户信息失败: {str(e)}")

    # ------------------------------
    # 孕妇基本信息相关服务
    # ------------------------------
    def create_maternal_info(
        self,
        id_card: str,
        phone: Optional[str] = None,
        current_gestational_week: Optional[int] = None,
        expected_delivery_date: Optional[date] = None,
        maternal_age: Optional[int] = None
    ) -> Dict[str, Any]:
        """创建孕妇基本信息"""
        try:
            result = self.dataset_service.create_maternal_info(
                id_card=id_card,
                phone=phone,
                current_gestational_week=current_gestational_week,
                expected_delivery_date=expected_delivery_date,
                maternal_age=maternal_age
            )
            return self._maternal_info_to_dict(result)
        except Exception as e:
            raise Exception(f"创建孕妇信息失败: {str(e)}")

    def get_maternal_info_by_id(self, info_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取孕妇信息"""
        try:
            result = self.dataset_service.get_maternal_info_by_id(info_id)
            return self._maternal_info_to_dict(result) if result else None
        except Exception as e:
            raise Exception(f"获取孕妇信息失败: {str(e)}")

    def get_maternal_info_by_id_card(self, id_card: str) -> Optional[Dict[str, Any]]:
        """根据身份证号获取孕妇信息"""
        try:
            result = self.dataset_service.get_maternal_info_by_id_card(id_card)
            return self._maternal_info_to_dict(result) if result else None
        except Exception as e:
            raise Exception(f"获取孕妇信息失败: {str(e)}")

    def get_all_maternal_infos(self) -> List[Dict[str, Any]]:
        """获取所有孕妇信息"""
        try:
            results = self.dataset_service.get_all_maternal_infos()
            return [self._maternal_info_to_dict(info) for info in results]
        except Exception as e:
            raise Exception(f"获取所有孕妇信息失败: {str(e)}")

    def update_maternal_info(
        self,
        user_id: int,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """更新孕妇信息"""
        try:
            result = self.dataset_service.update_maternal_info(
                user_id=user_id,** kwargs
            )
            return self._maternal_info_to_dict(result) if result else None
        except Exception as e:
            raise Exception(f"更新孕妇信息失败: {str(e)}")

    def delete_maternal_info(self, info_id: int) -> bool:
        """删除孕妇信息"""
        try:
            return self.dataset_service.delete_maternal_info(info_id)
        except Exception as e:
            raise Exception(f"删除孕妇信息失败: {str(e)}")

    # ------------------------------
    # 孕产史相关服务
    # ------------------------------
    def create_pregnancy_history(
        self,
        maternal_id: int,
        pregnancy_count: Optional[int] = None,
        bad_pregnancy_history: Optional[str] = None,
        delivery_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """添加孕产史记录"""
        try:
            result = self.dataset_service.create_pregnancy_history(
                maternal_id=maternal_id,
                pregnancy_count=pregnancy_count,
                bad_pregnancy_history=bad_pregnancy_history,
                delivery_method=delivery_method
            )
            return self._pregnancy_history_to_dict(result)
        except Exception as e:
            raise Exception(f"添加孕产史失败: {str(e)}")

    def get_pregnancy_histories(self, maternal_id: int) -> List[Dict[str, Any]]:
        """获取指定孕妇的孕产史"""
        try:
            results = self.dataset_service.get_pregnancy_histories(maternal_id)
            return [self._pregnancy_history_to_dict(history) for history in results]
        except Exception as e:
            raise Exception(f"获取孕产史失败: {str(e)}")

    def update_pregnancy_history(
        self,
        maternal_id: int,
        history_id: int,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """更新孕产史记录"""
        try:
            result = self.dataset_service.update_pregnancy_history(
                maternal_id=maternal_id,
                history_id=history_id,
                **kwargs
            )
            return self._pregnancy_history_to_dict(result) if result else None
        except Exception as e:
            raise Exception(f"更新孕产史失败: {str(e)}")

    # ------------------------------
    # 健康状况相关服务
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
    ) -> Dict[str, Any]:
        """添加健康状况记录"""
        try:
            result = self.dataset_service.create_health_condition(
                maternal_id=maternal_id,
                has_hypertension=has_hypertension,
                has_diabetes=has_diabetes,
                has_thyroid_disease=has_thyroid_disease,
                has_heart_disease=has_heart_disease,
                has_liver_disease=has_liver_disease,
                allergy_history=allergy_history
            )
            return self._health_condition_to_dict(result)
        except Exception as e:
            raise Exception(f"添加健康状况失败: {str(e)}")

    def get_health_conditions(self, maternal_id: int) -> List[Dict[str, Any]]:
        """获取指定孕妇的健康状况"""
        try:
            results = self.dataset_service.get_health_conditions(maternal_id)
            return [self._health_condition_to_dict(condition) for condition in results]
        except Exception as e:
            raise Exception(f"获取健康状况失败: {str(e)}")

    def update_health_condition(
        self,
        maternal_id: int,
        condition_id: int,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """更新健康状况记录"""
        try:
            result = self.dataset_service.update_health_condition(
                maternal_id=maternal_id,
                condition_id=condition_id,
                **kwargs
            )
            return self._health_condition_to_dict(result) if result else None
        except Exception as e:
            raise Exception(f"更新健康状况失败: {str(e)}")

    # ------------------------------
    # 医疗文件相关服务
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
    ) -> Dict[str, Any]:
        """添加医疗文件记录"""
        try:
            result = self.dataset_service.create_medical_file(
                maternal_id=maternal_id,
                file_name=file_name,
                file_path=file_path,
                file_type=file_type,
                file_size=file_size,
                upload_time=upload_time,
                file_desc=file_desc,
                check_date=check_date
            )
            return self._medical_file_to_dict(result)
        except Exception as e:
            raise Exception(f"添加医疗文件失败: {str(e)}")

    def get_medical_files(self, maternal_id: int, file_name: str) -> List[Dict[str, Any]]:
        """获取指定孕妇的医疗文件"""
        try:
            results = self.dataset_service.get_medical_files(maternal_id, file_name)
            return [self._medical_file_to_dict(file) for file in results]
        except Exception as e:
            raise Exception(f"获取医疗文件失败: {str(e)}")

    def get_medical_file_by_id(
        self,
        maternal_id: int,
        file_id: int,
    ) -> Optional[Dict[str, Any]]:
        """获取指定孕妇的医疗文件"""
        try:
            result = self.dataset_service.get_medical_file_by_id(
                maternal_id=maternal_id,
                file_id=file_id,
            )
            return self._medical_file_to_dict(result) if result else None
        except Exception as e:
            raise Exception(f"获取医疗文件失败: {str(e)}")

    def update_medical_file(
        self,
        maternal_id: int,
        file_id: int,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """更新医疗文件记录"""
        try:
            result = self.dataset_service.update_medical_file(
                maternal_id=maternal_id,
                file_id=file_id,
                **kwargs
            )
            return self._medical_file_to_dict(result) if result else None
        except Exception as e:
            raise Exception(f"更新医疗文件失败: {str(e)}")

    # ------------------------------
    # 对话记录相关服务
    # ------------------------------
    def create_dialogue(
        self,
        maternal_id: int,
        dialogue_content: str,
        vector_store_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """添加对话记录"""
        try:
            result = self.dataset_service.create_dialogue(
                maternal_id=maternal_id,
                dialogue_content=dialogue_content,
                vector_store_path=vector_store_path
            )
            return self._dialogue_to_dict(result)
        except Exception as e:
            raise Exception(f"添加对话记录失败: {str(e)}")

    def get_dialogues(self, maternal_id: int, chat_id: str) -> List[Dict[str, Any]]:
        """获取指定孕妇的对话记录"""
        try:
            results = self.dataset_service.get_dialogues(maternal_id, chat_id)
            return [self._dialogue_to_dict(dialogue) for dialogue in results]
        except Exception as e:
            raise Exception(f"获取对话记录失败: {str(e)}")
    
    def update_dialogue(
        self,
        maternal_id: int,
        dialogue_id: int,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """更新对话记录"""
        try:
            result = self.dataset_service.update_dialogue(
                maternal_id=maternal_id,
                dialogue_id=dialogue_id,
                **kwargs
            )
            return self._dialogue_to_dict(result) if result else None
        except Exception as e:
            raise Exception(f"更新对话记录失败: {str(e)}")

    # ------------------------------
    # 数据模型转字典工具方法
    # ------------------------------
    @staticmethod
    def _user_to_dict(user: User) -> Dict[str, Any]:
        return {
            "id": user.id,
            "username": user.username,
            'password_hash': user.password_hash,
            "user_type": user.user_type,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }

    @staticmethod
    def _maternal_info_to_dict(info: MaternalInfo) -> Dict[str, Any]:
        return {
            "id": info.id,
            "user_id": info.user_id,
            "id_card": info.id_card,
            "phone": info.phone,
            "current_gestational_week": info.current_gestational_week,
            "expected_delivery_date": info.expected_delivery_date.isoformat() if info.expected_delivery_date else None,
            "maternal_age": info.maternal_age,
        }

    @staticmethod
    def _pregnancy_history_to_dict(history: MaternalPregnancyHistory) -> Dict[str, Any]:
        return {
            "id": history.id,
            "maternal_id": history.maternal_id,
            "pregnancy_count": history.pregnancy_count,
            "bad_pregnancy_history": history.bad_pregnancy_history,
            "delivery_method": history.delivery_method,
            "created_at": history.created_at.isoformat() if history.created_at else None
        }

    @staticmethod
    def _health_condition_to_dict(condition: MaternalHealthCondition) -> Dict[str, Any]:
        return {
            "id": condition.id,
            "maternal_id": condition.maternal_id,
            "has_hypertension": condition.has_hypertension,
            "has_diabetes": condition.has_diabetes,
            "has_thyroid_disease": condition.has_thyroid_disease,
            "has_heart_disease": condition.has_heart_disease,
            "has_liver_disease": condition.has_liver_disease,
            "allergy_history": condition.allergy_history,
            "created_at": condition.created_at.isoformat() if condition.created_at else None
        }

    @staticmethod
    def _medical_file_to_dict(file: MaternalMedicalFiles) -> Dict[str, Any]:
        return {
            "id": file.id,
            "maternal_id": file.maternal_id,
            "file_name": file.file_name,
            "file_path": file.file_path,
            "file_type": file.file_type,
            "file_size": file.file_size,
            "upload_time": file.upload_time.isoformat() if file.upload_time else None,
            "file_desc": file.file_desc,
            "check_date": file.check_date.isoformat() if file.check_date else None,
        }

    @staticmethod
    def _dialogue_to_dict(dialogue: MaternalDialogue) -> Dict[str, Any]:
        return {
            "id": dialogue.id,
            "maternal_id": dialogue.maternal_id,
            "chat_id": dialogue.chat_id,
            "dialogue_content": dialogue.dialogue_content,
            "vector_store_path": dialogue.vector_store_path,
            "created_at": dialogue.created_at.isoformat() if dialogue.created_at else None
        }