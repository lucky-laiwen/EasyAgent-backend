import aiohttp
import json
from ddgs import DDGS
import asyncio
import os


async def fetch_json(url: str):
    """通用的 JSON 请求函数"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()


def normalize_city_name(city: str) -> str:
    for suffix in ["市", "县", "区", "镇", "乡", "村"]:
        if city.endswith(suffix):
            city = city[: -len(suffix)]
    return city


async def weather_query(city: str) -> str:
    """智能网页搜索 / 天气查询工具。"""
    data = {}
    with open(os.path.abspath("utils/city.json"), "r", encoding="utf-8") as f:
        content = f.read()
        for i in json.loads(content):
            if i["countyname"] == normalize_city_name(city):
                url = f"http://t.weather.sojson.com/api/weather/city/{i['areaid']}"
                data = await fetch_json(url)
                break

    if not data:
        return f"无法获取「{city}」的天气信息。"

    forecast = data["data"]["forecast"][0]
    cur_date = forecast["ymd"]
    high = forecast["high"]
    low = forecast["low"]
    week = forecast["week"]
    sunrise = forecast["sunrise"]
    sunset = forecast["sunset"]
    aqi = forecast["aqi"]
    fx = forecast["fx"]
    fl = forecast["fl"]
    weather_type = forecast["type"]
    notice = forecast.get("notice", "")
    air_quality = data["data"]["quality"]

    modal_str = (
        f"📍 当前城市：{city}\n\n"
        f"📅 日期：{cur_date}（{week}）\n\n"
        f"🌡 最高温度：{high}\n"
        f"🌡 最低温度：{low}\n\n"
        f"🌅 日出时间：{sunrise}\n"
        f"🌇 日落时间：{sunset}\n\n"
        f"💨 风向：{fx}\n"
        f"🍃 风力等级：{fl}\n\n"
        f"🌫 空气质量指数（AQI）：{aqi} / {air_quality}\n\n"
        f"☀️ 天气：{weather_type}\n\n"
        f"📝 小贴士：{notice}"
    )
    return json.dumps(
        {"modal_data": modal_str, "full_data": data["data"]["forecast"]},
        ensure_ascii=False,
    )


async def web_search(query: str) -> str:
    """智能网页搜索工具，支持文本、图片和新闻搜索。"""
    try:

        def search():
            with DDGS() as ddgs:
                text = list(ddgs.text(query, max_results=50))
                imgs = list(ddgs.images(query, max_results=50))
                news = list(ddgs.news(query, max_results=50))
                return {"text": text, "imgs": imgs, "news": news}

        results = await asyncio.to_thread(search)

        if not results:
            return "未查询到相关内容。"

        return json.dumps(results, ensure_ascii=False)

    except Exception as e:
        return f"搜索失败：{e}"


# OpenAI function calling 格式的工具定义
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "weather_query",
            "description": "智能网页搜索 / 天气查询工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "智能网页搜索工具，支持文本、图片和新闻搜索。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"],
            },
        },
    },
]

TOOL_MAP = {
    "weather_query": weather_query,
    "web_search": web_search,
}
