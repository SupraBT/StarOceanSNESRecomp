@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "F:\Recompilador Super Nintendo\StarOceanTest2"
cmake -S cosim -B build-cosim-release -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl "-DCMAKE_C_FLAGS=-DSNESRECOMP_INTERP_PROFILE" "-DSDL2_DIR=F:/Recompilador Super Nintendo/StarOceanTest2/deps/SDL2-2.30.5/x86_64-w64-mingw32/lib/cmake/SDL2" 2>&1 | findstr /i "error" | head -5
echo CONFIGURE_DONE=%ERRORLEVEL%
cmake --build build-cosim-release 2>&1 | findstr /i "error" | findstr /v "C4996" | head -20
echo BUILD_EXIT=%ERRORLEVEL%