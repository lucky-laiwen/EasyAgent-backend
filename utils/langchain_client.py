from dotenv import load_dotenv
import json
from langchain_openai import ChatOpenAI
from utils.langchain_tools import weather_query, web_search
from langgraph.prebuilt import create_react_agent
import os

load_dotenv()

llm = ChatOpenAI(
    api_key=os.getenv("MIMO_API_KEY"),
    base_url="https://token-plan-sgp.xiaomimimo.com/v1",
    model="mimo-v2.5-pro"
)

# llm = ChatOpenAI(                                                                                                
#     base_url="https://open.bigmodel.cn/api/paas/v4",                                                             
#     api_key=os.getenv("GLM_API_KEY"),                                                                            
#     model="glm-5.1",                                                                                             
# )                                                                                                                
 # llm = ChatOpenAI(                                                                                                
 #     base_url="https://api.deepseek.com",                                                                         
 #     api_key=os.getenv("DEEPSEEK_API_KEY"),                                                                       
 #     model="deepseek-v4-flash",                                                                                   
 # )   

with open("utils/optimizer_system_prompt.md", "r", encoding="utf-8") as f:
    system_prompt = f.read()

agent = create_react_agent(llm, tools=[weather_query, web_search], prompt=system_prompt)


async def chat_stream(messages):
    async for event in agent.astream_events({"messages": messages}):
        if event["event"] == "on_chat_model_stream":
            yield {
                "content": event["data"]["chunk"].content
            }
        elif event["event"] == "on_tool_start":
            tool_call = event["data"].get("input")
            tool_name = event["name"]
            tool_run_id = event.get("run_id", "")
            param = tool_call.get("city") or tool_call.get("query")
            yield {
                "type": "tool_start",
                "tool": tool_name,
                "tool_run_id": tool_run_id,
                "args": param
            }
        elif event["event"] == "on_tool_end":
            tool_name = event.get("name")
            tool_run_id = event.get("run_id", "")
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
                "tool_run_id": tool_run_id,
                "tool_content": tool_content
            }


async def generate_chat_title(text: str) -> str:
    resp = await llm.ainvoke([                                                                                     
        {"role": "system", "content":                                                                       
        "你是一个标题生成器。只输出一个简短的标题（不超过20个字），不要输出任何解释、前缀或其他内容。"},            
    {"role": "user", "content": f"为以下对话生成标题：{text}"}                                          
    ])                                                                                                      
    return resp.content.strip()       
