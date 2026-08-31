@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "F:\Recompilador Super Nintendo\StarOceanTest2"
cmake -S cosim -B build-cosim -G Ninja -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl "-DSDL2_DIR=F:/Recompilador Super Nintendo/StarOceanTest2/deps/SDL2-2.30.5/x86_64-w64-mingw32/lib/cmake/SDL2" 2>&1 | findstr /i "error" | head -5
echo CONFIGURE_DONE=%ERRORLEVEL%
cmake --build build-cosim 2>&1 | findstr /i "error" | head -20
echo BUILD_EXIT=%ERRORLEVEL%
