# 导入服务类
from backend.dataset.db.service import MaternalService

# 初始化服务
service = MaternalService()

# 调用删除方法（传入要删除的孕妇ID）
info_id = 20  # 要删除的孕妇信息ID
result = service.delete_maternal_info(info_id)

if result:
    print("删除成功")
else:
    print("删除失败（未找到对应ID的记录）")