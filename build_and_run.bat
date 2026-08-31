@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
ninja -C build
if %ERRORLEVEL% NEQ 0 (
    echo BUILD FAILED
    exit /b 1
)
echo Build OK, running game...
cd build
star_ocean.exe > debug_log.txt 2>&1
