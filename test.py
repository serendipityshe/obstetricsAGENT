from backend.agents.tools.tools import qwen_tool
import yaml

if __name__ == "__main__":
    with open("backend/config/model_settings.yaml", "r", encoding="utf-8") as f:
        model_settings = yaml.safe_load(f)
        vl_model_config = model_settings.get("DEFAULT_MODEL")
    qwen_result = qwen_tool.invoke({
        "input": "你好",
        "img_path": 'test/OIP.png',  
        "model_name": vl_model_config["llm_model"],
        "api_key": vl_model_config["api_key"],
        "base_url": vl_model_config["base_url"],
        "temperature": vl_model_config["temperature"]
    })
    print(qwen_result)