# 异步工作流API使用指南

## 概述

为了解决AI推理时间长导致的阻塞问题，我们新增了异步工作流处理机制。现在支持多个用户同时发起AI对话请求而不相互阻塞。

## 新增的API接口

### 1. 异步工作流调用接口

**接口地址**: `POST /api/v2/chat/qa/async`

**功能**: 立即返回任务ID，AI处理在后台进行

**请求示例**:
```json
{
  "input": "孕妇最近出现头晕症状，需要什么建议？",
  "maternal_id": 123,
  "chat_id": "chat_123_pregnant_mother_uuid",
  "user_type": "pregnant_mother",
  "timestamp": "2025-09-22T10:30:00.000Z",
  "file_id": []
}
```

**响应示例**:
```json
{
  "code": 200,
  "msg": "任务已创建，请使用task_id查询状态",
  "data": {
    "task_id": "task_uuid-1234",
    "status": "pending",
    "created_at": "2025-09-22T10:30:01.000Z",
    "status_url": "/api/v2/chat/qa/task/task_uuid-1234/status"
  }
}
```

### 2. 任务状态查询接口

**接口地址**: `GET /api/v2/chat/qa/task/{task_id}/status`

**功能**: 查询异步任务的执行状态和结果

**任务状态说明**:
- `pending`: 任务排队中，等待执行
- `running`: 任务正在执行中
- `completed`: 任务完成，可获取完整结果
- `failed`: 任务执行失败，查看错误信息

**响应示例**:

任务进行中:
```json
{
  "code": 200,
  "msg": "获取任务状态成功",
  "data": {
    "task_id": "task_uuid-1234",
    "status": "running",
    "created_at": "2025-09-22T10:30:01.000Z",
    "started_at": "2025-09-22T10:30:05.000Z",
    "progress": 50
  }
}
```

任务完成:
```json
{
  "code": 200,
  "msg": "获取任务状态成功",
  "data": {
    "task_id": "task_uuid-1234",
    "status": "completed",
    "created_at": "2025-09-22T10:30:01.000Z",
    "started_at": "2025-09-22T10:30:05.000Z",
    "completed_at": "2025-09-22T10:31:45.000Z",
    "progress": 100,
    "result": {
      "code": 200,
      "msg": "success",
      "data": {
        "chat_meta": {...},
        "session_title": "孕妇最近出现头晕...",
        "messages": [...],
        "error": null
      }
    }
  }
}
```

## 客户端使用流程

### 1. 基本轮询模式

```javascript
// 1. 发起异步请求
const response = await fetch('/api/v2/chat/qa/async', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    input: "孕妇最近出现头晕症状，需要什么建议？",
    maternal_id: 123,
    chat_id: "chat_123_pregnant_mother_uuid",
    user_type: "pregnant_mother",
    file_id: []
  })
});

const taskInfo = await response.json();
const taskId = taskInfo.data.task_id;

// 2. 轮询任务状态
async function pollTaskStatus(taskId) {
  while (true) {
    const statusResponse = await fetch(`/api/v2/chat/qa/task/${taskId}/status`);
    const statusData = await statusResponse.json();

    const status = statusData.data.status;
    console.log(`任务状态: ${status}, 进度: ${statusData.data.progress}%`);

    if (status === 'completed') {
      console.log('任务完成!', statusData.data.result);
      return statusData.data.result;
    } else if (status === 'failed') {
      console.error('任务失败:', statusData.data.error);
      throw new Error(statusData.data.error);
    }

    // 等待2秒后继续查询
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}

// 获取最终结果
const result = await pollTaskStatus(taskId);
```

### 2. 带超时的轮询

```javascript
async function pollTaskStatusWithTimeout(taskId, timeoutMs = 300000) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeoutMs) {
    const statusResponse = await fetch(`/api/v2/chat/qa/task/${taskId}/status`);
    const statusData = await statusResponse.json();

    const status = statusData.data.status;

    if (status === 'completed') {
      return statusData.data.result;
    } else if (status === 'failed') {
      throw new Error(statusData.data.error);
    }

    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  throw new Error('任务超时');
}
```

## 原有同步接口

原有的同步接口 `POST /api/v2/chat/qa` 仍然保留，用于向后兼容。但建议使用异步接口以获得更好的用户体验。

## 配置参数

在 `async_task_manager.py` 中可以调整以下参数：

- `max_workers`: 最大并发任务数（默认5）
- `cleanup_interval`: 清理过期任务的间隔时间（默认3600秒）
- `max_age_hours`: 已完成任务的保留时间（默认24小时）

## 性能优势

1. **非阻塞**: 多个用户可以同时发起请求，不会互相阻塞
2. **可扩展**: 通过调整 `max_workers` 可以控制并发处理能力
3. **资源优化**: 自动清理过期任务，避免内存泄漏
4. **用户体验**: 客户端可以显示进度，提供更好的交互体验

## 注意事项

1. 任务结果会在完成后保留24小时，超时会被自动清理
2. 建议客户端实现合理的轮询间隔（建议2-5秒）
3. 对于超长时间的任务，建议设置适当的超时时间
4. 系统重启后，所有进行中的任务会丢失，客户端需要处理这种情况

## 测试脚本

使用提供的测试脚本验证API功能：

```bash
python test_async_api.py
```

该脚本会测试异步API的完整流程，包括任务创建、状态查询和结果获取。