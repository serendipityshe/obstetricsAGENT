#!/usr/bin/env python3
"""
测试流式响应是否真正实时
用于验证修复后的流式输出效果
"""

import asyncio
import aiohttp
import time
import json

async def test_stream_response():
    """测试流式响应实时性"""
    url = "http://localhost:5000/api/v2/chat/qa"

    # 测试数据
    test_data = {
        "input": "请简单介绍一下孕期营养",
        "maternal_id": 1,
        "chat_id": "test_chat_stream_001",
        "user_type": "pregnant_mother",
        "timestamp": "2025-09-29T10:00:00.000Z"
    }

    print(f"🚀 开始测试流式响应 - {time.strftime('%H:%M:%S')}")
    print(f"📤 请求数据: {test_data['input']}")
    print("-" * 50)

    start_time = time.time()
    chunk_count = 0
    first_chunk_time = None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=test_data) as response:
                print(f"📡 响应状态: {response.status}")
                print(f"📋 响应头: {dict(response.headers)}")
                print("-" * 50)

                async for chunk in response.content.iter_chunked(1024):
                    if chunk:
                        chunk_count += 1
                        current_time = time.time()

                        if first_chunk_time is None:
                            first_chunk_time = current_time
                            print(f"⚡ 首次响应时间: {first_chunk_time - start_time:.3f}s")

                        elapsed = current_time - start_time
                        chunk_text = chunk.decode('utf-8', errors='ignore')

                        # 解析JSON行
                        for line in chunk_text.strip().split('\n'):
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    msg_type = data.get('type', 'unknown')

                                    if msg_type == 'ai_content':
                                        content = data.get('content', '')
                                        chunk_id = data.get('chunk_id', 0)
                                        print(f"🤖 [{elapsed:.2f}s] AI#{chunk_id}: {repr(content)}")
                                    elif msg_type == 'progress':
                                        message = data.get('message', '')
                                        progress = data.get('progress', 0)
                                        print(f"📈 [{elapsed:.2f}s] 进度{progress}%: {message}")
                                    elif msg_type == 'start':
                                        print(f"🚀 [{elapsed:.2f}s] {data.get('message', '开始')}")
                                    elif msg_type == 'complete':
                                        print(f"✅ [{elapsed:.2f}s] 完成")
                                    elif msg_type == 'done':
                                        print(f"🏁 [{elapsed:.2f}s] 结束")
                                        break
                                    elif msg_type == 'error':
                                        print(f"❌ [{elapsed:.2f}s] 错误: {data.get('message', '')}")
                                except json.JSONDecodeError:
                                    print(f"📦 [{elapsed:.2f}s] 原始数据: {repr(line[:100])}")

                        # 检查实时性：如果超过5秒没有新内容，说明可能有缓冲问题
                        if elapsed > 5 and chunk_count < 5:
                            print(f"⚠️  警告: {elapsed:.2f}s后才收到第{chunk_count}个chunk，可能存在缓冲问题")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

    total_time = time.time() - start_time
    print("-" * 50)
    print(f"📊 测试完成:")
    print(f"   总耗时: {total_time:.2f}s")
    print(f"   总chunks: {chunk_count}")
    print(f"   首次响应: {(first_chunk_time - start_time):.3f}s" if first_chunk_time else "无响应")

    # 判断是否真正实时
    if first_chunk_time and (first_chunk_time - start_time) < 1.0:
        print("✅ 流式响应正常：首次响应时间 < 1秒")
        return True
    else:
        print("❌ 流式响应异常：首次响应时间过长，可能存在缓冲问题")
        return False

if __name__ == "__main__":
    asyncio.run(test_stream_response())