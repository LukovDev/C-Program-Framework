#
# build.py - Скрипт системы сборки.
#
# Этот скрипт должен быть запущен в каталоге "<build-dir>/tools/"
#
# [ C-Program-Framework BuildSystem for PC <v2.0> ]
#


# Импортируем:
import os
import sys
import glob
import json
import time
import shutil
import subprocess
from threading import Thread


# Класс глобальных переменных:
class Vars:
    # Конфигурация:
    prog_name: str  = "Undefined"
    prog_icon: str  = None      # None | str.
    src_dp:    list = ["str/"]  # src dirs (paths).
    build_dn:  str  = "build/"  # build dir name.
    bin_dn:    str  = "bin"     # bin dir name.
    obj_dn:    str  = "obj"     # obj dir name.
    build_lg:  bool = True      # Build logging.
    strip:     bool = False     # Strip.
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
    total_src: list = []  # Список путей до исходников для компиляции.

    # Инициализировать переменные:
    @staticmethod
    def init_vars(config_path: str) -> None:
        with open(config_path, "r+", encoding="utf-8") as f:
            config = json.load(f)

        # Заполняем поля данными:
        Vars.prog_name = config["program-name"]
        Vars.prog_icon = config["program-icon"]
        Vars.src_dp    = config["source-dirs"]
        Vars.build_dn  = config["build-dir"]
        Vars.bin_dn    = config["bin-dir-name"]
        Vars.obj_dn    = config["obj-dir-name"]
        Vars.build_lg  = config["build-logging"]
        Vars.strip     = config["strip"]
        Vars.con_dis   = config["console-disabled"]
        Vars.defines   = config["defines"]
        Vars.includes  = config["includes"]
        Vars.libraries = config["libraries"]
        Vars.libnames  = config["libnames"]
        Vars.optimiz   = config["optimization"]
        Vars.std_c     = config["std-c"]
        Vars.std_cpp   = config["std-cpp"]
        Vars.comp_c    = config["compiler-c"]
        Vars.comp_cpp  = config["compiler-cpp"]
        Vars.linker    = config["linker"]
        Vars.warnings  = config["warnings"]
        Vars.comp_fg   = config["compile-flags"]
        Vars.link_fg   = config["linker-flags"]


# Вывести лог отладки сборки:
def log(msg: str) -> None:
    if not Vars.build_lg: return
    print(msg)


# Вывести лог отладки ошибки:
def log_error(msg: str) -> None:
    # if not Vars.build_lg: return
    print(f"BuildSystem: [/!\\] Error: {msg}")
    os._exit(1)  # Жёстко останавливаем сборку.


# Функция для поиска всех файлов определённого формата:
def find_files(path: str, form: str) -> list:
    return [p.replace("\\", "/") for p in glob.glob(os.path.join(path, f"**/*.{form}"), recursive=True)]


# Генерируем уникальные имена объектных файлов с учётом пути:
def generate_obj_filename(path: str) -> str:
    norm = path.replace("/", "_").replace("\\", "_")
    return os.path.join(Vars.build_dn, Vars.obj_dn, norm + ".o")


# Читаем мета-данные:
def load_metadata(file_path: str) -> dict:
    if not os.path.isfile(file_path):  # "<build-dir>/tools/file_path".
        with open(file_path, "w+", encoding="utf-8") as f:
            json.dump({
                "metainfo": {
                    "os": sys.platform,
                }, "files": {}
            }, f, indent=4)
    with open(file_path, "r+", encoding="utf-8") as f:
        metadata = json.load(f)
    return metadata


