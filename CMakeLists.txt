cmake_minimum_required(VERSION 3.20)
project(Star_Ocean_JapanRecomp C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Platform detection
if(WIN32)
    add_compile_definitions(_CRT_SECURE_NO_WARNINGS _WINSOCK_DEPRECATED_NO_WARNINGS)
    add_compile_definitions(NOMINMAX)
endif()

# SNESRecomp framework root
set(SNESRECOMP_ROOT "${CMAKE_SOURCE_DIR}/snesrecomp" CACHE PATH "Path to SNESRecomp")
set(SNESRECOMP_SDL_BACKEND SDL2 CACHE STRING "Desktop SDL backend")
include(${SNESRECOMP_ROOT}/runner/runner.cmake)

# Enable launcher (built-in console launcher)
option(SNESRECOMP_ENABLE_LAUNCHER "Build with SNES launcher" ON)
if(SNESRECOMP_ENABLE_LAUNCHER)
    add_compile_definitions(SNES_LAUNCHER=1)
    message(STATUS "SNES launcher: enabled (built-in console launcher)")
else()
    add_compile_definitions(SNES_LAUNCHER=0)
endif()

# Enable mods (optional)
option(SNESRECOMP_ENABLE_MODS "Enable mod support" OFF)
if(SNESRECOMP_ENABLE_MODS)
    add_compile_definitions(SNESRECOMP_ENABLE_MODS=1)
endif()

# Enable trace/debug (optional)
option(SNESRECOMP_ENABLE_TRACE "Enable TCP debug server" OFF)
if(SNESRECOMP_ENABLE_TRACE)
    add_compile_definitions(SNESRECOMP_TRACE=1)
endif()

set(STAROCEAN_GENERATED_DIR "${CMAKE_CURRENT_SOURCE_DIR}/generated"
    CACHE PATH "Directory containing generated Star Ocean AOT C sources")

# Clean production build: compile out all dev monitoring (pad markers,
# phase/slow/exit loggers, C2/C086 watches, SPCFF/spcffx logs, APU port diag,
# IBRWATCH/dtrace/xce traces). Default OFF keeps the instrumented dev build.
option(SNESRECOMP_CLEAN_BUILD "Compile out dev monitoring instrumentation" OFF)
if(SNESRECOMP_CLEAN_BUILD)
    add_compile_definitions(SNESRECOMP_CLEAN_BUILD=1)
    message(STATUS "Clean production build: dev monitors compiled out")
else()
    message(STATUS "Dev build: monitoring instrumentation enabled (env-gated)")
endif()

# Generated sources from snesrecomp
file(GLOB GENERATED_SOURCES CONFIGURE_DEPENDS
    "${STAROCEAN_GENERATED_DIR}/*.c")

# Game sources
set(GAME_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/src/main.c
    ${CMAKE_CURRENT_SOURCE_DIR}/src/so_rtl.c
    ${CMAKE_CURRENT_SOURCE_DIR}/src/so_cpu_infra.c
    ${CMAKE_CURRENT_SOURCE_DIR}/src/so_spc_player.c
    ${CMAKE_CURRENT_SOURCE_DIR}/src/state_file.c
    ${CMAKE_CURRENT_SOURCE_DIR}/snesrecomp/runner/src/desktop/mmx_config.c
)

# Main executable
add_executable(StarOcean
    ${SNESRECOMP_RUNNER_SOURCES}
    ${GAME_SOURCES}
    ${GENERATED_SOURCES}
)

target_include_directories(StarOcean PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${SNESRECOMP_RUNNER_INCLUDE_DIRS}
    ${SNESRECOMP_ROOT}/runner/src/desktop
    ${STAROCEAN_GENERATED_DIR}
)

target_compile_definitions(StarOcean PRIVATE
    SNESRECOMP_REVERSE_DEBUG=0        # raw WRAM stores; matches non-debug generated C
    SO_DEBUG_PORT=13308
    SNESRECOMP_BUILD_VERSION="dev"
)
# The TCP debug server is off by default; SNESRECOMP_ENABLE_TRACE above
# turns it on. Keep the production define explicit so the flag is visible
# in build logs either way.
if(NOT SNESRECOMP_ENABLE_TRACE)
    target_compile_definitions(StarOcean PRIVATE SNESRECOMP_TRACE=0)
endif()

snesrecomp_target_post_mortem(StarOcean TIER2)

# SDL integration
snesrecomp_target_sdl(StarOcean)

# Link libraries
target_link_libraries(StarOcean PRIVATE ${SNESRECOMP_RUNNER_LIBRARIES})
if(NOT WIN32)
    target_link_libraries(StarOcean PRIVATE m dl pthread)
endif()

# Windows resources
if(WIN32)
    target_link_libraries(StarOcean PRIVATE dbghelp)
endif()

# Install
install(TARGETS StarOcean
    RUNTIME DESTINATION .
    BUNDLE DESTINATION .
)

# CPack for release packaging
set(CPACK_PACKAGE_NAME "StarOceanRecomp")
set(CPACK_PACKAGE_VERSION "1.0.0")
set(CPACK_PACKAGE_DESCRIPTION "Star Ocean SNES Recompilation")
set(CPACK_GENERATOR "ZIP")
include(CPack)
