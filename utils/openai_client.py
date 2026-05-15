from dotenv import load_dotenv
import json
from openai import AsyncOpenAI
from utils.openai_tools import TOOLS, TOOL_MAP
import os

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("MIMO_API_KEY"),
    base_url="https://token-plan-sgp.xiaomimimo.com/v1",
)

with open("utils/optimizer_system_prompt.md", "r", encoding="utf-8") as f:
    system_prompt = f.read()


async def chat_stream(messages):
    """
    手动实现 ReAct Agent 循环：
    用户消息 → LLM → 有工具调用？→ 执行工具 → 追加结果 → 再调 LLM → ... → 无工具调用 → 结束
    """
    llm_messages = [{"role": "system", "content": system_prompt}] + messages

    while True:
        collected_content = ""
        collected_reasoning = ""
        tool_calls_map = {}  # index -> {id, name, arguments}

        stream = await client.chat.completions.create(
            model="mimo-v2.5-pro",
            messages=llm_messages,
            tools=TOOLS,
            stream=True,
            extra_body={"thinking": {"type": "enabled"}},
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # 思考内容
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                collected_reasoning += reasoning
                yield {"content": reasoning, "type": "think"}

            # 正常文本
            if delta.content is not None:
                collected_content += delta.content
                yield {"content": delta.content, "type": "text"}

            # 工具调用（流式拼接）
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_map:
                        tool_calls_map[idx] = {
                            "id": tc.id or "",
                            "name": tc.function.name or "",
                            "arguments": tc.function.arguments or "",
                        }
                    else:
                        if tc.id:
                            tool_calls_map[idx]["id"] = tc.id
                        if tc.function and tc.function.name:
                            tool_calls_map[idx]["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls_map[idx]["arguments"] += tc.function.arguments

        # 没有工具调用，流式循环结束
        if not tool_calls_map:
            break

        # 有工具调用：执行工具并追加到消息列表，继续循环
        assistant_msg = {"role": "assistant", "content": collected_content or None}
        if collected_reasoning:
            assistant_msg["reasoning_content"] = collected_reasoning
        assistant_msg["tool_calls"] = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc["arguments"]},
            }
            for tc in tool_calls_map.values()
        ]
        llm_messages.append(assistant_msg)

        for tc in tool_calls_map.values():
            tool_name = tc["name"]
            tool_args = json.loads(tc["arguments"])

            # 通知前端：工具开始
            args = tool_args.get("city") or tool_args.get("query")
            yield {
                "type": "tool_start",
                "tool": tool_name,
                "tool_run_id": tc["id"],
                "args": args,
            }

            # 执行工具
            tool_func = TOOL_MAP.get(tool_name)
            if tool_func:
                tool_result = await tool_func(**tool_args)
            else:
                tool_result = f"未知工具: {tool_name}"

            # 解析工具结果
            tool_content = tool_result
            if isinstance(tool_result, str):
                try:
                    parsed = json.loads(tool_result)
                    if tool_name == "weather_query":
                        tool_content = parsed.get("full_data", parsed)
                    else:
                        tool_content = parsed
                except json.JSONDecodeError:
                    pass

            # 通知前端：工具结果
            yield {
                "type": "tool_mid",
                "tool": tool_name,
                "tool_run_id": tc["id"],
                "tool_content": tool_content,
            }

            # 追加工具结果到消息列表
            llm_messages.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": tool_result}
            )


async def generate_chat_title(text: str) -> str:
    resp = await client.chat.completions.create(
        model="mimo-v2.5-pro",
        messages=[
            {
                "role": "system",
                "content": "你是一个标题生成器。只输出一个简短的标题（不超过20个字），不要输出任何解释、前缀或其他内容。",
            },
            {"role": "user", "content": f"为以下对话生成标题：{text}"},
        ],
    )
    return resp.choices[0].message.content.strip()
