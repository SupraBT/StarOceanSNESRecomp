// drive_bsnes.cpp -- headless libretro driver for the Track-B oracle.
// DEV/DIAGNOSTIC ONLY. Loads a libretro SNES core DLL, plays a ROM for a
// fixed number of frames with scripted input, and lets the core dump
// per-frame state (CPU/PPU/S-DD1/WRAM/VRAM/CGRAM) via the SNESREF_STATE_OUT
// env var (see bsnes target-libretro/state_snapshot.hpp).
//
//   drive_bsnes.exe <core.dll> <rom.sfc> --frames N [--input file]
//
// Input file: one event per line "start:duration:hexmask" with SNES joypad
// masks (same format/values as so_drive.py --input and the recorded
// name-screen walk: A=0x100).  # comments allowed.
//
// No SDL, no window, no audio sink: the core runs at full speed.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "libretro.h"

static HMODULE g_core;
#define LR(sym) static decltype(&sym) p_##sym;
LR(retro_init) LR(retro_deinit)
LR(retro_get_system_info) LR(retro_get_system_av_info)
LR(retro_set_environment) LR(retro_set_video_refresh)
LR(retro_set_audio_sample) LR(retro_set_audio_sample_batch)
LR(retro_set_input_poll) LR(retro_set_input_state)
LR(retro_set_controller_port_device)
LR(retro_load_game) LR(retro_unload_game) LR(retro_run)
#undef LR

template<class T> static void bind(T& fn, const char* name) {
    fn = (T)GetProcAddress(g_core, name);
    if (!fn) { fprintf(stderr, "drive_bsnes: missing core symbol: %s\n", name); exit(2); }
}

// Current libretro joypad mask (bit = RETRO_DEVICE_ID_JOYPAD_*).
static uint16_t g_retro_mask = 0;

// libretro IDs 0..11 in SNES bits: UP,DOWN,LEFT,RIGHT,B,A,Y,X,L,R,SELECT,START
static const uint16_t kSnesBit[12] = {
    0x0010, 0x0020, 0x0040, 0x0080,  // UP DOWN LEFT RIGHT
    0x0001, 0x0100, 0x0002, 0x0200,  // B   A    Y    X
    0x0400, 0x0800, 0x0004, 0x0008,  // L   R    SELECT START
};

static uint16_t snes_to_retro(uint16_t snes) {
    uint16_t retro = 0;
    for (int i = 0; i < 12; i++) {
        if (snes & kSnesBit[i]) retro |= (uint16_t)(1u << i);
    }
    return retro;
}

static bool environ_cb(unsigned cmd, void*) {
    switch (cmd) {
        case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
        case RETRO_ENVIRONMENT_SET_SYSTEM_AV_INFO:
            return true;
        default:
            return false;
    }
}

static void video_cb(const void*, unsigned, unsigned, size_t) {}
static void audio_cb(int16_t, int16_t) {}
static size_t audio_batch_cb(const int16_t*, size_t frames) { return frames; }
static void input_poll_cb(void) {}
static int16_t input_state_cb(unsigned port, unsigned device, unsigned index, unsigned id) {
    if (port == 0 && device == RETRO_DEVICE_JOYPAD && id < 12 && index == 0)
        return (g_retro_mask >> id) & 1;
    return 0;
}

struct InputEvent { uint64_t start, duration; uint16_t mask; };

static bool load_input_file(const char* path, std::vector<InputEvent>& out) {
    FILE* f = fopen(path, "r");
    if (!f) { fprintf(stderr, "drive_bsnes: cannot open input file %s\n", path); return false; }
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        char* comment = strchr(line, '#');
        if (comment) *comment = '\0';
        unsigned long long start = 0, duration = 0;
        unsigned mask = 0;
        if (sscanf(line, " %llu:%llu:%x", &start, &duration, &mask) == 3) {
            if (!duration || mask > 0xffffu) {
                fprintf(stderr, "drive_bsnes: invalid input event '%s'\n", line);
                fclose(f);
                return false;
            }
            out.push_back({start, duration, (uint16_t)mask});
        }
    }
    fclose(f);
    return true;
}

static void usage() {
    fprintf(stderr,
        "usage: drive_bsnes.exe <core.dll> <rom.sfc> --frames N [--input file]\n");
    exit(1);
}

int main(int argc, char** argv) {
    if (argc < 3) usage();
    const char* corePath = argv[1];
    const char* romPath = argv[2];
    uint64_t frames = 0;
    const char* inputFile = nullptr;
    for (int i = 3; i < argc; i++) {
        if (!strcmp(argv[i], "--frames") && i + 1 < argc) {
            frames = strtoull(argv[++i], nullptr, 0);
        } else if (!strcmp(argv[i], "--input") && i + 1 < argc) {
            inputFile = argv[++i];
        } else {
            usage();
        }
    }
    if (!frames) { fprintf(stderr, "drive_bsnes: --frames N required\n"); return 1; }

    g_core = LoadLibraryA(corePath);
    if (!g_core) { fprintf(stderr, "drive_bsnes: cannot load %s (err=%lu)\n", corePath, GetLastError()); return 1; }
    bind(p_retro_init, "retro_init");
    bind(p_retro_deinit, "retro_deinit");
    bind(p_retro_get_system_info, "retro_get_system_info");
    bind(p_retro_set_environment, "retro_set_environment");
    bind(p_retro_set_video_refresh, "retro_set_video_refresh");
    bind(p_retro_set_audio_sample, "retro_set_audio_sample");
    bind(p_retro_set_audio_sample_batch, "retro_set_audio_sample_batch");
    bind(p_retro_set_input_poll, "retro_set_input_poll");
    bind(p_retro_set_input_state, "retro_set_input_state");
    bind(p_retro_set_controller_port_device, "retro_set_controller_port_device");
    bind(p_retro_load_game, "retro_load_game");
    bind(p_retro_unload_game, "retro_unload_game");
    bind(p_retro_run, "retro_run");

    retro_system_info info{};
    p_retro_get_system_info(&info);
    printf("core: %s v%s (%s)\n", info.library_name ? info.library_name : "?", info.library_version ? info.library_version : "?", info.valid_extensions ? info.valid_extensions : "?");
    fflush(stdout);

    p_retro_set_environment(environ_cb);
    p_retro_set_video_refresh(video_cb);
    p_retro_set_audio_sample(audio_cb);
    p_retro_set_audio_sample_batch(audio_batch_cb);
    p_retro_set_input_poll(input_poll_cb);
    p_retro_set_input_state(input_state_cb);
    p_retro_init();
    p_retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD);

    retro_game_info gi{};
    gi.path = romPath;
    if (!p_retro_load_game(&gi)) {
        fprintf(stderr, "drive_bsnes: retro_load_game failed\n");
        return 1;
    }

    std::vector<InputEvent> events;
    if (inputFile && !load_input_file(inputFile, events)) return 1;

    printf("running %llu frames (%zu input events)\n",
           (unsigned long long)frames, events.size());
    fflush(stdout);

    for (uint64_t f = 0; f < frames; f++) {
        uint16_t snes = 0;
        for (const auto& e : events) {
            if (f >= e.start && f - e.start < e.duration) snes |= e.mask;
        }
        g_retro_mask = snes_to_retro(snes);
        p_retro_run();
    }

    p_retro_unload_game();
    p_retro_deinit();
    FreeLibrary(g_core);
    printf("drive_bsnes: done (%llu frames)\n", (unsigned long long)frames);
    return 0;
}
