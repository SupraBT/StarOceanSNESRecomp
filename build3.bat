@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2"
ninja -C build 2>&1
echo BUILD_EXIT=%ERRORLEVEL%
