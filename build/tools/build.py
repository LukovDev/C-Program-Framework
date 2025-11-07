#
# build.py - Скрипт системы сборки.
#
# Этот скрипт должен быть запущен в каталоге "<build-dir>/tools/"
#
# [ C-Program-Framework BuildSystem for PC <v3.0.0> ]
#

VERSION = "3.0.0"  # Версия этой системы сборки.


# Импортируем:
import os
import re
import sys
import glob
import json
import time
import shutil
import subprocess
from functools import partial
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor


# Класс глобальных переменных:
class Vars:
    # Конфигурация:
    prog_name: str  = "Undefined"
    prog_icon: str  = None      # None | str.
    src_dp:    list = ["str/"]  # src dirs (paths).
    build_dn:  str  = "build/"  # build dir name.
    bin_dn:    str  = "bin"     # bin dir name.
    obj_dn:    str  = "obj"     # obj dir name.
    libs_dn:   str  = ""        # libs dir name (in bin dir).
    build_lg:  bool = True      # Build logging.
    m_threads: bool = True      # Multi-thread building.
    strip:     bool = False     # Strip.
    prog_perc: bool = True      # Show progress in percent.
    con_dis:   bool = False     # Console disabled (for windows).
    defines:   list = []        # Defines on compilation.
    includes:  list = []        # Include dirs (paths).
    libraries: list = []        # Libraries dirs (paths).
    libnames:  list = []        # Libraries names.
    optimiz:   str  = "-O0"     # Code optimization level.
    std_c:     str  = "c17"     # Std C version.
    std_cpp:   str  = "c++17"   # Std C++ version.
    comp_c:    str  = "gcc"     # C Compiler.
    comp_cpp:  str  = "g++"     # C++ Compiler.
    linker:    str  = "g++"     # Linker.
    warnings:  list = []        # Warning flags.
    comp_fg:   list = []        # Compiler flags (during compiling).
    link_fg:   list = []        # Linker flags (during linking).

    # Прочее:
    config:        dict = {}      # Текст конфигурации.
    total_src:     list = []      # Список путей до исходников для компиляции.
    reset_build:   bool = False   # Сбросить сборку.
    log_queue:     list = []      # Очередь логов (стек).
    cpu_threads:   int  = 1       # Количество потоков процессора (хотя бы 1).

    compile_lock        = Lock()  # Блокировка счетчика.
    real_compiled: int  = 0       # Сколько реально скомпилировано.
    to_compile:    int  = 0       # Сколько должно быть скомпилировано.
    compile_done:  bool = False   # Компиляция завершена.

    analys_lock         = Lock()  # Блокировка счетчика.
    real_analysed: int  = 0       # Сколько реально анализировано.
    to_analys:     int  = 0       # Сколько должно быть анализировано.
    analys_done:   bool = False   # Анализ завершен.

    header_mtime_cache: dict = {}  # Глобальный кэш времени модификации заголовочных файлов.

    # Причины сброса сборки:
    build_clear:   bool = False  # Очистка сборки.
    build_no_meta: bool = False  # Отсутствует мета-файл.
    build_cfg_edt: bool = False  # Файл конфигурации редактирован.
    build_new_os:  bool = False  # Сборка на новой системе.
    build_new_os_info: dict = {"old": "UNK", "new": "UNK"}

    # Инициализировать переменные:
    @staticmethod
    def init_vars(config_path: str) -> None:
        with open(config_path, "r+", encoding="utf-8") as f:
            Vars.config = json.load(f)

        # Заполняем поля данными:
        Vars.prog_name = Vars.config["program-name"]
        Vars.prog_icon = Vars.config["program-icon"]
        Vars.src_dp    = Vars.config["source-dirs"]
        Vars.build_dn  = Vars.config["build-dir"]
        Vars.bin_dn    = Vars.config["bin-dir-name"]
        Vars.obj_dn    = Vars.config["obj-dir-name"]
        Vars.libs_dn   = Vars.config["libs-output"]
        Vars.build_lg  = Vars.config["build-logging"]
        Vars.m_threads = Vars.config["multi-threads"]
        Vars.strip     = Vars.config["strip"]
        Vars.prog_perc = Vars.config["progress-percent"]
        Vars.con_dis   = Vars.config["console-disabled"]
        Vars.defines   = Vars.config["defines"]
        Vars.includes  = Vars.config["includes"]
        Vars.libraries = Vars.config["libraries"]
        Vars.libnames  = Vars.config["libnames"]
        Vars.optimiz   = Vars.config["optimization"]
        Vars.std_c     = Vars.config["std-c"]
        Vars.std_cpp   = Vars.config["std-cpp"]
        Vars.comp_c    = Vars.config["compiler-c"]
        Vars.comp_cpp  = Vars.config["compiler-cpp"]
        Vars.linker    = Vars.config["linker"]
        Vars.warnings  = Vars.config["warnings"]
        Vars.comp_fg   = Vars.config["compile-flags"]
        Vars.link_fg   = Vars.config["linker-flags"]


