from langchain_core.messages import AIMessage,ToolMessage,HumanMessage,SystemMessage
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain.agents import create_agent
import asyncio
load_dotenv()
@tool
def weather_query(city: str) -> str:
    """
    智能网页搜索 / 天气查询工具。
    """
    return f"{city}的天气是晴天！"

agent = create_agent("deepseek-chat", tools=[weather_query])

async def chat(messages):
    async for event in agent.astream_events(
        {"messages": messages}
    ):
        print(event)

if __name__ == "__main__":
    asyncio.run(chat([SystemMessage(content="你是一个有帮助的助手。"),HumanMessage(content="北京天气如何？")]))