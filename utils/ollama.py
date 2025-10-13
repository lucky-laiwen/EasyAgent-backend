from ollama import chat


def chat_with_ollama_stream(messages):
    with open(r"utils\optimizer_system_prompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()
    full_messages = [{
        "role":"system",
        "content": system_prompt
    }] + messages
    response = chat(
        model='deepseek-r1:8b',
        messages=full_messages,
        stream=True,
        think=True,
    )

    for chunk in response:
        yield chunk.get("message", {})

def generate_chat_title(user_message: str) -> str:
    """
    调用 Ollama 模型自动生成聊天标题
    """
    prompt = f"""
        你是一个智能助理，请根据以下用户消息生成一个简洁的聊天标题（不超过15个字）：
        用户消息：
        {user_message}
        要求：
        - 不要包含引号或标点
        - 简洁明了，例如：“Python报错调试” 或 “GPU性能分析”
        返回标题：
        """
    response = chat(
        model="deepseek-r1:8b",
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        think=False
    )
    title = response["message"]["content"].strip()
    return title