# Отдельный поток для вывода логов компиляции:
def compile_log_thread() -> None:
    if Vars.to_compile == 0 or not Vars.build_lg: return
    compiled = 0  # Сколько было скомпилировано (логов компиляции).
    old_progress = ""

    # Пока мы не закончим компиляцию:
    start_time = time.time()
    while not Vars.compile_done:
        if Vars.log_queue:  # Если в очереди есть логи:
            compiled += 1
            target_num = f"[{compiled:{len(str(Vars.to_compile))}d}/{Vars.to_compile}]"
            print(f"\033[2K{target_num} {Vars.log_queue.pop(0)}")

        # Выводим прогресс компиляции:
        if Vars.prog_perc: progress = f"{Vars.real_compiled/Vars.to_compile*100:.1f}% done..."
        else: progress = f"{Vars.real_compiled} done of {Vars.to_compile}..."
        if old_progress != progress:
            print(f"Progress {progress}", end="\r", flush=True)
            old_progress = progress

        time.sleep(1/100)  # Интервал вывода и проверки.
    print("\r\033[2K", end="")  # Полностью очистить строку.
    if Vars.real_compiled == Vars.to_compile:
        print(f"\nCompilation finished: {time.time()-start_time:.2f}s")

    # В случае если что-то пошло не так:
    if compiled != Vars.to_compile:
        print(f"[!] Something went wrong... (compiled {compiled} of {Vars.to_compile} targets).")


# Вывести лог отладки сборки:
def log(msg: str, end: str = "\n") -> None:
    if not Vars.build_lg: return
    print(msg, end=end)


# Вывести лог отладки ошибки:
def log_error(msg: str) -> None:
    # if not Vars.build_lg: return
    print(f"BuildSystem: [!] Error: {msg}")
    os._exit(1)  # Жёстко останавливаем сборку.


# Обработать аргументы:
def handle_args() -> None:
    is_exit = False
    for arg in sys.argv[1:]:
        # Если передан флаг об очистке объектных файлов:
        if arg in ["-c", "-clear"]:
            Vars.build_clear = True
            Vars.reset_build = True

        # Если передан флаг для получения версии системы сборки:
        elif arg in ["-v", "-version"]:
            log(f"\nC-Program-Framework BuildSystem for PC <v{VERSION}>\n")
            is_exit = True

        # Если передан флаг для получения помощи:
        elif arg in ["-h", "-help"]:
            log("\n"
                "+ List of arguments:\n"
                "| [-c] / [-clear] - Delete previous build and build it again (Build is running).\n|\n"
                "| [-v] / [-version] - Get version of the build system (Build is not start).\n|\n"
                "| [-h] / [-help] - Get help with the startup arguments (Build is not start).\n+\n"
            )
            is_exit = True

        # Неизвестная команда:
        else:
            log(f"Unknown argument: \"{arg}\"")
    if is_exit: sys.exit(0)


