#
# all.py - Скрипт который запускает сначала систему сборки, потом запускает бинарник.
#


# Импортируем:
import os
import sys


# Если этот файл запускают:
if __name__ == "__main__":
    file_type = ".bat" if sys.platform == "win32" else ".sh"
    os.system(f"build{file_type} && run{file_type}")
