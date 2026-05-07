import os
import base64
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# ── LangChain LLM 初始化 ──────────────────────────────────────
tts_llm = ChatOpenAI(
    api_key=os.getenv("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1",
    model="mimo-v2.5-tts",
    model_kwargs={
        "audio": {"format": "wav", "voice": "Chloe"},
    },
)


# ── 语音合成 ───────────────────────────────────────────────────
async def synthesize_speech(
    text: str,
    style: str = "超级不耐烦，并且超级崩溃",
    output_path: str = "audio_file.wav",
) -> str:
    """
    使用 LangChain ChatOpenAI 调用 TTS 模型，将文本转为语音并保存。

    Args:
        text: 要转语音的文本内容
        style: 语音风格描述（情感/语调/语速等）
        output_path: 输出音频文件路径
    Returns:
        输出文件的路径
    """
    messages = [
        {"role": "user", "content": style},
        {"role": "assistant", "content": text},
    ]

    response = await tts_llm.ainvoke(messages)

    # 从 response_metadata 中提取音频数据
    audio_data = None
    raw = response.response_metadata or {}

    # 尝试从不同层级提取 base64 音频
    if "audio" in raw and isinstance(raw["audio"], dict):
        audio_data = raw["audio"].get("data")
    elif hasattr(response, "additional_kwargs") and "audio" in response.additional_kwargs:
        audio_info = response.additional_kwargs["audio"]
        if isinstance(audio_info, dict):
            audio_data = audio_info.get("data")

    if not audio_data:
        raise ValueError("TTS 响应中未找到音频数据，请检查模型是否支持 audio 输出")

    audio_bytes = base64.b64decode(audio_data)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    return output_path


# ── 直接运行示例 ───────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio

    # 更口语化、带情感色彩的内容
    sample_text = (
        "你和我分手吧，我受不了了"
        "你和别人结婚吧，我受不了了"
        "你和别人结婚吧，我受不了了"
        "你和别人结婚吧，我受不了了"
        "你和别人结婚吧，我受不了了"
    )

    result = asyncio.run(synthesize_speech(sample_text))
    print(f"音频已保存到: {result}")