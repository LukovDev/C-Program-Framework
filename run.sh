#!/bin/bash

# Переход в директорию с инструментами:
cd build/tools/

# Запуск скрипта сборки:
python3 run.py "$@"

# Удаляем папку кэша питона:
rm -rf build/tools/__pycache__
