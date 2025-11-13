import asyncio
import aiohttp
from fastmcp import FastMCP
from duckduckgo_search import DDGS
mcp = FastMCP("Web Search & Weather MCP")

async def fetch_json(url: str):
    """通用的 JSON 请求函数"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            return await resp.json()
        
def get_weather_desc(code):
    match code:
        case "Sunny" | "Clear":
            return "晴天"
        case "PartlyCloudy" | "Partly cloudy":
            return "局部多云"
        case "Cloudy" | "Overcast" | "VeryCloudy":
            return "多云"
        case "Rain" | "LightRain" | "HeavyRain" | "Showers" | "LightShowers" | "HeavyShowers":
            return "下雨"
        case "Thunder" | "ThunderyShowers":
            return "雷雨"
        case "Snow" | "LightSnow" | "HeavySnow" | "SnowShowers":
            return "雪"
        case "Sleet" | "LightSleet" | "HeavySleet" | "SleetShowers":
            return "雨夹雪"
        case "Fog" | "Mist":
            return "雾"
        case "Hail":
            return "冰雹"
        case "FreezingRain":
            return "冻雨"
        case _:
            return "未知天气"


@mcp.tool
async def weather_query(city: str) -> str:
    """
    智能网页搜索 / 天气查询工具。
    - 若 query 包含天气相关词汇，则调用 wttr.in API。
    - 否则使用 DuckDuckGo API 进行搜索。
    """

    # 使用 wttr.in 进行天气查询
    url = f"https://wttr.in/{city}?format=j1"
    data = await fetch_json(url)
    if not data:
        return f"无法获取「{city}」的天气信息。"

    current = data["current_condition"][0]
    desc = current.get("lang_zh", [{"value": current.get("weatherDesc", [{'value': '未知'}])[0]['value']}])[0]['value']
        
    temp = current.get("temp_C", "?")
    feel = current.get("FeelsLikeC", "?")
    humidity = current.get("humidity", "?")
    wind = current.get("windspeedKmph", "?")
    direction = current.get("winddir16Point", "?")
    uv = current.get("uvIndex", "?")
    pressure = current.get("pressure", "?")

    return (
        f"📍 当前城市：{city}\n\n"
        f"🌤 天气状况：{get_weather_desc(desc)}\n\n"
        f"🌡 实际温度：{temp}°C（体感 {feel}°C）\n\n"
        f"💧 湿度：{humidity}%\n\n"
        f"💨 风速：{wind} km/h（{direction}）\n\n"
        f"☀️ 紫外线指数：{uv}\n\n"
        f"🌪 气压：{pressure} hPa"
    )

@mcp.tool
async def web_search(query: str):
    try:
        # 在子线程中调用同步搜索
        def search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, region="cn-zh", max_results=10))

        results = await asyncio.to_thread(search)

        if not results:
            return f"未找到与「{query}」相关的结果。"

        return results

    except Exception as e:
        return f"搜索失败：{e}"


if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())
