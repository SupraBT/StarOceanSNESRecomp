@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
echo [%TIME%] BUILD STARTING (parallel) > "E:\Recompilador Super Nintendo\build_log.txt"
cmake --build build --parallel 2>> "E:\Recompilador Super Nintendo\build_log.txt"
echo [%TIME%] BUILD_EXIT=%ERRORLEVEL% >> "E:\Recompilador Super Nintendo\build_log.txt"
if %ERRORLEVEL% EQU 0 (
    echo [%TIME%] RUNNING EXE... >> "E:\Recompilador Super Nintendo\build_log.txt"
    .\build\starocean.exe >> "E:\Recompilador Super Nintendo\build_log.txt" 2>&1
    echo [%TIME%] EXE_DONE >> "E:\Recompilador Super Nintendo\build_log.txt"
) else (
    echo [%TIME%] BUILD FAILED >> "E:\Recompilador Super Nintendo\build_log.txt"
)
