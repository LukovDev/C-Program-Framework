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
    prog_name = config["program-name"]
    build_dir = config["build-dir"]

    # Запускаем:
    os.chdir("../../")
    file_path = os.path.join(build_dir, bin_dirname, f"{prog_name}.exe" if sys.platform == "win32" else f"{prog_name}")
    if os.path.isfile(file_path):
        print(f"\n{' '*20}{'~<[PROGRAM OUTPUT]>~':-^40}{' '*20}")
        start_time = time.time()
        os.system(f"\"{os.path.normpath(file_path)} {' '.join(sys.argv[1:])}\"")
        print(f"\nExecution time: {round(time.time()-start_time, 4)}s")
    else:
        print(f"\nRun: File \"{file_path}\" not found!")


# Если этот скрипт запускают:
if __name__ == "__main__":
    main()
