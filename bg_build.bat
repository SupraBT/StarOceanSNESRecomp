@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
echo STARTING BUILD...
ninja -C build 2>build_err.txt
echo BUILD_EXIT=%ERRORLEVEL% > build_status.txt
type build_err.txt
echo ---STATUS---
type build_status.txt
