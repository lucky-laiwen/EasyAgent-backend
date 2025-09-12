import gettext
import os
from fastapi import Request

LOCALE_DIR = os.path.abspath("locales")
DOMAIN = "messages"

def get_locale(request: Request) -> str:
    lang = request.headers.get("Accept-Language","en").split(",")[0].strip()
    return lang.split("-")[0]

async def i18n_middleware(request: Request, call_next):
    lang = get_locale(request)
    try:
        translator = gettext.translation(
            domain=DOMAIN,
            localedir=LOCALE_DIR,
            languages=[lang],
            fallback=False  # 不使用 gettext 原样返回
        )
    except FileNotFoundError:
        # 如果指定语言的文件不存在，使用默认语言
        translator = gettext.translation(
            domain=DOMAIN,
            localedir=LOCALE_DIR,
            languages=["en"],  # 默认语言
            fallback=True
        )
    request.state._ = translator.gettext  # ✅ 直接存到 request.state
    response = await call_next(request)
    return response
