#
# build.py - Скрипт системы сборки этого фреймворка.
#


# Импортируем:
import os
import sys
import glob
import json
import time
import shutil


# Глобальные переменные:
bin_dirname = "bin"
obj_dirname = "obj"


# Функция для поиска всех файлов определённого формата:
def find_files(path: str, form: str) -> list:
    return [p.replace("\\", "/") for p in glob.glob(os.path.join(path, f"**/*.{form}"), recursive=True)]


# Генерируем уникальные имена объектных файлов с учётом пути:
def generate_obj_filename(path: str, build_dir: str) -> str:
    return os.path.join(build_dir, obj_dirname, os.path.splitext(path)[0].replace("/", "_").replace("\\", "_") + ".o")


# Ищем необходимые динамические библиотеки:
def find_dynamic_libs(libs_dirs: str, libnames: list) -> list:
    if sys.platform.startswith("win32") or sys.platform.startswith("cygwin"): exts = ["dll"]
    elif sys.platform.startswith("linux"): exts = ["so"]
    elif sys.platform.startswith("darwin"): exts = ["dylib", "framework"]
    else: exts = ["dll", "so", "dylib"]
    libnames_clean, result = [name.lower().lstrip("lib") for name in libnames], []
    for libdir in libs_dirs:
        for ext in exts:
            for full_path in find_files(libdir, ext):
                name = os.path.basename(full_path).lower()
                if name.endswith(f".{ext}"): name = name[:-(len(ext)+1)]
                if name.startswith("lib"): name = name[3:]
                if name in libnames_clean: result.append(full_path)
    return result


# Проверяем файлы и прочее:
def check_files(metadata: dict, metadata_new: dict, build_dir: str) -> list:
    m_os, m_os_new = metadata["os"] if "os" in metadata else None, metadata_new["os"] if "os" in metadata_new else None
    del metadata["os"]; del metadata_new["os"]  # Удаляем из метаданных.

    # Находим удаленные файлы, измененные и новые файлы:
    meta_changed, meta_added, meta_removed = [], [], []
    for path, mtime in metadata_new.items():
        if path not in metadata: meta_added.append(path)
        elif metadata[path] != mtime: meta_changed.append(path)
    for path in metadata:
        if path not in metadata_new: meta_removed.append(path)
    total_objs = meta_added+meta_changed

    # Создаём папку объектов если её нет:
    if not os.path.isdir(os.path.join(build_dir, obj_dirname)): os.mkdir(os.path.join(build_dir, obj_dirname))

    # Создаём папку бинара:
    if os.path.isdir(os.path.join(build_dir, bin_dirname)): shutil.rmtree(os.path.join(build_dir, bin_dirname))
    os.mkdir(os.path.join(build_dir, bin_dirname))

    # Удаляем все объектные файлы, если прошлая сборка была сделана на другой системе:
    if m_os != m_os_new:
        # print(f"[!] Build on a new system. Previous OS: {m_os}, Current OS: {m_os_new}")
        for file in os.listdir(os.path.join(build_dir, obj_dirname)):
            if file.endswith(".o"): os.remove(os.path.join(build_dir, obj_dirname, file))

    # Удаление объектных файлов по списку удалённых исходников:
    for path in meta_removed:
        obj_path = os.path.splitext(path)[0] + ".o"
        if os.path.exists(obj_path): os.remove(obj_path)

    # Список всех целевых .o файлов из актуальных .c файлов:
    obj_files = {
        generate_obj_filename(path, build_dir): path
        for path in metadata_new
    }

    # Удаление лишних .o файлов которых не должно быть:
    for obj in [os.path.join(build_dir, obj_dirname, f)
                for f in os.listdir(os.path.join(build_dir, obj_dirname))
                if f.endswith(".o") and f != "icon.o"]:
        if obj not in obj_files and os.path.isfile(obj): os.remove(obj)

    # Проверка на отсутствующие .o файлы:
    for obj_path, src_path in obj_files.items():
        if src_path not in total_objs and not os.path.isfile(obj_path):
            total_objs.append(src_path)
    return total_objs


