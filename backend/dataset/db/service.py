"""
孕妇个人数据库服务层
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import date, datetime
from .models import (
    User,
    MaternalInfo,
    MaternalPregnancyHistory,
    MaternalHealthCondition,
    MaternalMedicalFiles,
    MaternalDialogue,
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
    # 用户基本信息服务
    # ------------------------------
    def create_user_info(self, username: str, password: str, user_type: str) -> User:
        """创建用户基本信息（孕妇用户自动创建关联数据）"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            # 1. 创建用户（先提交获取user.id，用于后续关联）
            user = repo.create_user_info(
                username=username,
                password=password,
                user_type=user_type
            )
            # 2. 若为孕妇用户，自动创建关联数据（同一Session内）
            if user_type == 'pregnant_mother':
                # 2.1 创建孕妇基本信息（必须传user_id关联用户）
                maternal_info = repo.create_maternal_info(
                    user_id=user.id,  # 关键：使用已创建用户的ID
                    id_card=None,
                    phone=None,
                    current_gestational_week=None,
                    expected_delivery_date=None,
                    maternal_age=None,
                )
                # 2.2 创建关联的孕产史
                repo.create_pregnancy_history(
                    maternal_id=maternal_info.id,
                    pregnancy_count=None,
                    bad_pregnancy_history=None,
                    delivery_method=None
                )
                # 2.3 创建关联的健康状况
                repo.create_health_condition(
                    maternal_id=maternal_info.id,
                    has_hypertension=False,
                    has_diabetes=False,
                    has_thyroid_disease=False,
                    has_heart_disease=False,
                    has_liver_disease=False,
                    allergy_history=None
                )
                # 2.4 创建关联的初始医疗文件
                repo.create_medical_file(
                    maternal_id=maternal_info.id,
                    file_name=f"init_{maternal_info.id}",  # 默认文件名
                    file_path=f"/default/medical/{maternal_info.id}",  # 默认路径
                    file_type="txt",  # 默认类型
                    file_desc="初始默认文件"  # 描述
                )
                # 2.5 创建关联的对话记录（空JSON）
                repo.create_dialogue(
                    maternal_id=maternal_info.id,
                    dialogue_content="{}",  # 符合JSON格式的空内容
                    vector_store_path=None
                )
            # 3. 统一提交Session（所有操作原子性，要么全成功要么全失败）
            db_session.commit()
            # 4. 刷新用户对象，确保关联数据可通过user.maternal_info访问
            db_session.refresh(user)
            return user
        except Exception as e:
            # 异常时回滚，避免部分数据残留
            db_session.rollback()
            raise Exception(f'创建用户信息失败：{str(e)}')
        finally:
            # 无论成功失败，都关闭Session释放资源
            db_session.close()

    def get_user_info_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户信息（包含关联的孕妇信息）"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.get_user_info_by_username(username)
        finally:
            db_session.close()
    
    # ------------------------------
    # 孕妇基本信息服务（修正：添加user_id参数）
    # ------------------------------
    def create_maternal_info(
        self,
        user_id: int,  # 新增：关联User表的必需参数
        id_card: str = None,
        phone: Optional[str] = None,
        current_gestational_week: Optional[int] = None,
        expected_delivery_date: Optional[date] = None,
        maternal_age: Optional[int] = None
    ) -> MaternalInfo:
        """创建孕妇基本信息（需关联已存在的用户）"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            # 验证用户是否存在（避免无效user_id）
            if not repo.get_user_info_by_id(user_id):
                raise ValueError(f"关联的用户ID {user_id} 不存在")
            # 调用Repository创建（传入user_id）
            maternal_info = repo.create_maternal_info(
                user_id=user_id,
                id_card=id_card,
                phone=phone,
                current_gestational_week=current_gestational_week,
                expected_delivery_date=expected_delivery_date,
                maternal_age=maternal_age
            )
            db_session.commit()
            db_session.refresh(maternal_info)
            return maternal_info
        except Exception as e:
            db_session.rollback()
            raise Exception(f'创建孕妇信息失败：{str(e)}')
        finally:
            db_session.close()
    
    # 以下方法保持不变（仅确保Session管理正确）
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
        user_id: int,
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
            result = repo.update_maternal_info(
                user_id=user_id,
                id_card=id_card,
                phone=phone,
                current_gestational_week=current_gestational_week,
                expected_delivery_date=expected_delivery_date,
                maternal_age=maternal_age
            )
            return result
        except Exception as e:
            db_session.rollback()
            raise Exception(f'更新孕妇信息失败：{str(e)}')
        finally:
            db_session.close()
    
    def delete_maternal_info(self, info_id: int) -> bool:
        """删除孕妇信息（级联删除关联数据）"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            result = repo.delete_maternal_info(info_id)
            db_session.commit()
            return result
        except Exception as e:
            db_session.rollback()
            raise Exception(f'删除孕妇信息失败：{str(e)}')
        finally:
            db_session.close()
    
    # ------------------------------
    # 孕产史服务（补充Session提交逻辑）
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
            result = repo.create_pregnancy_history(
                maternal_id=maternal_id,
                pregnancy_count=pregnancy_count,
                bad_pregnancy_history=bad_pregnancy_history,
                delivery_method=delivery_method
            )
            db_session.commit()
            db_session.refresh(result)
            return result
        except Exception as e:
            db_session.rollback()
            raise Exception(f'添加孕产史失败：{str(e)}')
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

    def update_pregnancy_history(
        self,
        maternal_id: int,
        pregnancy_count: Optional[int] = None,
        bad_pregnancy_history: Optional[str] = None,
        delivery_method: Optional[str] = None
    ) -> Optional[MaternalPregnancyHistory]:
        """更新孕产史记录"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            result = repo.update_pregnancy_history(
                maternal_id=maternal_id,
                pregnancy_count=pregnancy_count,
                bad_pregnancy_history=bad_pregnancy_history,
                delivery_method=delivery_method
            )
            db_session.commit()
            return result
        except Exception as e:
            db_session.rollback()
            raise Exception(f'更新孕产史失败：{str(e)}')
        finally:
            db_session.close()
    
    # ------------------------------
    # 健康状况服务（补充Session提交逻辑）
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
            result = repo.create_health_condition(
                maternal_id=maternal_id,
                has_hypertension=has_hypertension,
                has_diabetes=has_diabetes,
                has_thyroid_disease=has_thyroid_disease,
                has_heart_disease=has_heart_disease,
                has_liver_disease=has_liver_disease,
                allergy_history=allergy_history
            )
            db_session.commit()
            db_session.refresh(result)
            return result
        except Exception as e:
            db_session.rollback()
            raise Exception(f'添加健康状况失败：{str(e)}')
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
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            result = repo.update_health_condition(
                maternal_id=maternal_id,
                has_hypertension=has_hypertension,
                has_diabetes=has_diabetes,
                has_thyroid_disease=has_thyroid_disease,
                has_heart_disease=has_heart_disease,
                has_liver_disease=has_liver_disease,
                allergy_history=allergy_history
            )
            db_session.commit()
            return result
        except Exception as e:
            db_session.rollback()
            raise Exception(f'更新健康状况失败：{str(e)}')
        finally:
            db_session.close()
    
    # ------------------------------
    # 医疗文件服务（补充Session提交逻辑）
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
            result = repo.create_medical_file(
                maternal_id=maternal_id,
                file_name=file_name,
                file_path=file_path,
                file_type=file_type,
                file_size=file_size,
                upload_time=upload_time or datetime.now(),
                file_desc=file_desc,
                check_date=check_date
            )
            db_session.commit()
            db_session.refresh(result)
            return result
        except Exception as e:
            db_session.rollback()
            raise Exception(f'添加医疗文件失败：{str(e)}')
        finally:
            db_session.close()

    def get_medical_files(self, maternal_id: int, file_name: str) -> List[MaternalMedicalFiles]:
        """获取指定孕妇的医疗文件"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.get_medical_files(maternal_id, file_name)
        finally:
            db_session.close()

    def get_medical_file_by_id(
        self,
        maternal_id: int,
        file_id: int,
    ) -> Optional[MaternalMedicalFiles]:
        """
        通过file_id和maternal_id查询单个医疗文件
        """
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.get_medical_file_by_id(
                maternal_id=maternal_id,
                file_id=file_id,
            )
        finally:
            db_session.close()

    def update_medical_file(
        self,
        maternal_id: int,
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
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            result = repo.update_medical_file(
                maternal_id=maternal_id,
                file_id=file_id,
                file_name=file_name,
                file_path=file_path,
                file_type=file_type,
                file_size=file_size,
                upload_time=upload_time,
                file_desc=file_desc,
                check_date=check_date
            )
            db_session.commit()
            return result
        except Exception as e:
            db_session.rollback()
            raise Exception(f'更新医疗文件失败：{str(e)}')
        finally:
            db_session.close()
    
    #---------------------------------
    # 对话记录服务
    #---------------------------------
    def create_dialogue(
        self,
        maternal_id: int,
        user_id: int,
        user_input: str,
        agent_output: str,
        timestamp: Optional[datetime] = None
    ) -> MaternalDialogue:
        """添加对话记录"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            result = repo.create_dialogue(
                maternal_id=maternal_id,
                user_id=user_id,
                user_input=user_input,
                agent_output=agent_output,
                timestamp=timestamp or datetime.now()
            )
            db_session.commit()
            db_session.refresh(result)
            return result
        except Exception as e:
            db_session.rollback()
            raise Exception(f'添加对话记录失败：{str(e)}')
        finally:
            db_session.close()

    def get_dialogues(self, maternal_id: int, chat_id: str) -> List[MaternalDialogue]:
        """获取指定孕妇的对话记录"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            return repo.get_dialogues(maternal_id, chat_id)
        finally:
            db_session.close()

    def update_dialogue(
        self,
        maternal_id: int,
        dialogue_id: int,
        user_input: Optional[str] = None,
        agent_output: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> Optional[MaternalDialogue]:
        """更新对话记录"""
        db_session = self._get_session()
        try:
            repo = MaternalRepository(db_session)
            result = repo.update_dialogue(
                maternal_id=maternal_id,
                dialogue_id=dialogue_id,
                user_input=user_input,
                agent_output=agent_output,
                timestamp=timestamp
            )
            db_session.commit()
            return result
        except Exception as e:
            db_session.rollback()
            raise Exception(f'更新对话记录失败：{str(e)}')
        finally:
            db_session.close()
