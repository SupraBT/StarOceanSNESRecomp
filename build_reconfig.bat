@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
cmake -B build -G Ninja
cmake --build build --config Release --parallel
