from dotenv import load_dotenv
import json
from langchain_openai import ChatOpenAI
from utils.langchain_tools import weather_query, web_search
from langchain.agents import create_agent
from langchain_core.messages import AIMessage
import os
load_dotenv()
llm = ChatOpenAI(
    base_url="https://open.bigmodel.cn/api/paas/v4",
    api_key=os.getenv("GLM_API_KEY"),
    model="glm-5.1",
)
# llm = ChatOpenAI(
#     base_url="https://api.deepseek.com",
#     api_key=os.getenv("DEEPSEEK_API_KEY"),
#     model="deepseek-v4-flash",
# )
def get_final_ai_message(messages):
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content
    return None



async def chat_stream(messages):
    agent = create_agent(llm, tools=[weather_query, web_search])
    with open("utils/optimizer_system_prompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    full_messages = [
        {"role": "system", "content": system_prompt},
        *messages
    ]

    async for event in agent.astream_events(
        {"messages": full_messages}
    ):
        # 2️⃣ content
        if event["event"] == "on_chat_model_stream":
            yield {
                "content": event["data"]["chunk"].content
            }

        # 3️⃣ 返回正在使用的工具名称
        elif event["event"] == "on_tool_start":
            tool_call = event["data"].get("input")
            tool_name = event["name"]
            param = tool_call.get("city") or tool_call.get("query")
            yield {
                "type": "tool_start",
                "tool": tool_name,
                "args": param
            }
        elif event["event"] == "on_tool_end":
            tool_name = event.get("name")
            tool_message = event["data"].get("output")
            raw_content = getattr(tool_message, "content", "")
            tool_content = raw_content
            if isinstance(raw_content, str):
                try:
                    parsed_content = json.loads(raw_content)
                    if tool_name == "weather_query":
                        tool_content = parsed_content.get("full_data", parsed_content)
                    else:
                        tool_content = parsed_content
                except json.JSONDecodeError:
                    tool_content = raw_content
            yield {
                "type": "tool_mid",
                "tool": tool_name,
                "tool_content": tool_content
            }
        

# 创建标题
async def generate_chat_title(messages):
    title_agent = create_agent(llm, tools=[])
    messages=[
        {
            "role": "system",
            "content":"请用不超过20个字概括下面这句话的核心主题，作为聊天标题,其余一律不要生成"
        },
        {
            "role": "user",
            "content":messages
        }
    ]
    client =await title_agent.ainvoke(
        {"messages": messages}
    )
    final = get_final_ai_message(client["messages"])
    return final
