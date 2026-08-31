@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
cmake --build build 2>&1 > "E:\Recompilador Super Nintendo\build_log.txt"
echo BUILD_EXIT_CODE=%ERRORLEVEL% >> "E:\Recompilador Super Nintendo\build_log.txt"
echo BUILD_DONE >> "E:\Recompilador Super Nintendo\build_log.txt"
