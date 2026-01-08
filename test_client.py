import asyncio
from openrouter import OpenRouter
from fastmcp.client.transports import StdioTransport
from fastmcp import Client
import json

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "weather_query",
            "description": "查询指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

async def weather_query(city: str):
    transport = StdioTransport(
        command="python",
        args=["utils/server.py"]
    )
    async with Client(transport=transport) as client:
        result = await client.call_tool("weather_query", {"city": city})
        # 打印工具原始返回对象
        print("=== weather_query 原始返回 ===")
        print(result)
        return result.content[0].text

async def main():
    async with OpenRouter(
        api_key="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"
    ) as client:

        response = await client.chat.send_async(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": "查询南京今天的天气"},{"role":"system","content":"""
                            1. 天气查询（weather_query）

                            触发条件：当用户的问题中出现以下关键词时调用：
                            天气、气温、气候、风速、湿度、空气质量、紫外线、下雨、晴天、冷、热、预报

                                天气查询规则说明：

                                1. 仅接收城市名参数，例如 "杭州"，并去掉所有地级市、县级市、区、镇、村、乡等后缀。
                                - 示例：输入 "杭州市西湖区" 或 "西湖区" → 统一解析为 "杭州" 或所属区。
                                2. 若输入的是镇、村、乡等较小行政区，则自动使用其所属县/区作为查询城市。
                                - 示例：输入 "临安区青山镇" → 查询 "临安区" 的天气。
                                3. 返回内容仅包含城市名和天气信息，不附加“今日天气”等额外文字。
                                4. 如果用户输入的城市不存在，则选择最接近匹配的城市，并返回匹配提示。
                                5. 确保输出清晰简洁，去掉无用词汇，方便前端展示。


                                输出要求：
                                严格原样输出 MCP 工具返回的内容，不得改写、删减、添加或重新组织文本。
                                禁止总结、解释或附加其他文字。
                            """}],
            stream=False,
            tools=TOOLS
        )

        print("机器人回复",response)

if __name__ == "__main__":
    asyncio.run(main())
