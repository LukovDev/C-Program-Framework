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
def find_files(format: str) -> list:
    return glob.glob(f"**/*.{format}", recursive=True)


# Проверяем файлы и прочее:
def check_files(cfiles: list, metadata: dict, metadata_new: dict) -> list:
    # Находим удаленные файлы, измененные и новые файлы:
    meta_changed, meta_added, meta_removed = [], [], []
    for path, mtime in metadata_new.items():
        if path not in metadata: meta_added.append(path)
        elif metadata[path] != mtime: meta_changed.append(path)
    for path in metadata:
        if path not in metadata_new: meta_removed.append(path)
    total_objs = meta_added+meta_changed

    # Создаём временную папку для сборки, если её нет:
    if not os.path.isdir("build/tmp/"): os.mkdir("build/tmp/")

    # Создаём папку вывода:
    if os.path.isdir("build/out/"): shutil.rmtree("build/out/")
    os.mkdir("build/out/")

    # Удаление объектных файлов по списку удалённых исходников:
    for path in meta_removed:
        obj_path = os.path.splitext(path)[0] + ".o"
        if os.path.exists(obj_path): os.remove(obj_path)

    # Список всех целевых .o файлов из актуальных .c файлов:
    obj_files = {
        os.path.join("build/tmp", os.path.splitext(os.path.basename(path))[0] + ".o"): path
        for path in metadata_new
    }

    # Удаление лишних .o файлов которых не должно быть:
    for obj in [os.path.join("build/tmp", f) for f in os.listdir("build/tmp/") if f.endswith(".o") and f != "icon.o"]:
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
        with open("metadata.json", "w+", encoding="utf-8") as f: json.dump({}, f, indent=4)
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
    optimizer    = config["optimization"]
    noconsole    = config["console-disabled"]
    warnings     = config["warnings"]
    cflags       = config["cflags"]

    # Поиск всех си файлов:
    os.chdir("../../src/")
    cfiles = []
    for file in find_files("c"):
        cfiles.append(f"\"{os.path.join('src/', file)}\"")
    os.chdir("../")

    # Получаем новый metadata:
    metadata_new = {file[1:-1]: os.path.getmtime(file[1:-1]) for file in cfiles}

    # Сохраняем новый metadata:
    with open("build/tools/metadata.json", "w+", encoding="utf-8") as f: json.dump(metadata_new, f, indent=4)

    # Проверяем файлы и прочее:
    total_objs = check_files(cfiles, metadata, metadata_new)

    # Генерация флагов компиляции:
    includes = " ".join([f"-I\"{inc}\"" for inc in includes])
    compile_flags = f"{compiler} -std={std_type} {optimizer} {includes} " \
                    f" {' '.join(warnings)} {' '.join(cflags)}"  # Флаги компиляции.

    strip_flag = ("-Wl,-x" if sys.platform == "darwin" else "-s") if strip_enable else ""
    noconsole_flag = "-mwindows" if noconsole and sys.platform == "win32" else ""
    linker_flags  = f"{compiler} {strip_flag} {noconsole_flag}"  # Флаги линковки.

    # Собираем программу:
    print(f"{' COMPILATION PROJECT ':-^80}")
    print(f"Command: \"{' '.join(compile_flags.split())}\"")
    print(f"Compile: [{', '.join([os.path.basename(file) for file in total_objs])}]") if total_objs else None
    print(f"{' '*20}{'~<[OUTPUT]>~':-^40}{' '*20}")

    # Удаляем файлы иконок из временной папки:
    if os.path.isdir("build/tmp/"):
        [os.remove(os.path.join("build/tmp", f)) for f in os.listdir("build/tmp/") if f.endswith(".ico")]

    # Создаём .o файл иконки если это Windows система:
    if sys.platform == "win32" and program_icon is not None and os.path.isfile(program_icon):
        with open(f"build/tmp/icon.rc", "w+", encoding="utf-8") as f:
            f.write(f"ResurceName ICON \"{os.path.basename(program_icon)}\"")
        shutil.copy(f"{program_icon}", f"build/tmp/")
        os.system(f"windres build/tmp/icon.rc build/tmp/icon.o")
    elif os.path.isfile("build/tmp/icon.o"):  # Если не Windows или null иконка, то удаляем объект иконки.
        if os.path.isfile("build/tmp/icon.rc"):
            os.remove("build/tmp/icon.rc")
        os.remove("build/tmp/icon.o")

    # Комpиляция новых и изменённых исходников:
    for path in total_objs:
        print(f"> {path}")
        obj_path = os.path.join("build/tmp/", os.path.splitext(os.path.basename(path))[0]+".o")
        os.system(f"{compile_flags} -c {path} -o {obj_path}")

    # Линкуем все объектные файлы в один:
    obj_files = " ".join([f"\"{f}\"" for f in glob.glob("build/tmp/**/*.o", recursive=True)])
    os.system(f"{linker_flags} {obj_files} -o \"build/out/{program_name}\"")
    print(f"{'-'*80}")


# Если этот скрипт запускают:
if __name__ == "__main__":
    main()
