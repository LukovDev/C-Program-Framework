#
# build.py - Скрипт системы сборки этого фреймворка.
#


# Импортируем:
import os
import sys
import glob
import json
import shutil


# Функция для поиска всех файлов определённого формата:
def find_files(path: str, format: str) -> list:
    return [p.replace("\\", "/") for p in glob.glob(os.path.join(path, f"**/*.{format}"), recursive=True)]


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
def check_files(metadata: dict, metadata_new: dict) -> list:
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
    if not os.path.isdir("build/obj/"): os.mkdir("build/obj/")

    # Создаём папку бинара:
    if os.path.isdir("build/bin/"): shutil.rmtree("build/bin/")
    os.mkdir("build/bin/")

    # Удаляем все объектные файлы, если прошлая сборка была сделана на другой системе:
    if m_os != m_os_new:
        # print(f"[!] Build on a new system. Previous OS: {m_os}, Current OS: {m_os_new}")
        for file in os.listdir("build/obj/"):
            if file.endswith(".o"): os.remove(os.path.join("build/obj/", file))

    # Удаление объектных файлов по списку удалённых исходников:
    for path in meta_removed:
        obj_path = os.path.splitext(path)[0] + ".o"
        if os.path.exists(obj_path): os.remove(obj_path)

    # Список всех целевых .o файлов из актуальных .c файлов:
    obj_files = {
        os.path.join("build/obj", os.path.splitext(os.path.basename(path))[0] + ".o"): path
        for path in metadata_new
    }

    # Удаление лишних .o файлов которых не должно быть:
    for obj in [os.path.join("build/obj", f) for f in os.listdir("build/obj/") if f.endswith(".o") and f != "icon.o"]:
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
    for file in find_files("src/", "c"):
        cfiles.append(f"\"{file}\"")

    # Поиск всех динамических библиотек:
    all_libs = find_dynamic_libs(libraries, libnames)

    # Получаем новый metadata:
    metadata_new = {"os": sys.platform} | {file[1:-1]: os.path.getmtime(file[1:-1]) for file in cfiles}

    # Сохраняем новый metadata:
    with open("build/tools/metadata.json", "w+", encoding="utf-8") as f: json.dump(metadata_new, f, indent=4)

    # Проверяем файлы и прочее:
    total_objs = check_files(metadata, metadata_new)

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
    print(f"{' COMPILATION PROJECT ':-^80}")
    print(f"Compile flags: \"{' '.join(compile_flags.split())}\"")
    print(f"Linker flags: \"{' '.join((linker_flags+' '+libraries_flags+' '+libnames_flags).split())}\"")
    print(f"Dynamic libs: [{', '.join([os.path.basename(f) for f in all_libs])}]") if all_libs else None
    print(f"Compile: [{', '.join([os.path.basename(f) for f in total_objs])}]") if total_objs else None
    print(f"{' '*20}{'~<[OUTPUT]>~':-^40}{' '*20}")

    # Удаляем файлы иконок из папки объектов:
    if os.path.isdir("build/obj/"):
        [os.remove(os.path.join("build/obj", f)) for f in os.listdir("build/obj/") if f.endswith(".ico")]

    # Создаём .o файл иконки если это Windows система:
    if sys.platform == "win32" and program_icon is not None and os.path.isfile(program_icon):
        with open(f"build/obj/icon.rc", "w+", encoding="utf-8") as f:
            f.write(f"ResurceName ICON \"{os.path.basename(program_icon)}\"")
        shutil.copy(f"{program_icon}", f"build/obj/")
        os.system(f"windres build/obj/icon.rc build/obj/icon.o")
    elif os.path.isfile("build/obj/icon.o"):  # Если не Windows или null иконка, то удаляем объект иконки.
        if os.path.isfile("build/obj/icon.rc"):
            os.remove("build/obj/icon.rc")
        os.remove("build/obj/icon.o")

    # Компиляция новых и изменённых исходников:
    for path in total_objs:
        print(f"> {path}")
        obj_path = os.path.join("build/obj/", os.path.splitext(os.path.basename(path))[0]+".o")
        os.system(f"{compile_flags} -c {path} -o {obj_path}")

    # Линкуем все объектные файлы в один:
    obj_files = " ".join([f"\"{f}\"" for f in glob.glob("build/obj/**/*.o", recursive=True)])
    os.system(f"{linker_flags} {obj_files} {libraries_flags} {libnames_flags} -o \"build/bin/{program_name}\"")
    print(f"{'-'*80}")

    # Копируем необходимые библиотеки в папку бинара:
    if all_libs:
        print("Copying dynamic libraries... ", end="")
        for path in all_libs:
            if os.path.isfile(path): shutil.copy2(path, "build/bin/")
        print("Done!")

# Если этот скрипт запускают:
if __name__ == "__main__":
    main()
