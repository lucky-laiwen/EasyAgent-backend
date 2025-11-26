from ollama import chat,ChatResponse
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
import json
async def chat_with_ollama_stream(messages):
    search_result = ""
    full_messages = []
    with open(r"utils/optimizer_system_prompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()
    full_messages = [{
        "role": "system",
        "content": system_prompt
    }]
    full_messages += messages
    # deepseek-r1:7b   qwen3:8b
    response : ChatResponse = chat(
        model='qwen3:8b', 
        messages=full_messages,
        stream=True,
        tools=[weather_query,web_search]
    )
    for chunk in response:
        if chunk.message.tool_calls:
            tool_call = chunk.message.tool_calls[0]
            args = tool_call.function.arguments
            param = args.get("city") or args.get("query")
            tool_name = tool_call.function.name
            yield {"type": "tool_start", "tool": tool_name, "args": {args.get("city") or args.get("query"): param}}
            if tool_name == "weather_query":
                try:
                    res_str = await weather_query(param)  
                    res = json.loads(res_str)              
                    search_result = res["modal_data"]
                    yield {"type": "tool_mid", "tool": tool_name, "tool_content": res["full_data"]}
                except Exception as e:
                    print("调用 weather_query 出错:", e)
                    search_result = ""
            elif tool_name == "web_search":
                search_result = await web_search(param)
                yield {"type": "tool_mid", "tool": tool_name, "tool_content": search_result}

            full_messages.append({
                "role": "tool",
                "content": f"这是调用{tool_name}函数的结果：{search_result}"
            })
            response = chat(
                model='qwen3:8b', 
                messages=full_messages,
                stream=True,
                tools=[weather_query,web_search],
                think=False
            )
            for chunk in response:
                yield chunk.get("message", {})

        else:
            yield chunk.get("message", {})

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