# Основная функция:
def main() -> None:
    # Читаем мета-данные сборки:
    if not os.path.isfile("metadata.json"):
        with open("metadata.json", "w+", encoding="utf-8") as f: json.dump({"os": sys.platform}, f, indent=4)
    with open("metadata.json", "r+", encoding="utf-8") as f: metadata = json.load(f)

    # Читаем конфигурационный файл сборки:
    with open("../config.json", "r+", encoding="utf-8") as f: config = json.load(f)

    # Преобразование данных конфигурации в переменные:
    program_name = config["program-name"]
    program_icon = config["program-icon"]
    source_dir   = config["source-dir"]
    build_dir    = config["build-dir"]
    compiler     = config["compiler"]
    std_type     = config["std"]
    strip_enable = config["strip"]
    includes     = config["includes"]
    libraries    = config["libraries"]
    libnames     = config["libnames"]
    optimizer    = config["optimization"]
    noconsole    = config["console-disabled"]
    warnings     = config["warnings"]
    comp_flags   = config["compile-flags"]
    link_flags   = config["linker-flags"]

    # Поиск всех си файлов:
    os.chdir("../../")
    cfiles = []
    if not os.path.isdir(source_dir):
        print(f"\nBuild: Error: Directory \"{source_dir}\" not found.")
        sys.exit()
    for file in find_files(source_dir, "c"): cfiles.append(f"\"{file}\"")

    # Если передан флаг о очистке объектных файлов:
    obj_dir_path = os.path.join(build_dir, obj_dirname)
    if any(arg in ["-c", "-clear"] for arg in sys.argv[1:]) and os.path.isdir(obj_dir_path):
        shutil.rmtree(obj_dir_path); os.mkdir(obj_dir_path)

    # Поиск всех динамических библиотек:
    all_libs = find_dynamic_libs(libraries, libnames)

    # Получаем новый metadata:
    metadata_new = {"os": sys.platform} | {file[1:-1]: os.path.getmtime(file[1:-1]) for file in cfiles}

    # Сохраняем новый metadata:
    with open(os.path.join(build_dir, "tools/metadata.json"), "w+", encoding="utf-8") as f:
        json.dump(metadata_new, f, indent=4)

    # Проверяем файлы и прочее:
    total_objs = check_files(metadata, metadata_new, build_dir)

    # Генерация флагов сборки:
    # Флаги компиляции:
    includes = " ".join([f"-I\"{inc}\"" for inc in includes])
    compile_flags = f"{compiler} -std={std_type} {optimizer} {includes} " \
                    f" {' '.join(warnings)} {' '.join(comp_flags)}"  # Флаги компиляции.

    # Флаги линковки:
    libraries_flags = " ".join([f"-L\"{path}\"" for path in libraries]) if libraries else ""
    libnames_flags  = " ".join([f"-l\"{name}\"" for name in libnames]) if libnames else ""
    strip_flag = ("-Wl,-x" if sys.platform == "darwin" else "-s") if strip_enable else ""
    noconsole_flag = "-mwindows" if noconsole and sys.platform == "win32" else ""
    linker_flags  = f"{compiler} {strip_flag} {noconsole_flag} {' '.join(link_flags)}"  # Флаги линковки.

    # Собираем программу:
    start_time = time.time()
    print(f"{' COMPILATION PROJECT ':-^80}")
    print(f"Compile flags: \"{' '.join(compile_flags.split())}\"")
    print(f"Linker flags: \"{' '.join((linker_flags+' '+libraries_flags+' '+libnames_flags).split())}\"")
    print(f"Dynamic libs: [{', '.join([os.path.basename(f) for f in all_libs])}]") if all_libs else None
    print(f"Compile: [{', '.join([os.path.basename(f) for f in total_objs])}]") if total_objs else None
    print(f"{' '*20}{'~<[OUTPUT]>~':-^40}{' '*20}")

    # Удаляем файлы иконок из папки объектов:
    if os.path.isdir(os.path.join(build_dir, obj_dirname)):
        [os.remove(os.path.join(build_dir, obj_dirname, f))
         for f in os.listdir(os.path.join(build_dir, obj_dirname))
         if f.endswith(".ico")]

    # Создаём .o файл иконки если это Windows система:
    icon_rc_path = os.path.join(build_dir, obj_dirname, "icon.rc")
    if sys.platform == "win32" and program_icon is not None and os.path.isfile(program_icon):
        with open(icon_rc_path, "w+", encoding="utf-8") as f:
            f.write(f"ResurceName ICON \"{os.path.basename(program_icon)}\"")
        shutil.copy(f"{program_icon}", os.path.join(build_dir, obj_dirname))
        os.system(f"windres {icon_rc_path} {os.path.join(build_dir, obj_dirname, 'icon.o')}")
    # Если не Windows или null иконка, то удаляем объект иконки:
    elif os.path.isfile(os.path.join(build_dir, obj_dirname, "icon.o")):
        os.remove(os.path.join(build_dir, obj_dirname, "icon.o"))
    if os.path.isfile(icon_rc_path): os.remove(icon_rc_path)

    # Компиляция новых и изменённых исходников:
    for path in total_objs:
        print(f"> {path}")
        obj_path = generate_obj_filename(path, build_dir)
        os.system(f"{compile_flags} -c {path} -o {obj_path}")

    # Линкуем все объектные файлы в один:
    o_command = f"\"{os.path.join(build_dir, bin_dirname)}/{program_name}\""
    objfls = " ".join([f"\"{f}\"" for f in glob.glob(f"{os.path.join(build_dir, obj_dirname)}/**/*.o", recursive=True)])
    os.system(f"{linker_flags} {objfls} {libraries_flags} {libnames_flags} -o {o_command}")
    print(f"{'-'*80}")

    # Копируем необходимые библиотеки в папку бинара:
    if all_libs:
        print("Copying dynamic libraries... ", end="")
        for path in all_libs:
            if os.path.isfile(path): shutil.copy2(path, os.path.join(build_dir, bin_dirname))
        print("Done!")
    print(f"Build time: {round(time.time()-start_time, 4)}s")

# Если этот скрипт запускают:
if __name__ == "__main__":
    main()
