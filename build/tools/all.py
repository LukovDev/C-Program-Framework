#
# all.py - Скрипт, который запускает сначала систему сборки, потом запускает бинарник.
#


# Импортируем:
import os
import sys


# Если этот файл запускают:
if __name__ == "__main__":
    cfg = "build/config.json"
    if sys.platform == "win32":
        os.system(f"build.bat -cfg {cfg} && run.bat -cfg {cfg}")
    else: os.system(f"bash build.sh -cfg {cfg} && bash run.sh -cfg {cfg}")