# Сохраняем мета-данные:
def save_metadata(file_path: str, data: dict) -> None:
    with open(os.path.join(Vars.build_dn, file_path), "w+", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# Поиск всех .c/.cpp файлов:
def fild_all_c_cpp_files() -> dict:
    found_files = {"c": [], "cpp": []}  # Найденные файлы.

    # Проходимся по всем папкам-исходникам:
    for src_dir in Vars.src_dp:
        if not os.path.isdir(src_dir):
            log_error(f"\nDirectory \"{src_dir}\" not found.")
            sys.exit()
        # Ищем и сохраняем пути до найденных файлов:
        for f in find_files(src_dir, "c"):   found_files["c"].append(f"\"{f}\"")
        for f in find_files(src_dir, "cpp"): found_files["cpp"].append(f"\"{f}\"")
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


# Обрабатываем файлы:
def process_files(metadata: dict, metadata_new: dict) -> None:
    # Получаем поле метаинформации и файлов из метаданных:
    metainfo, files = metadata["metainfo"], metadata["files"]
    metainfo_new, files_new = metadata_new["metainfo"], metadata_new["files"]

    # Получаем имена операционных систем на которых производились сборки:
    m_os, m_os_new = metainfo["os"] if "os" in metainfo else None, metainfo_new["os"] if "os" in metainfo_new else None

    # Находим измененные, новые и удаленные файлы:
    meta_changed, meta_added, meta_removed = [], [], []
    for path, mtime in files_new.items():
        if path not in files: meta_added.append(path)
        elif files[path] != mtime: meta_changed.append(path)
    for path in files:
        if path not in files_new: meta_removed.append(path)
    total_src = meta_added+meta_changed

    # Удаляем все объектные файлы, если прошлая сборка была сделана на другой системе:
    obj_full_dn = os.path.join(Vars.build_dn, Vars.obj_dn)
    if m_os != m_os_new:
        log(f"BuildSystem: [/!\\] Build on a new system. Previous OS: {m_os}, Current OS: {m_os_new}")
        for file in os.listdir(obj_full_dn):
            if file.endswith(".o"): os.remove(os.path.join(obj_full_dn, file))

    # Удаление объектных файлов по списку удалённых исходников:
    for path in meta_removed:
        obj_path = os.path.splitext(path)[0] + ".o"
        if os.path.exists(obj_path): os.remove(obj_path)

    # Список всех целевых .o файлов из актуальных .c/.cpp файлов:
    obj_files = {  # [(Обработанное имя исходника в .o формате):(Полный путь к исходнику)].
        generate_obj_filename(path): path
        for path in files_new
    }

    # Удаление .o файлов, исходников которых больше нет:
    # Пометка: Проверяем существующие .o файлы (с обработанным именем) на отсутствие в obj_files.
    for obj in [os.path.join(obj_full_dn, f)
                for f in os.listdir(obj_full_dn)
                if f.endswith(".o") and f != "icon.o"]:
        if obj not in obj_files and os.path.isfile(obj): os.remove(obj)

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
                f.write(f"ResurceName ICON \"{os.path.basename(Vars.prog_icon)}\"")
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
        log(f"[{' C ' if comp_flag == Vars.comp_c else 'C++'}] > {file_path}")

        # Компилируем:
        args = [comp_flag, std_flag] + compile_flags + ["-c", file_path, "-o", generate_obj_filename(file_path)]
        subprocess.run([a for a in args if a], text=True, check=True)
    except subprocess.CalledProcessError as error:
        log_error(f"Compile returned status: {error.returncode}")


# Линковать объектные файлы в один исполняемый файл:
def link_files(linker_flags: list, linker_lib_flags: list) -> None:
    try:
        obj_full_dn = os.path.join(Vars.build_dn, Vars.obj_dn)
        prog_full_path = os.path.join(Vars.build_dn, Vars.bin_dn, Vars.prog_name)
        obj_files = glob.glob(f"{obj_full_dn}/**/*.o", recursive=True)

        # Линкуем:
        args = [Vars.linker] + linker_flags + obj_files + linker_lib_flags + ["-o", prog_full_path]
        subprocess.run([a for a in args if a], check=True)
    except subprocess.CalledProcessError as error:
        log_error(f"Linker returned status: {error.returncode}")
    except Exception as error:
        log_error(f"Linker: {error}")


# Копируем необходимые библиотеки в папку бинара:
def copy_libs(all_libs: list) -> None:
    try:
        log("Copying dynamic libraries... ", end="")
        for path in all_libs:
            if os.path.isfile(path): shutil.copy2(path, os.path.join(Vars.build_dn, Vars.bin_dn))
        log("Done!")
    except Exception as error:
        log_error(f"Copying libs: {error}")


# Основная функция:
def main() -> None:
    Vars.init_vars("../config.json")  # Инициализируем переменные.
    metadata = load_metadata("metadata.json")  # Читаем мета-данные.
    obj_full_dn = os.path.join(Vars.build_dn, Vars.obj_dn)

    os.chdir("../../")  # Переходим в корневую директорию из "<build-dir>/tools/".

    # Если передан флаг об очистке объектных файлов:
    if any(arg in ["-c", "-clear"] for arg in sys.argv[1:]) and os.path.isdir(obj_full_dn):
        shutil.rmtree(obj_full_dn)
        os.mkdir(obj_full_dn)

    # Поиск всех .c/.cpp файлов:
    found_files = fild_all_c_cpp_files()
    all_files = found_files["c"] + found_files["cpp"]

    # Поиск всех динамических библиотек:
    all_libs = find_dynamic_libs()

    # Получаем новый metadata:
    metadata_new = {
        "metainfo": {
            "os": sys.platform,
        }, "files": {
            file[1:-1]: os.path.getmtime(file[1:-1])
            for file in all_files
        }
    }

    # Проверяем папки сборки:
    check_dirs()

    # Обрабатываем файлы:
    process_files(metadata, metadata_new)

    # Генерация флагов сборки:
    defines         = [f"-D{d}" for d in Vars.defines]
    includes        = [f"-I{i}" for i in Vars.includes]
    libraries_flags = [f"-L{p}" for p in Vars.libraries]
    libnames_flags  = [f"-l{n}" for n in Vars.libnames]
    strip_flag      = ("-Wl,-x" if sys.platform == "darwin" else "-s") if Vars.strip else ""
    disconsole_flag = "-mwindows" if Vars.con_dis and sys.platform == "win32" else ""

    # Флаги компиляции и линковки:
    compile_flags    = [Vars.optimiz] + defines + includes + Vars.warnings + Vars.comp_fg
    linker_flags     = [f for f in [strip_flag, disconsole_flag] if f] + Vars.link_fg
    linker_lib_flags = libraries_flags + libnames_flags

    # Собираем программу:
    try:
        start_time = time.time()
        log(f"{' COMPILATION PROJECT ':-^80}")
        log(f"Compile flags: \"{' '.join([f for f in compile_flags if f])}\"")
        log(f"Linker flags: \"{' '.join([f for f in linker_flags+linker_lib_flags if f])}\"")
        log(f"Dynamic libs: [{', '.join([os.path.basename(f) for f in all_libs])}]") if all_libs else None
        log(f"To compile: [{', '.join(Vars.total_src)}]") if Vars.total_src else None
        log(f"{' '*20}{'~<[PROCESS]>~':-^40}{' '*20}")

        # Пересоздать иконку для системы виндовс:
        recreate_windows_icon()

        # Компиляция исходников:
        threads = []
        for path in Vars.total_src:
            thread = Thread(target=compile_file, args=(path, compile_flags,), daemon=True)
            threads.append(thread)
            thread.start()

        # Ждём завершение компиляции:
        for thread in threads: thread.join()

        # Линкуем все объектные файлы в один исполняемый:
        link_files(linker_flags, linker_lib_flags)
        log(f"{'-'*80}")

        # Копируем необходимые библиотеки в папку бинара:
        if all_libs: copy_libs(all_libs)
        log(f"Build time: {round(time.time()-start_time, 4)}s")

        # Сохраняем мета-данные в случае удачной сборки:
        save_metadata("tools/metadata.json", metadata_new)
    except Exception as error:
        log_error(f"{error}")


# Если этот скрипт запускают:
if __name__ == "__main__":
    main()
