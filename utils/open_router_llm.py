from openrouter import OpenRouter
import os
import json
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

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
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "根据关键词进行网页搜索",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

async def weather_query(city:str):
    transport = StdioTransport(
        command="python",
        args=["utils/server.py"]
    )
    async with Client(transport=transport) as client:
        result = await client.call_tool("weather_query", {"city": city})
        return result.content[0].text
    
async def web_search(query:str):
    transport = StdioTransport(
        command="python",
        args=["utils/server.py"]
    )
    async with Client(transport=transport) as client:
        result = await client.call_tool("web_search", {"query": query})
        return result.content[0].text

async def chat_with_openrouter_stream(messages):
    search_result = ""

    with open("utils/optimizer_system_prompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    full_messages = [
        {"role": "system", "content": system_prompt},
        *messages
    ]

    async with OpenRouter(
        api_key="111"
    ) as client:

        # 流式调用
        stream = await client.chat.send_async(
            model="xiaomi/mimo-v2-flash:free",
            messages=full_messages,
            tools=TOOLS,
            stream=True
        )

        async for event in stream:
            delta = event.choices[0].delta
            # 1️⃣ reasoning
            if getattr(delta, "reasoning", None):
                yield {
                    "thinking": delta.reasoning
                }

            # 2️⃣ content
            if getattr(delta, "content", None):
                yield {
                    "content": delta.content
                }

            # 3️⃣ 工具调用
            if getattr(delta, "tool_calls", None):
                tool_call = delta.tool_calls[0]
                tool_name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    print("工具参数非 JSON:", tool_call.function.arguments)
                tool_call_id = getattr(tool_call, "id", None)
                # 统一取参数
                if isinstance(args, dict):
                    param = args.get("city") or args.get("query")
                elif isinstance(args, list) and len(args) > 0:
                    first_arg = args[0]
                    if isinstance(first_arg, dict):
                        param = first_arg.get("city") or first_arg.get("query")
                    else:
                        param = first_arg
                else:
                    param = None

                yield {
                    "type": "tool_start",
                    "tool": tool_name,
                    "args": args
                }

                # 执行工具
                if tool_name == "weather_query":
                    try:
                        res_str = await weather_query(param)
                        if not res_str:
                            res = {}  # 空 JSON 对象
                        else:
                            try:
                                res = json.loads(res_str)
                            except json.JSONDecodeError:
                                res = {}

                        search_result = res["modal_data"]
                        yield {
                            "type": "tool_mid",
                            "tool": tool_name,
                            "tool_content": res["full_data"]
                        }
                    except Exception as e:
                        search_result = ""
                elif tool_name == "web_search":
                    search_result = await web_search(param)
                    yield {
                        "type": "tool_mid",
                        "tool": tool_name,
                        "tool_content": search_result
                    }

                # 把 tool 结果塞回模型做二次推理
                full_messages.append({
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": search_result[:100],
                    "tool_call_id": tool_call_id
                })

                follow_stream = await client.chat.send_async(
                    model="openai/gpt-4o",
                    messages=full_messages,
                    tools=TOOLS,
                    stream=True
                )

                async for ev in follow_stream:
                    d = ev.choices[0].delta
                    if getattr(d, "content", None):
                        yield {
                            "type": "message",
                            "content": d.content
                        }


