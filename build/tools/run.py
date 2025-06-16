#
# run.py - Скрипт запуска готовой программы.
#


# Импортируем:
import os
import sys
import json
import time
from build import bin_dirname


# Основная функция:
def main() -> None:
    # Читаем конфигурационный файл сборки:
    with open("../config.json", "r+", encoding="utf-8") as f: config = json.load(f)

    # Преобразование данных конфигурации в переменные:
    program_name = config["program-name"]

    # Запускаем:
    os.chdir("../../")
    bin_dir = f"build/{bin_dirname}/"
    file_path = os.path.join(bin_dir, f"{program_name}.exe" if sys.platform == "win32" else f"{program_name}")
    if os.path.isfile(file_path):
        print(f"\n{' '*20}{'~<[PROGRAM OUTPUT]>~':-^40}{' '*20}")
        start_time = time.time()
        os.system(f"\"{file_path}\" {' '.join(sys.argv[1:])}")
        print(f"\nExecution time: {round(time.time()-start_time, 4)}s")
    else:
        print(f"Run: File \"{file_path}\" not found!")


# Если этот скрипт запускают:
if __name__ == "__main__":
    main()
