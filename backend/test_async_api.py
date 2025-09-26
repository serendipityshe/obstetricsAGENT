#!/usr/bin/env python3
"""
测试异步API的功能
测试新的/qa/async接口和任务状态查询接口
"""

import requests
import time
import json
from datetime import datetime

# API基础URL（需要根据实际情况调整）
BASE_URL = "http://localhost:8000/api/v2/chat"

def test_async_workflow_api():
    """测试异步工作流API"""
    print("=" * 50)
    print("测试异步工作流API")
    print("=" * 50)

    # 1. 准备测试数据
    test_request = {
        "input": "孕妇最近出现头晕症状，需要什么建议？",
        "maternal_id": 123,
        "chat_id": "test_chat_001",
        "user_type": "pregnant_mother",
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "file_id": []
    }

    print(f"1. 发送异步请求...")
    print(f"请求数据: {json.dumps(test_request, ensure_ascii=False, indent=2)}")

    try:
        # 2. 发送异步请求
        response = requests.post(
            f"{BASE_URL}/qa/async",
            json=test_request,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")

        if response.status_code == 200:
            result = response.json()
            task_id = result.get("data", {}).get("task_id")

            if task_id:
                print(f"\n2. 获得任务ID: {task_id}")
                print(f"状态查询URL: {result.get('data', {}).get('status_url')}")

                # 3. 轮询任务状态
                print(f"\n3. 开始轮询任务状态...")
                max_attempts = 30  # 最多轮询30次
                for attempt in range(max_attempts):
                    time.sleep(2)  # 每2秒查询一次

                    status_response = requests.get(
                        f"{BASE_URL}/qa/task/{task_id}/status",
                        timeout=10
                    )

                    if status_response.status_code == 200:
                        status_result = status_response.json()
                        task_data = status_result.get("data", {})
                        status = task_data.get("status")
                        progress = task_data.get("progress", 0)

                        print(f"第{attempt+1}次查询 - 状态: {status}, 进度: {progress}%")

                        if status == "completed":
                            print(f"\n✅ 任务完成!")
                            print(f"任务结果: {json.dumps(task_data.get('result'), ensure_ascii=False, indent=2)}")
                            break
                        elif status == "failed":
                            print(f"\n❌ 任务失败!")
                            print(f"错误信息: {task_data.get('error')}")
                            break
                    else:
                        print(f"查询状态失败: {status_response.status_code} - {status_response.text}")

                else:
                    print(f"\n⏰ 任务超时（轮询{max_attempts}次后仍未完成）")

            else:
                print("❌ 未获得有效的任务ID")
        else:
            print(f"❌ 异步请求失败: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")

def test_sync_workflow_api():
    """测试同步工作流API（对比用）"""
    print("\n" + "=" * 50)
    print("测试同步工作流API（对比用）")
    print("=" * 50)

    test_request = {
        "input": "孕妇最近出现头晕症状，需要什么建议？",
        "maternal_id": 123,
        "chat_id": "test_chat_002",
        "user_type": "pregnant_mother",
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "file_id": []
    }

    print(f"发送同步请求（可能需要较长时间）...")

    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/qa",
            json=test_request,
            headers={"Content-Type": "application/json"},
            timeout=120  # 2分钟超时
        )
        end_time = time.time()

        print(f"响应时间: {end_time - start_time:.2f}秒")
        print(f"响应状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 同步请求成功")
            print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print(f"❌ 同步请求失败: {response.status_code} - {response.text}")

    except requests.exceptions.Timeout:
        print("❌ 同步请求超时")
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    print("异步工作流API测试脚本")
    print(f"测试时间: {datetime.now()}")
    print(f"API基础URL: {BASE_URL}")

    # 提示用户
    print("\n⚠️  注意: 请确保API服务已启动")
    print("如果API地址不是 http://localhost:8000，请修改脚本中的BASE_URL")

    input("\n按回车键开始测试...")

    # 测试异步API
    test_async_workflow_api()

    # 测试同步API（可选）
    test_sync = input("\n是否测试同步API？(y/N): ").lower().strip()
    if test_sync == 'y':
        test_sync_workflow_api()

    print("\n✅ 测试完成")