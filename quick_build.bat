@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "E:\Recompilador Super Nintendo\StarOceanTest2\build"
MSBuild.exe StarOcean.vcxproj /p:Configuration=Release /p:Platform=x64 /m /nologo /t:Build > "E:\Recompilador Super Nintendo\msbuild_log.txt" 2>&1
echo BUILD_COMPLETE > "E:\Recompilador Super Nintendo\build_flag.txt"
