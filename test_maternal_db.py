"""
孕妇个人数据库测试脚本
"""

from datetime import date
from backend.maternal_database import MaternalService

def test_maternal_database():
    """
    测试孕妇个人数据库功能
    """
    print("开始测试孕妇个人数据库功能...")
    
    # 创建服务实例
    service = MaternalService()
    
    # 创建孕妇信息
    print("创建孕妇信息...")
    maternal_info = service.create_maternal_info(
        maternal_name="张小花",
        expected_delivery_date=date(2024, 12, 25),
        maternal_age=28,
        pregnancy_history="G1P0",
        health_status="健康",
        baby_name="小宝贝"
    )
    print(f"创建的孕妇信息: {maternal_info}")
    
    # 查询孕妇信息
    print("\n查询孕妇信息...")
    info = service.get_maternal_info_by_id(2)
    print(f"查询到的孕妇信息: {info}")
    
    # 更新孕妇信息
    print("\n更新孕妇信息...")
    updated_info = service.update_maternal_info(
        info_id=maternal_info.id,
        maternal_name="张小花花",
        baby_name="小天使"
    )
    print(f"更新后的孕妇信息: {updated_info}")
    
    # 获取所有孕妇信息
    print("\n获取所有孕妇信息...")
    all_infos = service.get_all_maternal_infos()
    print(f"所有孕妇信息数量: {len(all_infos)}")
    for info in all_infos:
        print(f"  - {info}")
    
    # 删除孕妇信息
    print("\n删除孕妇信息...")
    result = service.delete_maternal_info(maternal_info.id)
    print(f"删除结果: {'成功' if result else '失败'}")
    
    print("\n测试完成！")

if __name__ == "__main__":
    test_maternal_database()