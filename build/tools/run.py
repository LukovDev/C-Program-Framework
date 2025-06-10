#
# run.py - Скрипт запуска готовой программы.
#


# Импортируем:
import os
import sys
import json
import time


# Основная функция:
def main() -> None:
    # Читаем конфигурационный файл сборки:
    with open("../config.json", "r+", encoding="utf-8") as f: config = json.load(f)

    # Преобразование данных конфигурации в переменные:
    program_name = config["program-name"]

    # Запускаем:
    os.chdir("../../")
    print(f"{' '*20}{'~<[PROGRAM OUTPUT]>~':-^40}{' '*20}")
    pname = f"{program_name}.exe" if sys.platform == "win32" else f"{program_name}"
    start_time = time.time()
    os.system(f"\"build/out/{pname}\" {' '.join(sys.argv[1:])}")
    print(f"\nExecution time: {round(time.time()-start_time, 4)}s")


# Если этот скрипт запускают:
if __name__ == "__main__":
    main()
