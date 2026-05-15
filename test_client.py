import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://token-plan-sgp.xiaomimimo.com/v1",
)

# 测试非流式调用，检查是否有 reasoning_content
resp = client.chat.completions.create(
    model="mimo-v2.5-pro",
    messages=[
        {"role": "system", "content": "You are MiMo, an AI assistant developed by Xiaomi."},
        {"role": "user", "content": "介绍一下你自己"}
    ],
    extra_body={"enable_thinking": True},
)

choice = resp.choices[0]
msg = choice.message

print("=== 回复内容 ===")
print(msg.content)
print()

print("=== reasoning_content ===")
reasoning = getattr(msg, "reasoning_content", None)
print(reasoning if reasoning else "(无此字段)")
print()

print("=== 完整 message 对象属性 ===")
print(dir(msg))
print()

print("=== 原始 response ===")
print(resp.model_dump())