# Глобальный кэш для всех заголовков:
def get_header_mtime(path) -> float:
    if path in Vars.header_mtime_cache:
        return Vars.header_mtime_cache[path]
    mtime = os.path.getmtime(path)
    Vars.header_mtime_cache[path] = mtime
    return mtime


# Рекурсивно собирает все заголовочные файлы, включая вложенные, из исходника:
def collect_all_includes(path: str, inc_dirs: list[str] = None, _visited=None, _found=None) -> dict:
    path = os.path.abspath(path.strip('"'))

    if inc_dirs is None: inc_dirs = []
    if _visited is None: _visited = set()  # Нужен для предотвращения рекурсивных циклов.
    if _found is None: _found = {}         # Для уникальности заголовков в результате.

    # Если файл уже посещён или не существует - пропускаем:
    if path in _visited or not os.path.isfile(path): return _found
    _visited.add(path)  # Добавляем в посещенные.

    src_dir = os.path.dirname(path)  # Директория текущего файла, нужна, чтобы искать локальные include’ы.

    try:
        # Чтение файла построчно:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                # Регулярка ищет конструкции вида #include "file.h" или #include <file.h>:
                match = re.search(r'#include\s*[<"]([^">]+)[">]', line)
                if not match: continue

                # Формируем возможные пути для поиска файла:
                inc_name = match.group(1)  # Имя из #include (например, "../core/mm.h").
                candidate_paths = [
                    os.path.abspath(os.path.join(src_dir, inc_name))
                ] + [
                    os.path.abspath(os.path.join(inc_dir, inc_name))
                    for inc_dir in inc_dirs
                ]

                # Проверяем каждый возможный путь:
                for inc_path in candidate_paths:
                    if os.path.isfile(inc_path):
                        if inc_path in _found: break  # Уже есть в словаре.
                        _found[inc_path] = get_header_mtime(inc_path)
                        # Рекурсивно собираем include’ы этого заголовка:
                        collect_all_includes(inc_path, inc_dirs, _visited, _found)
                        break
    except Exception: pass
    return _found  # {путь_до_заголовка: время_изменения, ...}


# Функция для поиска всех файлов определённого формата:
def find_files(path: str, form: str) -> list:
    return [p.replace("\\", "/") for p in glob.glob(os.path.join(path, f"**/*.{form}"), recursive=True)]


# Генерируем уникальные имена объектных файлов с учётом пути:
def generate_obj_filename(path: str) -> str:
    norm = path.replace("/", "_").replace("\\", "_")
    return os.path.join(Vars.build_dn, Vars.obj_dn, norm + ".o")


# Получить метаинформацию:
def get_metainfo() -> dict:
    return {
        "os": sys.platform,
        "build-system-version": VERSION,
        "config": Vars.config,
    }


# Читаем мета-данные:
def load_metadata(file_path: str) -> dict:
    if not os.path.isfile(file_path):  # "<build-dir>/tools/file_path".
        with open(file_path, "w+", encoding="utf-8") as f:
            json.dump({
                "metainfo": get_metainfo(),
                "files": {}
            }, f, indent=4)
        Vars.build_no_meta = True
        Vars.reset_build = True
    with open(file_path, "r+", encoding="utf-8") as f:
        metadata = json.load(f)
    # Если не указана версия системы сборки, или она не совпадает с этой - пересоздаём:
    if "build-system-version" not in metadata["metainfo"] or metadata["metainfo"]["build-system-version"] != VERSION:
        os.remove(file_path)
        metadata = load_metadata(file_path)
    return metadata


