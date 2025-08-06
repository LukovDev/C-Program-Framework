#
# run.py - Скрипт запуска готовой программы.
#


# Импортируем:
import os
import sys
import time
import subprocess
from build import Vars


# Вывести лог отладки сборки:
def log(msg: str, end: str = "\n") -> None:
    if not Vars.build_lg: return
    print(msg, end=end)


# Основная функция:
def main() -> None:
    # Инициализируем переменные:
    Vars.init_vars("../config.json")

    # Преобразование данных конфигурации в переменные:
    prog_name   = Vars.prog_name
    build_dir   = Vars.build_dn
    bin_dirname = Vars.bin_dn

    # Запускаем:
    os.chdir("../../")
    file_path = os.path.join(build_dir, bin_dirname, f"{prog_name}.exe" if sys.platform == "win32" else f"{prog_name}")
    if os.path.isfile(file_path):
        log(f"\n{' '*20}{'~<[PROGRAM OUTPUT]>~':-^40}{' '*20}")
        start_time = time.time()
        result = subprocess.run([os.path.normpath(file_path), ' '.join(sys.argv[1:])]).returncode
        print(f"\nProcess returned: {result} <{hex(result)}>")
        print(f"Execution time: {round(time.time()-start_time, 4)}s")
    else:
        print(f"\nRun: File \"{file_path}\" not found!")


# Если этот скрипт запускают:
if __name__ == "__main__":
    main()
