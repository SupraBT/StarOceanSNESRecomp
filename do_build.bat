@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
cmake --build build --parallel --config Release 2>&1 > "E:\Recompilador Super Nintendo\build_result.txt"
echo BUILD_DONE > "E:\Recompilador Super Nintendo\build_done.txt"