# Сохраняем мета-данные:
def save_metadata(file_path: str, data: dict) -> None:
    with open(os.path.join(Vars.build_dn, file_path), "w+", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# Получить новые метаданные:
def get_new_metadata(all_files: list) -> dict:
    new_all_files = []

    # Отдельный поток для вывода прогресса анализа:
    def analysis_log_thread() -> None:
        if not Vars.build_lg: return
        old_progress = ""

        # Пока мы не закончим анализ:
        start_time = time.time()
        while not Vars.analys_done:
            # Выводим прогресс компиляции:
            if Vars.prog_perc: progress = f"{Vars.real_analysed/Vars.to_analys*100:.1f}% done..."
            else: progress = f"{Vars.real_analysed} done of {Vars.to_analys}..."
            if old_progress != progress:
                print(f"Analysis {progress}", end="\r", flush=True)
                old_progress = progress
            time.sleep(1/100)  # Интервал вывода и проверки.
        print("\r\033[2K", end="")  # Полностью очистить строку.
        if Vars.real_analysed == Vars.to_analys:
            print(f"Analysis deps finished: {time.time()-start_time:.2f}s")

    def find_deps(path: str) -> list:
        nonlocal new_all_files
        new_all_files.append([path, collect_all_includes(path, inc_dirs=Vars.includes)])
        with Vars.analys_lock: Vars.real_analysed += 1

    # Поиск зависимостей исходников:
    Vars.to_analys = len(all_files)
    log_analysis_thread = Thread(target=analysis_log_thread, daemon=True)
    log_analysis_thread.start()
    if Vars.m_threads:
        # Создаём отдельные потоки для поиска:
        with ThreadPoolExecutor(max_workers=Vars.cpu_threads) as exc:
            exc.map(find_deps, all_files)
    else:
        # Просто ищем поочерёдно:
        for path in all_files: find_deps(path)
    Vars.analys_done = True
    log_analysis_thread.join()  # Ждём завершение вывода логов компиляции.

    return {
        "metainfo": get_metainfo(),
        "files": {
            # Путь_до_исходника: {"time": время_изменения, "headers": словарь_зависимостей}
            f[0].strip('"'): {
                "time": os.path.getmtime(f[0].strip('"')),
                "headers": f[1]
            } for f in new_all_files
        }
    }


# Поиск всех .c/.cpp файлов:
def find_all_c_cpp_files() -> dict:
    found_files = {"c": [], "cpp": []}  # Найденные файлы.

    # Проходимся по всем папкам-исходникам:
    for src_dir in Vars.src_dp:
        if not os.path.isdir(src_dir):
            log_error(f"\nDirectory \"{src_dir}\" not found.")
            sys.exit()
        # Ищем и сохраняем пути до найденных файлов:
        for f in find_files(src_dir, "c"):
            if f"\"{f}\"" not in found_files["c"]: found_files["c"].append(f"\"{f}\"")
        for f in find_files(src_dir, "cpp"):
            if f"\"{f}\"" not in found_files["cpp"]: found_files["cpp"].append(f"\"{f}\"")
    return found_files


# Ищем необходимые динамические библиотеки:
def find_dynamic_libs() -> list:
    if sys.platform.startswith("win32") or sys.platform.startswith("cygwin"): exts = ["dll"]
    elif sys.platform.startswith("linux"): exts = ["so"]
    elif sys.platform.startswith("darwin"): exts = ["dylib", "framework"]
    else: exts = ["dll", "so", "dylib"]
    libnames_clean, result = [name.lower().lstrip("lib") for name in Vars.libnames], []
    for libdir in Vars.libraries:
        for ext in exts:
            for full_path in find_files(libdir, ext):
                name = os.path.basename(full_path).lower()
                if name.endswith(f".{ext}"): name = name[:-(len(ext)+1)]
                if name.startswith("lib"): name = name[3:]
                if name in libnames_clean: result.append(full_path)
    return result


# Проверяем папки сборки:
def check_dirs() -> None:
    # Создаём папку объектов если её нет:
    obj_full_dn = os.path.join(Vars.build_dn, Vars.obj_dn)
    if not os.path.isdir(obj_full_dn): os.mkdir(obj_full_dn)

    # Создаём папку бинара (пересоздаём при существовании):
    bin_full_dn = os.path.join(Vars.build_dn, Vars.bin_dn)
    if os.path.isdir(bin_full_dn): shutil.rmtree(bin_full_dn)
    os.mkdir(bin_full_dn)


# Проверяем изменение конфига:
def check_configs(metadata: dict, metadata_new: dict) -> None:
    # Если конфиги разные, надо сбросить сборку:
    if ("config" not in metadata["metainfo"]) or ("config" not in metadata_new["metainfo"]) or \
            (metadata["metainfo"]["config"] != metadata_new["metainfo"]["config"]):
        Vars.build_cfg_edt = True
        Vars.reset_build = True


# Обрабатываем файлы:
def process_files(metadata: dict, metadata_new: dict) -> None:
    # Получаем поле метаинформации и файлов из метаданных:
    metainfo, files = metadata["metainfo"], metadata["files"]
    metainfo_new, files_new = metadata_new["metainfo"], metadata_new["files"]

    # Получаем имена операционных систем на которых производились сборки:
    m_os = metainfo.get("os")
    m_os_new = metainfo_new.get("os")

    # Находим измененные, новые и удаленные файлы:
    meta_changed, meta_added, meta_removed = [], [], []
    for path, data_new in files_new.items():
        time_new, headers_new = data_new["time"], data_new["headers"]
        if path not in files:
            meta_added.append(path)
            continue

        # Проверяем время изменения исходника:
        changed = False
        time_old, headers_old = files[path]["time"], files[path]["headers"]
        if time_old != time_new: changed = True
        else:  # Иначе проверяем время изменения заголовков:
            for h, htime in headers_new.items():
                if h not in headers_old or headers_old[h] != htime:
                    changed = True
                    break

        # Если файл изменился, добавляем его в список изменённых:
        if changed: meta_changed.append(path)
    for path in files:
        if path not in files_new: meta_removed.append(path)
    total_src = meta_added+meta_changed

    # Удаляем все объектные файлы, если прошлая сборка была сделана на другой системе:
    obj_full_dn = os.path.join(Vars.build_dn, Vars.obj_dn)
    if m_os != m_os_new:
        Vars.build_new_os = True
        Vars.build_new_os_info["old"] = m_os
        Vars.build_new_os_info["new"] = m_os_new
        Vars.reset_build = True

    # Сбрасываем сборку путём удаления всех объектных файлов:
    if Vars.reset_build:
        for file in os.listdir(obj_full_dn):
            if file.endswith(".o"): os.remove(os.path.join(obj_full_dn, file))

    # Удаление объектных файлов по списку удалённых исходников:
    for path in meta_removed:
        obj_path = os.path.splitext(path)[0] + ".o"
        if os.path.exists(obj_path): os.remove(obj_path)

    # Список всех актуальных .o файлов:
    obj_files = {  # [(Обработанное имя исходника в .o формате):(Полный путь к исходнику)].
        generate_obj_filename(path): path
        for path in files_new
    }

    # Удаление .o файлов, исходников которых больше нет:
    # Пометка: Проверяем существующие .o файлы (с обработанным именем) на отсутствие в obj_files.
    for obj in [os.path.join(obj_full_dn, f) for f in os.listdir(obj_full_dn)
                if f.endswith(".o") and f != "icon.o"]:
        if obj not in obj_files and os.path.isfile(obj):
            os.remove(obj)

    # Проверка на отсутствующие .o файлы:
    for obj_path, src_path in obj_files.items():
        # Если исходника нет в массиве исходников и файл .o исходника отсутствует:
        if src_path not in total_src and not os.path.isfile(obj_path):
            total_src.append(src_path)
    Vars.total_src = total_src  # Обновляем массив исходников.


# Пересоздать иконку для системы виндовс:
def recreate_windows_icon() -> None:
    try:
        obj_full_dn = os.path.join(Vars.build_dn, Vars.obj_dn)

        # Удаляем файлы иконок из папки объектов:
        if os.path.isdir(obj_full_dn):
            [os.remove(os.path.join(obj_full_dn, f))
            for f in os.listdir(obj_full_dn)
            if f.endswith(".ico")]

        # Создаём .o файл иконки если это Windows система:
        icon_rc_path = os.path.join(obj_full_dn, "icon.rc")
        if sys.platform == "win32" and Vars.prog_icon is not None and os.path.isfile(Vars.prog_icon):
            with open(icon_rc_path, "w+", encoding="utf-8") as f:
                f.write(f"IDI_ICON1 ICON \"{os.path.basename(Vars.prog_icon)}\"")
            shutil.copy(f"{Vars.prog_icon}", os.path.join(obj_full_dn))
            subprocess.run(["windres", icon_rc_path, os.path.join(obj_full_dn, 'icon.o')], check=True)

        # Если не Windows или null иконка, то удаляем объект иконки:
        elif os.path.isfile(os.path.join(obj_full_dn, "icon.o")):
            os.remove(os.path.join(obj_full_dn, "icon.o"))
        if os.path.isfile(icon_rc_path): os.remove(icon_rc_path)
    except Exception as error:
        log_error(f"Recreate icon for windows: {error}")


# Компилировать файл:
def compile_file(file_path: str, compile_flags: list) -> None:
    try:
        if   os.path.splitext(file_path)[1] == ".c":   comp_flag, std_flag = f"{Vars.comp_c}",   f"-std={Vars.std_c}"
        elif os.path.splitext(file_path)[1] == ".cpp": comp_flag, std_flag = f"{Vars.comp_cpp}", f"-std={Vars.std_cpp}"
        Vars.log_queue.append(f"{file_path}")

        # Компилируем:
        args = [comp_flag, std_flag] + compile_flags + ["-c", file_path, "-o", generate_obj_filename(file_path)]
        subprocess.run([a for a in args if a], text=True, check=True)

        with Vars.compile_lock: Vars.real_compiled += 1
    except subprocess.CalledProcessError as error:
        log_error(f"Compile returned status: {error.returncode}")


# Линковать объектные файлы в один исполняемый файл:
def link_files(linker_flags: list, linker_lib_flags: list) -> None:
    try:
        obj_full_dn = os.path.join(Vars.build_dn, Vars.obj_dn)
        prog_full_path = os.path.join(Vars.build_dn, Vars.bin_dn, Vars.prog_name)
        obj_files = glob.glob(f"{obj_full_dn}/**/*.o", recursive=True)

        # Линкуем:
        start_time = time.time()
        log("Linking files... ", end="\r")
        args = [Vars.linker] + linker_flags + obj_files + linker_lib_flags + ["-o", prog_full_path]
        subprocess.run([a for a in args if a], check=True)
        log(f"\033[2KLinking finished: {time.time()-start_time:.2f}s")
    except subprocess.CalledProcessError as error:
        log_error(f"Linker returned status: {error.returncode}")
    except Exception as error:
        log_error(f"Linker: {error}")


# Копируем необходимые библиотеки в папку бинара:
def copy_libs(all_libs: list) -> None:
    try:
        full_libs_dn = os.path.normpath(os.path.join(Vars.build_dn, Vars.bin_dn, Vars.libs_dn))
        if not os.path.isdir(full_libs_dn): os.makedirs(full_libs_dn, exist_ok=True)
        start_time = time.time()
        log("Copying dynamic libraries... ", end="\r")
        for path in all_libs:
            if os.path.isfile(path): shutil.copy2(path, full_libs_dn)
        log(f"\033[2KCopying libs finished: {time.time()-start_time:.2f}s")
    except Exception as error:
        log_error(f"Copying libs: {error}")


# Основная функция:
def main() -> None:
    Vars.init_vars("../config.json")  # Инициализируем переменные.
    metadata = load_metadata("metadata.json")  # Читаем мета-данные.
    Vars.cpu_threads = os.cpu_count()  # Узнаем количество ядер.

    os.chdir("../../")  # Переходим в корневую директорию из "<build-dir>/tools/".

    # Обработать аргументы:
    handle_args()

    # Поиск всех .c/.cpp файлов:
    found_files = find_all_c_cpp_files()
    all_files = found_files["c"] + found_files["cpp"]

    # Поиск всех динамических библиотек:
    all_libs = find_dynamic_libs()

    # Генерация флагов сборки:
    defines         = [f"-D{d}" for d in Vars.defines if d]
    includes        = [f"-I{i}" for i in Vars.includes if i]
    libraries_flags = [f"-L{p}" for p in Vars.libraries if p]
    libnames_flags  = [f"-l{n}" for n in Vars.libnames if n]
    strip_flag      = ("-Wl,-x" if sys.platform == "darwin" else "-s") if Vars.strip else ""
    disconsole_flag = "-mwindows" if Vars.con_dis and sys.platform == "win32" else ""

    # Флаги компиляции и линковки:
    compile_flags    = [Vars.optimiz] + defines + includes + Vars.warnings + Vars.comp_fg
    linker_flags     = [f for f in [strip_flag, disconsole_flag] if f] + Vars.link_fg
    linker_lib_flags = libraries_flags + libnames_flags

    # Собираем программу:
    try:
        # Первая часть вывода информации:
        start_time = time.time()
        log(f"{' BUILDING THE PROJECT ':-^80}")
        log(f"Compile flags: \"{' '.join([f for f in compile_flags if f])}\"")
        log(f"Linker flags: \"{' '.join([f for f in linker_flags+linker_lib_flags if f])}\"")
        if all_libs: log(f"Dynamic libs ({len(all_libs)}): [{', '.join([os.path.basename(f) for f in all_libs])}]")
        if Vars.m_threads: log(f"Using {Vars.cpu_threads} cpu threads.")

        # Получаем новый metadata (+ анализируем зависимости исходников):
        metadata_new = get_new_metadata(all_files)

        # Проверяем папки сборки:
        check_dirs()

        # Проверяем конфиги:
        check_configs(metadata, metadata_new)

        # Обрабатываем файлы:
        process_files(metadata, metadata_new)

        # Вторая часть вывода информации:
        if Vars.build_clear: log(f"[!] Used clear flag for reset build.")
        if Vars.build_no_meta: log(f"[!] File not found \"metadata.json\".")
        if Vars.build_cfg_edt: log(f"[!] Build config edited.")
        if Vars.build_new_os:
            old_os, new_os = Vars.build_new_os_info["old"], Vars.build_new_os_info["new"]
            log(f"[!] Build on a new system. Previous OS: {old_os}, Current OS: {new_os}")
        if Vars.reset_build: log(f"Recompiling all files (build reseted).")
        log(f"{' '*20}{'~<[PROCESS]>~':-^40}{' '*20}")

        # Пересоздать иконку для системы виндовс:
        recreate_windows_icon()

        # Компиляция исходников:
        Vars.to_compile = len(Vars.total_src)
        log_compile_thread = Thread(target=compile_log_thread, daemon=True)
        log_compile_thread.start()
        if Vars.m_threads:
            # Создаём отдельные потоки для компиляции:
            with ThreadPoolExecutor(max_workers=Vars.cpu_threads) as exc:
                exc.map(partial(compile_file, compile_flags=compile_flags), Vars.total_src)
        else:
            # Просто компилируем поочередно:
            for path in Vars.total_src:
                compile_file(path, compile_flags)
        Vars.compile_done = True
        log_compile_thread.join()  # Ждём завершение вывода логов компиляции.

        # Линкуем все объектные файлы в один исполняемый:
        link_files(linker_flags, linker_lib_flags)

        # Копируем необходимые библиотеки в папку бинара:
        if all_libs: copy_libs(all_libs)
        log(f"Build finished: {time.time()-start_time:.2f}s")

        # Сохраняем мета-данные в случае удачной сборки:
        save_metadata("tools/metadata.json", metadata_new)

        log(f"{'-'*80}")
    except Exception as error:
        log_error(f"{error}")


# Если этот скрипт запускают:
if __name__ == "__main__":
    main()
