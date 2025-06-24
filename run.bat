@echo off

cd .\build\tools\
python run.py %*
rmdir /s /q "__pycache__"
cd ..\..\
