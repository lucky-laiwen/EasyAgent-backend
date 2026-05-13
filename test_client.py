import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://token-plan-sgp.xiaomimimo.com/v1",
    model="mimo-v2.5-pro"
)
completion = llm.invoke(
    [
        {
            "role": "system",
            "content": "You are MiMo, an AI assistant developed by Xiaomi. Today is date: Tuesday, December 16, 2025. Your knowledge cutoff date is December 2024."
        },
        {
            "role": "user",
            "content": "介绍一下你自己"
        }
    ]
)

print(completion.content)