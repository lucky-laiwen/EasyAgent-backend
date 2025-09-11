import gettext
import os

LOCALE_DIR = r"D:\xlw\KiwiCode\EasyAgent-backend\i18n"
lang = "zh"

t = gettext.translation("messages", localedir=LOCALE_DIR, languages=[lang], fallback=True)
_ = t.gettext

print(_("login_success"))  # 应该输出：登录成功！
