# 孕妇个人数据库模块

## 功能说明

该模块用于管理孕妇的个人数据库信息，包括预产期、准妈妈年龄、孕产史、基础健康状况、宝宝名称等内容。

## 数据库表结构

### maternal_info 表

| 字段名 | 类型 | 允许空值 | 说明 |
|--------|------|----------|------|
| id | Integer | 否 | 主键ID，自增 |
| expected_delivery_date | Date | 是 | 预产期 |
| maternal_age | Integer | 是 | 准妈妈年龄 |
| pregnancy_history | Text | 是 | 孕产史 |
| health_status | Text | 是 | 基础健康状况 |
| baby_name | String(100) | 是 | 宝宝名称 |

## 环境配置

1. 安装MySQL数据库
2. 创建数据库：`CREATE DATABASE maternal_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
3. 在项目根目录的.env文件中配置数据库连接信息：

```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=maternal_db
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

```python
from backend.maternal_database import MaternalService

# 创建服务实例
service = MaternalService()

# 创建孕妇信息
maternal_info = service.create_maternal_info(
    expected_delivery_date=date(2024, 12, 25),
    maternal_age=28,
    pregnancy_history="G1P0",
    health_status="健康",
    baby_name="小宝贝"
)

# 查询孕妇信息
info = service.get_maternal_info_by_id(maternal_info.id)
print(info)

# 更新孕妇信息
updated_info = service.update_maternal_info(
    info_id=maternal_info.id,
    baby_name="小天使"
)

# 获取所有孕妇信息
all_infos = service.get_all_maternal_infos()

# 删除孕妇信息
service.delete_maternal_info(maternal_info.id)
```