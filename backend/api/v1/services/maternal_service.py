"""数据库操作封装"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from backend.dataset.db.service import MaternalService as DatasetMaternalService
from backend.dataset.db.models import (
    MaternalInfo,
    MaternalPregnancyHistory,
    MaternalHealthCondition,
    MaternalMedicalFiles
)

class MaternalService:
    def __init__(self):
        self.dataset_service = DatasetMaternalService()

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
        info_id: int,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """更新孕妇信息"""
        try:
            result = self.dataset_service.update_maternal_info(
                info_id=info_id,** kwargs
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

    def add_pregnancy_history(
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

    def add_health_condition(
        self,
        maternal_id: int,**kwargs
    ) -> Dict[str, Any]:
        """添加健康状况记录"""
        try:
            result = self.dataset_service.create_health_condition(
                maternal_id=maternal_id,** kwargs
            )
            return self._health_condition_to_dict(result)
        except Exception as e:
            raise Exception(f"添加健康状况失败: {str(e)}")

    def add_medical_file(
        self,
        maternal_id: int,
        file_name: str,
        file_path: str,
        file_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """添加医疗文件记录"""
        try:
            result = self.dataset_service.create_medical_file(
                maternal_id=maternal_id,
                file_name=file_name,
                file_path=file_path,
                file_type=file_type,** kwargs
            )
            return self._medical_file_to_dict(result)
        except Exception as e:
            raise Exception(f"添加医疗文件失败: {str(e)}")

    # 数据模型转字典的工具方法
    @staticmethod
    def _maternal_info_to_dict(info: MaternalInfo) -> Dict[str, Any]:
        return {
            "id": info.id,
            "id_card": info.id_card,
            "phone": info.phone,
            "current_gestational_week": info.current_gestational_week,
            "expected_delivery_date": info.expected_delivery_date.isoformat() if info.expected_delivery_date else None,
            "maternal_age": info.maternal_age,
            "created_at": info.created_at.isoformat() if info.created_at else None,
            "updated_at": info.updated_at.isoformat() if info.updated_at else None
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
            "check_date": file.check_date.isoformat() if file.check_date else None
        }