import requests
import socket
from urllib.parse import urljoin

def is_port_open(domain, port):
    """检查域名对应的端口是否开放"""
    try:
        # 解析域名到IP
        ip = socket.gethostbyname(domain)
        print(f"解析域名 {domain} 到IP: {ip}")
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            result = s.connect_ex((ip, port))
            return result == 0
    except Exception as e:
        print(f"端口检查失败: {str(e)}")
        return False

def test_api_endpoint(base_url, endpoint, method='post', data=None):
    """测试指定API端点"""
    try:
        url = urljoin(base_url, endpoint)
        if method.lower() == 'post':
            response = requests.post(url, data=data, timeout=10)
        else:
            response = requests.get(url, timeout=10)
        
        return {
            'success': response.status_code in [200, 201],
            'status_code': response.status_code,
            'message': f"状态码: {response.status_code}"
        }
    except Exception as e:
        return {
            'success': False,
            'status_code': None,
            'message': f"接口调用出错: {str(e)}"
        }

def main():
    # 配置目标地址（根据实际情况修改）
    public_domain = "js1.blockelite.cn"
    public_port = 26159
    
    print("开始API端口验证...")
    print(f"目标地址: {public_domain}:{public_port}")
    
    # 1. 检查端口是否开放
    if not is_port_open(public_domain, public_port):
        print(f"端口 {public_port} 未开放，无法访问API")
        return
    
    # 2. 构建基础URL
    base_url = f"http://{public_domain}:{public_port}"
    print(f"API基础URL: {base_url}")
    
    # 3. 定义需要测试的API端点
    api_endpoints = [
        {'endpoint': '/api/v1/chat/new_session', 'method': 'post'},  # 新增会话接口
        {'endpoint': '/api/v1/chat/qa', 'method': 'post', 'data': {'query': '羊水过多怎么办', 'user_type': 'pregnant_mother'}}  # 问答接口
    ]
    
    # 4. 依次测试API端点
    all_success = True
    for api in api_endpoints:
        print(f"\n测试API: {api['endpoint']} ({api['method'].upper()})")
        result = test_api_endpoint(
            base_url,
            api['endpoint'],
            api['method'],
            api.get('data')
        )
        
        status = "成功" if result['success'] else "失败"
        print(f"测试结果: {status} - {result['message']}")
        if not result['success']:
            all_success = False
    
    # 5. 输出总结
    print("\n===== 测试总结 =====")
    if all_success:
        print("所有API端点均可正常访问")
    else:
        print("部分API端点访问异常，请检查服务配置")

if __name__ == "__main__":
    main()