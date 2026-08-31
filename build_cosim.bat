@echo off
rem Configure + build the co-simulation harness (so_cosim + so_cosim_ref).
rem DEV/DIAGNOSTICS ONLY - never part of the Release build.
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "%~dp0"
if not exist build-cosim\CMakeCache.txt (
  cmake -S cosim -B build-cosim -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo ^
    -DCMAKE_MAKE_PROGRAM="C:\Program Files\CMake\bin\ninja.exe" ^
    -DSDL2_DIR="E:\Recompilador Super Nintendo\StarOceanTest2\deps\SDL2-2.30.5\x86_64-w64-mingw32\lib\cmake\SDL2"
)
ninja -C build-cosim %*
