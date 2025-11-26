import asyncio
import aiohttp
from fastmcp import FastMCP
from duckduckgo_search import DDGS
from datetime import datetime
import json
mcp = FastMCP("Web Search & Weather MCP")

async def fetch_json(url: str):
    """通用的 JSON 请求函数"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()
        
def normalize_city_name(city: str) -> str:
    # 去掉常见后缀
    for suffix in ["市", "县", "区","镇","乡","村"]:
        if city.endswith(suffix):
            city = city[:-len(suffix)]
    return city

@mcp.tool
async def weather_query(city: str) -> str:
    """
    智能网页搜索 / 天气查询工具。
    """

    # 默认 data 为 None
    data = {}
    with open(r'utils/city.json', 'r', encoding='utf-8') as f:
        content = f.read()
        for i in json.loads(content):
            if i['countyname'] == normalize_city_name(city):
                url = f"http://t.weather.sojson.com/api/weather/city/{i['areaid']}"
                data = await fetch_json(url)
                break  # 找到城市后就跳出

    if not data:
        return f"无法获取「{city}」的天气信息。"

    # 读取今日天气
    forecast = data["data"]["forecast"][0]  # 今日天气

    # 对应字段
    cur_date = forecast['ymd']          # 日期
    high = forecast['high']             # 最高温度
    low = forecast['low']               # 最低温度
    week = forecast['week']             # 星期
    sunrise = forecast['sunrise']       # 日出时间
    sunset = forecast['sunset']         # 日落时间
    aqi = forecast['aqi']               # 空气质量指数
    fx = forecast['fx']                 # 风向
    fl = forecast['fl']                 # 风力等级
    weather_type = forecast['type']     # 天气类型
    notice = forecast.get('notice', '') # 天气提示
    air_quality = data["data"]["quality"] # 空气质量

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

    return json.dumps({
        "modal_data": modal_str,
        "full_data": data["data"]["forecast"]  # 返回完整天气数组
    })



@mcp.tool
async def web_search(query: str):
    try:
        # 在子线程中调用同步搜索
        def search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, region="cn-zh", max_results=20))

        results = await asyncio.to_thread(search)

        if not results:
            return f"未找到与「{query}」相关的结果。"

        return results

    except Exception as e:
        return f"搜索失败：{e}"


if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())
