import gettext
import os
from fastapi import Request

# 指向翻译资源目录，不是 i18n.py
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "locale")  
print(LOCALE_DIR,9999999999999999)
TRANSLATORS = {}

def get_translator(lang: str):
    if lang in TRANSLATORS:
        return TRANSLATORS[lang]
    try:
        translator = gettext.translation(
            domain="messages", 
            localedir=LOCALE_DIR, 
            languages=[lang]
        )
        TRANSLATORS[lang] = translator.gettext
        return TRANSLATORS[lang]
    except FileNotFoundError:
        TRANSLATORS[lang] = gettext.gettext  # fallback
        return gettext.gettext

async def i18n_middleware(request: Request, call_next):
    lang = request.query_params.get("lang") or request.headers.get("accept-language", "zh").split(",")[0]
    request.state._ = get_translator(lang)
    response = await call_next(request)
    return response
