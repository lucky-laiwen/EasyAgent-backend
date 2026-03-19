from ollama import chat,ChatResponse,Client as ollama_client
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
import json
import time
import asyncio
# 主要聊天
async def chat_with_ollama_stream(messages):
    weather_search_result = ""
    web_search_result = {}
    full_messages = []
    cur_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open(r"utils/optimizer_system_prompt.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()
    full_messages = [{
        "role": "system",
        "content": system_prompt + f"当前时间为{cur_time}。"
    }]
    full_messages += messages
    client = ollama_client(
        host="https://ollama.com",
        headers={'Authorization': 'bede7a62497b4316adef41f8cb4dfb7e.6qjsZv3RxGTfmOApCgmhU01z'}
    )
    
    response : ChatResponse = client.chat(
        model='qwen3.5:397b-cloud', 
        messages=full_messages,
        stream=True,
        tools=[weather_query,web_search],
        think=True
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
                    weather_search_result = res["modal_data"]
                    yield {"type": "tool_mid", "tool": tool_name, "tool_content": res["full_data"]}
                except Exception as e:
                    print("调用 weather_query 出错:", e)
                    weather_search_result = ""
            elif tool_name == "web_search":
                web_search_result = await web_search(param)
                yield {"type": "tool_mid", "tool": tool_name, "tool_content": web_search_result}

            full_messages.append({
                "role": "tool",
                "content": f"这是调用{tool_name}函数的结果：{
                    web_search_result['news'][1:10] if isinstance(web_search_result, dict) and 'news' in web_search_result 
                    else web_search_result['text'][1:10] if isinstance(web_search_result, dict) and 'text' in web_search_result 
                    else str(web_search_result) if tool_name == "web_search" 
                    else weather_search_result
                }"
            })

            new_response = client.chat(
                model='qwen3.5:397b-cloud', 
                messages=full_messages,
                stream=True,
                think=False
            )
            
            for chunk in new_response:
                thinking = chunk.get("message", {}).get("thinking", False)
                if not thinking:
                    yield chunk.get("message", {})

        else:
            yield chunk.get("message", {})

async def generate_chat_title(messages):
    client = ollama_client(
        host="https://ollama.com",
        headers={'Authorization': 'bede7a62497b4316adef41f8cb4dfb7e.6qjsZv3RxGTfmOApCgmhU01z'}
    )
    response = client.chat(
        model='qwen3.5:397b-cloud', 
        messages=[
            {
                "role": "system",
                "content":"请用不超过20个字概括下面这句话的核心主题，作为聊天标题,其余一律不要生成"
            },
            {
                "role": "user",
                "content":messages
            }
        ],
        stream=False,
        think=False
    )
    return response.get("message",{}).get("content")

async def weather_query(city:str):
    transport = StdioTransport(
        command="python",
        args=["utils/server.py"]
    )
    async with Client(transport=transport) as client:
        result = await client.call_tool("weather_query", {"city": city})
        return result.content[0].text
    
async def web_search(query: str, max_retry: int = 3):
    for _ in range(max_retry):
        transport = StdioTransport(
            command="python",
            args=["utils/server.py"]
        )

        async with Client(transport=transport) as client:
            result = await client.call_tool("web_search", {"query": query})

            if result and getattr(result, "content", None):
                text = getattr(result.content[0], "text", None)
                if text:
                    return json.loads(text)

        await asyncio.sleep(0.5)

    return "未查询到相关内容。"

