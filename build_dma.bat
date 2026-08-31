@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
cmake --build build --config Release --parallel > build_output.txt 2>&1
echo BUILD_DONE >> build_output.txt
