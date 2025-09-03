# Flask到FastAPI迁移指南

## 概述

本项目已成功从Flask迁移到FastAPI，提供了更好的性能、自动文档生成和现代化的API开发体验。

## 迁移内容

### 1. 架构变更

#### 原始Flask架构
```
backend/api/v1/
├── app.py              # Flask应用入口
├── routes/
│   ├── auth_routes.py  # 认证路由
│   ├── chat_routes.py  # 聊天路由
│   └── maternal_routes.py # 孕妇信息路由
└── common/
    └── auth.py         # 认证工具

web/
└── app.py              # Web界面应用
```

#### 新的FastAPI架构
```
backend/fastapi_app/
├── main.py             # API服务入口
├── web_app.py          # Web服务入口
├── complete_app.py     # 完整应用入口
├── config.py           # 配置管理
├── auth.py             # 认证系统
├── models/             # Pydantic数据模型
│   ├── auth.py
│   ├── chat.py
│   ├── maternal.py
│   └── __init__.py
└── routers/            # 路由模块
    ├── auth.py
    ├── chat.py
    ├── maternal.py
    └── __init__.py
```

### 2. 核心变更

| 组件 | Flask | FastAPI |
|------|-------|---------|
| 路由 | Blueprint | APIRouter |
| 请求处理 | request对象 | 依赖注入 |
| 数据验证 | 手动验证 | Pydantic自动验证 |
| 认证 | 装饰器 | 依赖系统 |
| 文档 | 手动编写 | 自动生成 |
| 异步支持 | 有限 | 原生支持 |

### 3. 功能对比

#### 认证系统
- **Flask**: 使用装饰器 `@require_auth`
- **FastAPI**: 使用依赖注入 `Depends(get_current_user)`

#### 文件上传
- **Flask**: `request.files.get('file')`
- **FastAPI**: `file: UploadFile = File(...)`

#### 错误处理
- **Flask**: 手动返回JSON错误
- **FastAPI**: 异常处理器自动处理

## 使用方法

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

#### 使用启动脚本（推荐）
```bash
# 启动完整服务（API + Web界面）
./start_fastapi.sh complete

# 仅启动API服务
./start_fastapi.sh api

# 仅启动Web界面服务
./start_fastapi.sh web
```

#### 手动启动
```bash
# 完整服务
cd backend/fastapi_app
uvicorn complete_app:app --host 0.0.0.0 --port 8801 --reload

# API服务
uvicorn main:app --host 0.0.0.0 --port 8801 --reload

# Web服务
uvicorn web_app:app --host 0.0.0.0 --port 8801 --reload
```

### 3. 访问服务

- **Web界面**: http://localhost:8801/
- **API文档**: http://localhost:8801/docs
- **健康检查**: http://localhost:8801/health
- **系统信息**: http://localhost:8801/info

## API端点对比

### 认证接口

| 功能 | Flask端点 | FastAPI端点 | 说明 |
|------|-----------|-------------|-----|
| 用户注册 | POST /api/v1/auth/register | POST /api/v1/auth/register | 保持不变 |
| 用户登录 | POST /api/v1/auth/login | POST /api/v1/auth/login | 保持不变 |
| 用户注销 | POST /api/v1/auth/logout | POST /api/v1/auth/logout | 保持不变 |
| 认证验证 | GET /api/v1/auth/verify | GET /api/v1/auth/verify | 保持不变 |
| 用户信息 | - | GET /api/v1/auth/me | 新增 |

### 聊天接口

| 功能 | Flask端点 | FastAPI端点 | 说明 |
|------|-----------|-------------|-----|
| 创建会话 | POST /api/v1/chat/new_session | POST /api/v1/chat/new_session | 保持不变 |
| 医疗问答 | POST /api/v1/chat/qa | POST /api/v1/chat/qa | 优化文件上传 |
| 会话历史 | GET /api/v1/chat/session/{id}/history | GET /api/v1/chat/session/{id}/history | 保持不变 |
| 删除会话 | - | DELETE /api/v1/chat/session/{id} | 新增 |
| 会话列表 | - | GET /api/v1/chat/sessions | 新增 |

### 孕妇信息接口

所有孕妇信息相关的接口保持与Flask版本相同的路径和功能，但增加了：
- 更好的数据验证
- 自动文档生成
- 改进的错误处理

## 配置管理

### Flask配置（原）
```python
# 硬编码配置
JWT_SECRET = 'ad09ba2a7ede8fedb9fcf5a6b482c5e4'
```

### FastAPI配置（新）
```python
# 使用Pydantic Settings
class Settings(BaseSettings):
    jwt_secret: str = os.getenv("JWT_SECRET", "默认值")
    
    class Config:
        env_file = ".env"
```

## 性能提升

1. **异步支持**: FastAPI原生支持异步操作
2. **自动验证**: Pydantic自动验证请求数据
3. **更好的错误处理**: 统一的异常处理机制
4. **自动文档**: OpenAPI/Swagger自动生成

## 兼容性

- 所有原有的API端点保持兼容
- 请求和响应格式基本不变
- 认证机制保持相同（JWT）
- 数据库操作保持不变

## 开发优势

1. **自动文档**: 访问 `/docs` 查看交互式API文档
2. **类型安全**: Pydantic模型提供类型检查
3. **现代语法**: 支持Python类型提示
4. **更好的IDE支持**: 更好的代码提示和检查
5. **性能监控**: 内置性能分析工具

## 故障排除

### 常见问题

1. **导入错误**: 确保PYTHONPATH包含项目根目录
2. **端口占用**: 检查8801端口是否被占用
3. **依赖缺失**: 运行 `pip install -r requirements.txt`
4. **模板找不到**: 确保在项目根目录启动应用

### 日志查看

FastAPI提供详细的启动日志和错误信息，便于调试和监控。

## 后续计划

1. **性能优化**: 添加缓存和数据库连接池
2. **监控集成**: 添加APM和指标收集
3. **容器化**: 创建Docker镜像
4. **测试覆盖**: 增加自动化测试

## 总结

FastAPI迁移为项目带来了：
- 更好的性能和可扩展性
- 现代化的开发体验
- 自动生成的API文档
- 更强的类型安全
- 更好的错误处理

原有的Flask应用保持在原位置，可以根据需要进行对比和回退。