from langchain_core.tools import Tool
from backend.maternal_database.service import MaternalService
from datetime import date
from typing import Optional, List

class MaternalTools:
    """将数据库的连接和查询等相关功能打包成tool"""
    def __init__(self) -> None:
        self.maternal_service = MaternalService()

    def get_maternal_info(self, info_id: int) -> dict:
        """根据ID查询孕妇信息
        
        输入：孕妇信息ID
        输出：查询到的孕妇信息或错误信息
        """
        try:
            maternal_info = self.maternal_service.get_maternal_info_by_id(info_id)
            if not maternal_info:
                return {"error": f"未找到ID为{info_id}的孕妇信息"}
            return {
                "id": maternal_info.id,
                "maternal_name": maternal_info.maternal_name,
                "expected_delivery_date": str(maternal_info.expected_delivery_date) if maternal_info.expected_delivery_date else None,
                "maternal_age": maternal_info.maternal_age,
                "pregnancy_history": maternal_info.pregnancy_history,
                "health_status": maternal_info.health_status,
                "baby_name": maternal_info.baby_name 
            }
        except Exception as e:
            return {"error": f"查询孕妇信息失败:{str(e)}"}

    def get_tool(self) -> Tool:
        """创建并返回查询孕妇信息的Tool实例"""
        return Tool(
            name = "query_maternal_info",
            func = self.get_maternal_info,
            description = "根据ID查询孕妇信息。输入参数为孕妇信息ID，输出为查询到的孕妇信息或错误信息。",
        )
