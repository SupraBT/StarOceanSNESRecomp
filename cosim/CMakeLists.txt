# Headless Star Ocean co-simulation build (SNES_COSIM.md).
# DEV/DIAGNOSTICS ONLY. Builds:
#   so_cosim     - the Star Ocean recomp runtime with NO SDL window / host
#                  audio (harness_so.c replaces main.c) + the cosim engine.
#   so_cosim_ref - Track A B-side: the interp816 65816 interpreter over the
#                  runner's OWN device sources (identical struct layouts =>
#                  the cosim state hash compares directly).
#
# Configure (MSVC + Ninja, matching build-trace):
#   cmake -S cosim -B build-cosim -G Ninja
#         -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl
#         -DSDL2_DIR=$PROJECT_ROOT/deps/SDL2-2.30.5/x86_64-w64-mingw32/lib/cmake/SDL2
#   cmake --build build-cosim
# (run from a shell with vcvars64.bat loaded, like build_trace.bat does)
cmake_minimum_required(VERSION 3.16)
project(so_cosim C)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
if(WIN32)
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS _WINSOCK_DEPRECATED_NO_WARNINGS)
    add_compile_definitions(NOMINMAX)
endif()

option(SNES_COSIM_REF_ONLY
    "Configure only the game-neutral interpreter reference target" OFF)

get_filename_component(SNESRECOMP_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/../snesrecomp ABSOLUTE)
set(SO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/..")

set(SNES_COSIM ON CACHE BOOL "" FORCE)   # pull cosim.c/cosim_state.c hooks
set(SNESRECOMP_SDL_BACKEND "SDL2" CACHE STRING "Desktop SDL backend" FORCE)
include(${SNESRECOMP_ROOT}/runner/runner.cmake)

if(NOT SNES_COSIM_REF_ONLY)
file(GLOB SO_GEN CONFIGURE_DEPENDS ${SO_ROOT}/generated/*.c)
if(NOT SO_GEN)
    message(FATAL_ERROR "no generated banks at ${SO_ROOT}/generated - regen Star Ocean first")
endif()

add_executable(so_cosim
    ${SNESRECOMP_RUNNER_SOURCES}
    harness_so.c
    harness_glue.c
    ${SO_ROOT}/src/so_cpu_infra.c
    ${SO_ROOT}/src/so_rtl.c
    ${SO_ROOT}/src/so_spc_player.c
    ${SO_GEN}
)
target_include_directories(so_cosim PRIVATE
    ${SO_ROOT}/src
    ${SO_ROOT}/generated
    ${SNESRECOMP_RUNNER_INCLUDE_DIRS}
    ${SNESRECOMP_ROOT}/runner/src/desktop
)
target_compile_definitions(so_cosim PRIVATE
    SNESRECOMP_REVERSE_DEBUG=0   # raw WRAM stores; matches non-debug generated C
    SNESRECOMP_TRACE=0           # no TCP debug server; the cosim server is separate
    SDL_MAIN_HANDLED
)
# SDL2 headers are pulled in for keycode/types (keybinds.h, host_report.c) and
# host_report.c calls SDL_GetVersion() at link time. We link SDL2 (NOT
# SDL2main) and define SDL_MAIN_HANDLED so SDL does not hijack main() - the
# harness owns main and NEVER calls SDL_Init / opens a window or audio device.
find_package(SDL2 QUIET)
if(SDL2_INCLUDE_DIRS)
    target_include_directories(so_cosim PRIVATE ${SDL2_INCLUDE_DIRS})
endif()
if(TARGET SDL2::SDL2)
    target_link_libraries(so_cosim PRIVATE SDL2::SDL2)
endif()
target_link_libraries(so_cosim PRIVATE ${SNESRECOMP_RUNNER_LIBRARIES})
if(WIN32)
    target_link_libraries(so_cosim PRIVATE ws2_32)   # cosim.c TCP server
endif()
endif()

# ── Track A B-side: interp816 reference (so_cosim_ref) ───────────────────────
# Explicit source list = runner DEVICE sources + interp816 + cosim + a headless
# accurate frame driver. Deliberately EXCLUDES the recomp runtime (common_rtl.c,
# cpu_state.c, gen banks, main.c) - the ref executes via interp816, not the
# recompiled C. Same device sources as the A-side => identical struct layouts =>
# the state hash compares directly. NOTE: Star Ocean's cart uses S-DD1, so
# sdd1.c MUST be here (the SMW reference list has no sdd1.c).
set(RUNSNES ${SNESRECOMP_ROOT}/runner/src)
add_executable(so_cosim_ref
    ref_driver.c
    ${RUNSNES}/cosim.c
    ${RUNSNES}/cosim_state.c
    ${RUNSNES}/audio_trace.c
    ${RUNSNES}/crc32.c
    ${RUNSNES}/sha256.c
    ${RUNSNES}/util.c
    ${RUNSNES}/snes/apu.c
    ${RUNSNES}/snes/cart.c
    ${RUNSNES}/snes/cx4.c
    ${RUNSNES}/snes/cpu.c
    ${RUNSNES}/snes/dma.c
    ${RUNSNES}/snes/dsp.c
    ${RUNSNES}/snes/dsp1.c
    ${RUNSNES}/snes/dsp1_hle.c
    ${RUNSNES}/snes/joypad.c
    ${RUNSNES}/snes/ppu.c
    ${RUNSNES}/snes/ppu_legacy.c
    ${RUNSNES}/snes/sa1.c
    ${RUNSNES}/snes/sdd1.c
    ${RUNSNES}/snes/snes.c
    ${RUNSNES}/snes/snes_other.c
    ${RUNSNES}/snes/spc.c
    ${RUNSNES}/snes/superfx.c
    ${RUNSNES}/snes/ws_shadow.c
    ${RUNSNES}/snes/interp816.c
    ${RUNSNES}/snes/color_lut.c
)
target_include_directories(so_cosim_ref PRIVATE
    ${RUNSNES} ${RUNSNES}/snes ${SO_ROOT} ${SO_ROOT}/src
)
target_compile_definitions(so_cosim_ref PRIVATE
    SNES_COSIM SNES_COSIM_REF
    SNESRECOMP_REVERSE_DEBUG=0
    SNESRECOMP_TRACE=0 SDL_MAIN_HANDLED
)
target_link_libraries(so_cosim_ref PRIVATE ${SNESRECOMP_RUNNER_LIBRARIES})
if(WIN32)
    target_link_libraries(so_cosim_ref PRIVATE ws2_32)
endif()
