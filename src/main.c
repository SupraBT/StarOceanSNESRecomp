#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include "desktop/sdl_compat.h"
#include "snes/snes.h"
#include "snes/ppu.h"
#include "snes/apu.h"
#include "snes/sdd1.h"
#include "snes/cart.h"
#include "common_cpu_infra.h"
#include "common_rtl.h"
#include "config.h"
#include "host_report.h"
#include "keybinds.h"
#include "launcher.h"
#include "launcher_cache.h"
#include "framedump.h"
#include "cpu_state.h"
#include "cpu_trace.h"
#include "util.h"
#include "widescreen.h"
#include "so_spc_player.h"

#define WINDOW_TITLE "Star Ocean (S-DD1 Test)"
#define SO_DEBUG_PORT 13308

static const char kWindowTitle[] = WINDOW_TITLE;
static SDL_WindowFlags g_win_flags = SDL_WINDOW_RESIZABLE;
static SDL_Window *g_window;

static uint8 g_paused, g_turbo, g_cursor = true;
int g_benchmark_frames;
int g_benchmark_audio;
static FILE *g_input_log = NULL;
static uint32 g_last_logged_input = 0;
/* Input replay (dev, SNESRECOMP_REPLAY_FILE=<path>): replays a recording in
 * the SNESRECOMP_INPUT_LOG format ("<frame> <hexmask>" per line, with explicit
 * press/release events). The mask active at frame F is the last event at or
 * before F, so press/release pairs reproduce exactly. After each Up-press
 * (mask bit 0x10) the host pauses briefly (SNESRECOMP_REPLAY_UP_PAUSE_MS,
 * default 1500 ms) so scene changes are visible. Off by default. */
#define kReplayMaxEvents 4096
typedef struct { long long frame; uint16_t mask; } ReplayEvent;
static ReplayEvent s_replay_events[kReplayMaxEvents];
static int s_replay_count = 0;
static int s_replay_loaded = 0;
static int s_replay_up_pause_ms = 1500;

static uint16_t replay_mask_for_frame(long long frame) {
    if (!s_replay_count) return 0;
    int lo = 0, hi = s_replay_count - 1, best = -1;
    while (lo <= hi) {
        int mid = (lo + hi) >> 1;
        if (s_replay_events[mid].frame <= frame) { best = mid; lo = mid + 1; }
        else hi = mid - 1;
    }
    return best >= 0 ? s_replay_events[best].mask : 0;
}

static void replay_load(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "[replay] cannot open '%s'\n", path); return; }
    char line[64];
    int up_pauses = 0;
    while (s_replay_count < kReplayMaxEvents && fgets(line, sizeof line, f)) {
        char *end = NULL;
        long long fr = strtoll(line, &end, 10);
        if (end == line) continue;
        unsigned long mask = strtoul(end, NULL, 16);
        s_replay_events[s_replay_count].frame = fr;
        s_replay_events[s_replay_count].mask = (uint16_t)mask;
        /* Count Up presses: mask includes 0x10 and it is a press (previous
         * event differs, i.e. a transition, not a held repeat). */
        if ((mask & 0x10) && s_replay_count &&
            s_replay_events[s_replay_count - 1].mask != (uint16_t)mask)
            up_pauses++;
        s_replay_count++;
    }
    fclose(f);
    s_replay_loaded = 1;
    const char *pms = getenv("SNESRECOMP_REPLAY_UP_PAUSE_MS");
    if (pms && *pms) { int v = atoi(pms); if (v >= 0) s_replay_up_pause_ms = v; }
    fprintf(stderr, "[replay] loaded %d input entries from %s, %d UP pause frames\n",
            s_replay_count, path, up_pauses);
}
static uint8 g_current_window_scale;
static uint32 g_input_state;
static uint32 g_pad_buttons;
static bool g_display_perf;
static int g_curr_fps;
static int g_ppu_render_flags = 0;
static int g_snes_width, g_snes_height;
static int g_last_drawable_width, g_last_drawable_height;
bool g_ws_active;
int g_ws_extra;
static const char *g_active_config_file;
static int g_sdl_audio_mixer_volume = SNESRECOMP_SDL_MIX_MAXVOLUME;
static struct RendererFuncs g_renderer_funcs;

typedef struct GamepadInfo {
  uint32 modifiers;
  SDL_JoystickID joystick_id;
  SDL_Joystick *joystick;
  bool raw_joystick;
  uint8 index;
  uint8 axis_buttons;
  uint16 last_cmd[kGamepadBtn_Count];
  Sint16 last_axis_x, last_axis_y;
} GamepadInfo;

static GamepadInfo g_gamepad[2];

static void EnsureConfigIni(void);
static void OpenOneGamepad(SDL_JoystickID i);
static void OpenOneJoystick(SDL_JoystickID i);
static uint32 GetActiveControllers(void);
static void HandleVolumeAdjustment(int volume_adjustment);
static void HandleGamepadAxisInput(GamepadInfo *gi, int axis, Sint16 value);
static int RemapSdlButton(int button);
static void HandleGamepadInput(GamepadInfo *gi, int button, bool pressed);
static void HandleInput(int keyCode, int keyMod, bool pressed);
static void HandleCommand(uint32 j, bool pressed);

extern Snes *g_snes;

struct SpcPlayer *g_spc_player;

static uint8_t g_my_pixels[(256 + 2 * kWsExtraMax) * 4 * 240];

enum {
    kDefaultFullscreen = 0,
    kMaxWindowScale = 10,
    kDefaultFreq = 44100,
    kDefaultChannels = 2,
    kDefaultSamples = 2048,
};

void NORETURN Die(const char *error) {
    host_report_fatal(error);
    SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, kWindowTitle, error, NULL);
    fprintf(stderr, "Error: %s\n", error);
    exit(1);
}

static GamepadInfo *GetGamepadInfo(SDL_JoystickID id) {
    return (g_gamepad[0].joystick_id == id) ? &g_gamepad[0] :
        (g_gamepad[1].joystick_id == id) ? &g_gamepad[1] : NULL;
}

void ChangeWindowScale(int scale_step) {
    if ((SDL_GetWindowFlags(g_window) & (SNESRECOMP_SDL_WINDOW_FULLSCREEN_DESKTOP | SDL_WINDOW_FULLSCREEN | SDL_WINDOW_MINIMIZED | SDL_WINDOW_MAXIMIZED)) != 0)
        return;
    int max_scale = kMaxWindowScale;
    SDL_Rect bounds;
    int bt = -1, bl, bb, br;
    if (snesrecomp_sdl_get_display_usable_bounds(g_window, &bounds)) {
        if (!snesrecomp_sdl_get_window_borders_size(g_window, &bt, &bl, &bb, &br)) {
            bl = br = bb = 1;
            bt = 31;
        }
        int logical_width = 256;
        int logical_height = 224;
        int mw = (bounds.w - bl - br + logical_width / 4) / logical_width;
        int mh = (bounds.h - bt - bb + logical_height / 4) / logical_height;
        max_scale = IntMin(mw, mh);
    }
    int new_scale = IntMax(IntMin(g_current_window_scale + scale_step, max_scale), 1);
    g_current_window_scale = new_scale;
    int w = new_scale * 256;
    int h = new_scale * 224;

    SDL_SetWindowSize(g_window, w, h);
    if (bt >= 0) {
        int mx, my;
        snesrecomp_sdl_get_global_mouse_state(&mx, &my);
        int wx = IntMax(IntMin(mx - w / 2, bounds.x + bounds.w - bl - br - w), bounds.x + bl);
        int wy = IntMax(IntMin(my - h / 2, bounds.y + bounds.h - bt - bb - h), bounds.y + bt);
        SDL_SetWindowPosition(g_window, wx, wy);
    } else {
        SDL_SetWindowPosition(g_window, SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED);
    }
}

#define RESIZE_BORDER 20
static SDL_HitTestResult HitTestCallback(SDL_Window *win, const SDL_Point *pt, void *data) {
    uint32 flags = SDL_GetWindowFlags(win);
    if ((flags & SNESRECOMP_SDL_WINDOW_FULLSCREEN_DESKTOP) != 0 || (flags & SDL_WINDOW_FULLSCREEN) != 0)
        return SDL_HITTEST_NORMAL;

    if ((SDL_GetModState() & KMOD_CTRL) != 0)
        return SDL_HITTEST_DRAGGABLE;

    int w, h;
    SDL_GetWindowSize(win, &w, &h);

    if (pt->y < RESIZE_BORDER) {
        return (pt->x < RESIZE_BORDER) ? SDL_HITTEST_RESIZE_TOPLEFT :
            (pt->x >= w - RESIZE_BORDER) ? SDL_HITTEST_RESIZE_TOPRIGHT : SDL_HITTEST_RESIZE_TOP;
    } else if (pt->y >= h - RESIZE_BORDER) {
        return (pt->x < RESIZE_BORDER) ? SDL_HITTEST_RESIZE_BOTTOMLEFT :
            (pt->x >= w - RESIZE_BORDER) ? SDL_HITTEST_RESIZE_BOTTOMRIGHT : SDL_HITTEST_RESIZE_BOTTOM;
    } else {
        if (pt->x < RESIZE_BORDER) {
            return SDL_HITTEST_RESIZE_LEFT;
        } else if (pt->x >= w - RESIZE_BORDER) {
            return SDL_HITTEST_RESIZE_RIGHT;
        }
    }
    return SDL_HITTEST_NORMAL;
}

static void DrawPpuFrameWithPerf(void) {
    int drawable_width = 0, drawable_height = 0;
    if (g_renderer_funcs.GetOutputSize)
        g_renderer_funcs.GetOutputSize(&drawable_width, &drawable_height);
    if (drawable_width <= 0 || drawable_height <= 0)
        SDL_GetWindowSize(g_window, &drawable_width, &drawable_height);
    if (drawable_width > 0 && drawable_height > 0) {
        g_last_drawable_width = drawable_width;
        g_last_drawable_height = drawable_height;
    } else {
        drawable_width = g_last_drawable_width;
        drawable_height = g_last_drawable_height;
    }

    int width = 256;
    int ws_extra = 0;
    g_snes_width = width;
    g_ws_extra = ws_extra;
    g_ws_active = g_ws_extra != 0;

    uint32 render_flags = g_ppu_render_flags;
    if (g_ws_active)
        render_flags |= kPpuRenderFlags_NewRenderer;

    /* Render PPU to g_my_pixels, then upload to the SDL texture. */
    extern Ppu *g_ppu;
    PpuBeginDrawing(g_ppu, g_my_pixels, (size_t)width * 4, render_flags);
    PpuSetExtraSpace(g_ppu, (uint8)g_ws_extra);
    g_rtl_game_info->draw_ppu_frame();

    /* Lock the SDL texture, copy the rendered frame into it, and present. */
    uint8 *tex_pixels = NULL;
    int tex_pitch = 0;
    bool draw_started = false;
    if (g_renderer_funcs.BeginDraw) {
        g_renderer_funcs.BeginDraw(width, 224, &tex_pixels, &tex_pitch);
        draw_started = (tex_pixels != NULL);
    }
    if (draw_started && tex_pixels) {
        /* Copy g_my_pixels into the locked texture row by row. */
        size_t row_bytes = (size_t)width * 4;
        for (int y = 0; y < 224; y++)
            memcpy(tex_pixels + (size_t)y * tex_pitch,
                   g_my_pixels + (size_t)y * row_bytes, row_bytes);
    }
    if (draw_started && g_renderer_funcs.EndDraw)
        g_renderer_funcs.EndDraw();
}

static SDL_mutex *g_audio_mutex;
static uint8 *g_audiobuffer, *g_audiobuffer_cur, *g_audiobuffer_end;
static int g_frames_per_block;
static uint8 g_audio_channels;
static SDL_AudioDeviceID g_audio_device;
#if SNESRECOMP_SDL3
static SDL_AudioStream *g_audio_stream;
static uint8 *g_audio_stream_buffer;
static size_t g_audio_stream_buffer_size;
#endif

void RtlApuLock(void) {
    SDL_LockMutex(g_audio_mutex);
}

void RtlApuUnlock(void) {
    SDL_UnlockMutex(g_audio_mutex);
}

static void FillAudioBuffer(Uint8 *stream, int len) {
    static SDL_atomic_t first_cb;
    if (SDL_AtomicCAS(&first_cb, 0, 1))
        host_report_breadcrumb("first audio callback (len=%d)", len);
    if (!snesrecomp_sdl_lock_mutex(g_audio_mutex)) Die("Mutex lock failed!");
    while (len != 0) {
        if (g_audiobuffer_end - g_audiobuffer_cur == 0) {
            RtlRenderAudio((int16 *)g_audiobuffer, g_frames_per_block, g_audio_channels);
            g_audiobuffer_cur = g_audiobuffer;
            g_audiobuffer_end = g_audiobuffer + g_frames_per_block * g_audio_channels * sizeof(int16);
        }
        int n = IntMin(len, g_audiobuffer_end - g_audiobuffer_cur);
        if (g_sdl_audio_mixer_volume == SNESRECOMP_SDL_MIX_MAXVOLUME) {
            memcpy(stream, g_audiobuffer_cur, n);
        } else {
            SDL_memset(stream, 0, n);
#if SNESRECOMP_SDL3
            SDL_MixAudio(stream, g_audiobuffer_cur, SDL_AUDIO_S16, n,
                        (float)g_sdl_audio_mixer_volume / SNESRECOMP_SDL_MIX_MAXVOLUME);
#else
            SDL_MixAudioFormat(stream, g_audiobuffer_cur, AUDIO_S16, n,
                            g_sdl_audio_mixer_volume);
#endif
        }
        g_audiobuffer_cur += n;
        stream += n;
        len -= n;
    }
    SDL_UnlockMutex(g_audio_mutex);
}

#if SNESRECOMP_SDL3
static void SDLCALL AudioStreamCallback(
    void *userdata, SDL_AudioStream *stream, int additional_amount,
    int total_amount) {
    (void)userdata;
    (void)total_amount;
    if (additional_amount <= 0) return;
    if ((size_t)additional_amount > g_audio_stream_buffer_size) {
        uint8 *resized = (uint8 *)realloc(g_audio_stream_buffer, additional_amount);
        if (!resized) return;
        g_audio_stream_buffer = resized;
        g_audio_stream_buffer_size = (size_t)additional_amount;
    }
    FillAudioBuffer(g_audio_stream_buffer, additional_amount);
    SDL_PutAudioStreamData(stream, g_audio_stream_buffer, additional_amount);
}
#else
static void SDLCALL AudioCallback(void *userdata, Uint8 *stream, int len) {
    (void)userdata;
    FillAudioBuffer(stream, len);
}
#endif

static void SetAudioPaused(bool paused) {
#if SNESRECOMP_SDL3
    if (g_audio_stream) {
        if (paused) SDL_PauseAudioStreamDevice(g_audio_stream);
        else SDL_ResumeAudioStreamDevice(g_audio_stream);
    }
#else
    if (g_audio_device) SDL_PauseAudioDevice(g_audio_device, paused);
#endif
}

static SDL_Renderer *g_renderer;
static SDL_Texture *g_texture;
static SDL_Rect g_sdl_renderer_rect;
static SDL_Rect g_sdl_present_rect;

static bool SdlRenderer_Init(SDL_Window *window) {
    if (g_config.shader)
        fprintf(stderr, "Warning: Shaders are supported only with the OpenGL backend\n");

    bool want_software = g_config.output_method == kOutputMethod_SDLSoftware;
    SDL_Renderer *renderer = snesrecomp_sdl_create_renderer(
        g_window, want_software, true);
    if (renderer == NULL) {
        printf("Failed to create renderer: %s\n", SDL_GetError());
        return false;
    }
    if (kDebugFlag) {
        const char *name = snesrecomp_sdl_renderer_name(renderer);
        printf("Renderer: %s (vsync=%d)\n", name ? name : "(unknown)",
                snesrecomp_sdl_get_render_vsync(renderer));
    }
    g_renderer = renderer;

    int tex_mult = 1;
    g_texture = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_ARGB8888, SDL_TEXTUREACCESS_STREAMING,
                                256 * tex_mult, 224 * tex_mult);
    if (g_texture == NULL) {
        printf("Failed to create texture: %s\n", SDL_GetError());
        return false;
    }
    snesrecomp_sdl_set_texture_opaque(g_texture);
    snesrecomp_sdl_set_texture_linear(g_texture, g_config.linear_filtering);
    return true;
}

static void SdlRenderer_Destroy(void) {
    SDL_DestroyTexture(g_texture);
    SDL_DestroyRenderer(g_renderer);
}

static void SdlRenderer_GetOutputSize(int *width, int *height) {
    if (!snesrecomp_sdl_get_render_output_size(g_renderer, width, height)) {
        *width = 0;
        *height = 0;
    }
}

static void SdlRenderer_BeginDraw(int width, int height, uint8 **pixels, int *pitch) {
    int texture_width, texture_height;
    snesrecomp_sdl_get_texture_size(g_texture, &texture_width, &texture_height);
    if (texture_width != width || texture_height != height) {
        SDL_DestroyTexture(g_texture);
        g_texture = SDL_CreateTexture(g_renderer, SDL_PIXELFORMAT_ARGB8888,
                                    SDL_TEXTUREACCESS_STREAMING, width, height);
        if (!g_texture) Die("SDL widescreen texture allocation failed");
    }
    snesrecomp_sdl_set_texture_opaque(g_texture);
    int output_width = 0, output_height = 0;
    SdlRenderer_GetOutputSize(&output_width, &output_height);
    /* Letterbox the SNES frame into the output rect. Star Ocean is rendered
     * at native 256x224 (no widescreen support), so this is a plain
     * aspect-preserving fit centered on the output surface. */
    if (g_config.ignore_aspect_ratio || output_width <= 0 || output_height <= 0) {
      g_sdl_present_rect.x = 0;
      g_sdl_present_rect.y = 0;
      g_sdl_present_rect.w = output_width;
      g_sdl_present_rect.h = output_height;
    } else {
      double scale = (double)output_width / width < (double)output_height / height
          ? (double)output_width / width : (double)output_height / height;
      int w = (int)(width * scale);
      int h = (int)(height * scale);
      g_sdl_present_rect.w = w;
      g_sdl_present_rect.h = h;
      g_sdl_present_rect.x = (output_width - w) / 2;
      g_sdl_present_rect.y = (output_height - h) / 2;
    }
    g_sdl_renderer_rect.w = width;
    g_sdl_renderer_rect.h = height;
    if (!snesrecomp_sdl_lock_texture(g_texture, &g_sdl_renderer_rect,
                                    (void **)pixels, pitch)) {
        printf("Failed to lock texture: %s\n", SDL_GetError());
        return;
    }
}

static void SdlRenderer_EndDraw(void) {
    SDL_UnlockTexture(g_texture);
    snesrecomp_sdl_render_texture(g_renderer, g_texture, &g_sdl_renderer_rect,
                    &g_sdl_present_rect);
    SDL_RenderPresent(g_renderer);
}

static const struct RendererFuncs kSdlRendererFuncs = {
    &SdlRenderer_Init,
    &SdlRenderer_Destroy,
    &SdlRenderer_GetOutputSize,
    &SdlRenderer_BeginDraw,
    &SdlRenderer_EndDraw,
};

void MkDir(const char *s) {
#if defined(_WIN32)
    _mkdir(s);
#else
    mkdir(s, 0755);
#endif
}

#include <signal.h>
#include "cpu_state.h"
#include "cpu_trace.h"
#include "post_mortem.h"
extern uint8_t g_ram[0x20000];
static void crash_handler(int sig) {
    extern const char *g_last_recomp_func;
    extern void RecompStackDump(void);
    fprintf(stderr, "\n*** CRASH (signal %d) in recomp func: %s ***\n",
            sig, g_last_recomp_func ? g_last_recomp_func : "(unknown)");
    RecompStackDump();
    cpu_trace_dump_dbpb("CRASH -- DB/PB mutations");
    cpu_trace_dump_recent("CRASH -- main trace ring", 256);
    fflush(stderr);
    recomp_post_mortem_dump("signal", NULL);
    _exit(128 + sig);
}

#ifdef _WIN32
#include <windows.h>
static LONG WINAPI seh_handler(EXCEPTION_POINTERS* info) {
    extern const char *g_last_recomp_func;
    extern void RecompStackDump(void);
    DWORD code = info->ExceptionRecord->ExceptionCode;
    void* addr = info->ExceptionRecord->ExceptionAddress;
    fprintf(stderr, "\n*** SEH CRASH code=0x%08lX at %p, last recomp func: %s ***\n",
            code, addr, g_last_recomp_func ? g_last_recomp_func : "(unknown)");
    if (code == EXCEPTION_ACCESS_VIOLATION) {
        ULONG_PTR kind = info->ExceptionRecord->ExceptionInformation[0];
        ULONG_PTR fault_addr = info->ExceptionRecord->ExceptionInformation[1];
        fprintf(stderr, "    access violation: %s at 0x%p\n",
                kind == 0 ? "read" : (kind == 1 ? "write" : "execute"),
                (void*)fault_addr);
    }
    RecompStackDump();
    cpu_trace_dump_dbpb("SEH CRASH -- DB/PB mutations");
    cpu_trace_dump_recent("SEH CRASH -- main trace ring", 256);
    fflush(stderr);
    recomp_post_mortem_dump("seh", info);
    return EXCEPTION_EXECUTE_HANDLER;
}
#endif

static void post_mortem_atexit(void) {
    recomp_post_mortem_dump("atexit", NULL);
}

static const char *AbsolutizePathArg(const char *path, char *buf, size_t size) {
    extern int snesrecomp_abspath(const char *path, char *out, size_t max_len);
    return (path && snesrecomp_abspath(path, buf, size)) ? buf : path;
}

static int RelocateRomToExeDir(char *rom_path, size_t cap) {
    if (!rom_path || !rom_path[0]) return 0;
    const char *base = rom_path;
    for (const char *p = rom_path; *p; p++)
        if (*p == '/' || *p == '\\') base = p + 1;
    if (!*base) return 0;

    char dst[1024];
    if (!snesrecomp_exe_dir_path(base, dst, sizeof(dst))) return 0;
#ifdef _WIN32
    if (_stricmp(dst, rom_path) == 0) return 0;
#else
    if (strcmp(dst, rom_path) == 0) return 0;
#endif

    FILE *in = fopen(rom_path, "rb");
    if (!in) return 0;
    /* Skip the copy when the destination already exists with the same size:
     * avoids re-copying the 6MB ROM (and the resulting HDD churn) every launch. */
    {
        FILE *probe = fopen(dst, "rb");
        if (probe) {
            long src_size = -1, dst_size = -1;
            if (fseek(in, 0, SEEK_END) == 0) src_size = ftell(in);
            if (fseek(probe, 0, SEEK_END) == 0) dst_size = ftell(probe);
            fseek(in, 0, SEEK_SET);
            fclose(probe);
            if (src_size >= 0 && src_size == dst_size) {
                snprintf(rom_path, cap, "%s", dst);
                return 1;
            }
        }
    }
    FILE *out = fopen(dst, "wb");
    if (!out) { fclose(in); return 0; }
    char buf[65536];
    size_t n;
    int ok = 1;
    while ((n = fread(buf, 1, sizeof(buf), in)) > 0)
        if (fwrite(buf, 1, n, out) != n) { ok = 0; break; }
    fclose(in);
    fclose(out);
    if (!ok) { remove(dst); return 0; }

    snprintf(rom_path, cap, "%s", dst);
    printf("[Launcher] Copied ROM into the game directory: %s\n", dst);
    return 1;
}

static void HandleCommand(uint32 j, bool pressed) {
  static const uint8 kKbdRemap[] = { 4, 5, 6, 7, 2, 3, 8, 0, 9, 1, 10, 11 };
  if (j < kKeys_Controls)
    return;

  if (j <= kKeys_Controls_Last) {
    uint32 m = 1 << kKbdRemap[j - kKeys_Controls];
    g_input_state = pressed ? (g_input_state | m) : (g_input_state & ~m);
    return;
  }

  if (j <= kKeys_ControlsP2_Last) {
    uint32 m = 0x1000 << kKbdRemap[j - kKeys_ControlsP2];
    g_input_state = pressed ? (g_input_state | m) : (g_input_state & ~m);
    return;
  }

  if (j == kKeys_Turbo) {
    g_turbo = pressed;
    return;
  }

  if (!pressed)
    return;
  if (j <= kKeys_Load_Last) {
    RtlSaveLoad(kSaveLoad_Load, j - kKeys_Load);
  } else if (j <= kKeys_Save_Last) {
    RtlSaveLoad(kSaveLoad_Save, j - kKeys_Save);
  } else {
    switch (j) {
    case kKeys_Fullscreen:
      g_win_flags ^= SDL_WINDOW_FULLSCREEN;
      snesrecomp_sdl_set_fullscreen(
          g_window, (g_win_flags & SDL_WINDOW_FULLSCREEN) != 0);
      g_cursor = !g_cursor;
      snesrecomp_sdl_show_cursor(g_cursor != 0);
      break;
    case kKeys_Reset:
      RtlReset(1);
      break;
    case kKeys_Pause: g_paused = !g_paused; break;
    case kKeys_PauseDimmed:
      g_paused = !g_paused;
#ifdef _WIN32
      if (g_paused) {
        SDL_SetRenderDrawBlendMode(g_renderer, SDL_BLENDMODE_BLEND);
#if SNESRECOMP_SDL3
        SDL_SetRenderDrawColor(g_renderer, 0.0f, 0.0f, 0.0f, 159.0f / 255.0f);
#else
        SDL_SetRenderDrawColor(g_renderer, 0, 0, 0, 159);
#endif
        SDL_RenderFillRect(g_renderer, NULL);
        SDL_RenderPresent(g_renderer);
      }
#endif
      break;
    case kKeys_WindowBigger: ChangeWindowScale(1); break;
    case kKeys_WindowSmaller: ChangeWindowScale(-1); break;
    case kKeys_DisplayPerf: g_display_perf ^= 1; break;
    case kKeys_ToggleRenderer:
      g_ppu_render_flags ^= kPpuRenderFlags_NewRenderer;
      printf("New renderer = %x\n", g_ppu_render_flags & kPpuRenderFlags_NewRenderer);
      break;
    case kKeys_VolumeUp:
    case kKeys_VolumeDown: HandleVolumeAdjustment(j == kKeys_VolumeUp ? 1 : -1); break;
    default: assert(0);
    }
  }
}

static void HandleInput(int keyCode, int keyMod, bool pressed) {
  int j = FindCmdForSdlKey(keyCode, (SDL_Keymod)keyMod);
  if (j != 0)
    HandleCommand(j, pressed);
}

static uint32 GetActiveControllers() {
  uint32 ctrl = g_config.has_keyboard_controls;
  ctrl |= g_gamepad[0].joystick_id != -1 ? 1 : 0;
  ctrl |= g_gamepad[1].joystick_id != -1 ? 2 : 0;
  return ctrl << 30;
}

static void OpenOneGamepad(SDL_JoystickID i) {
  if (!SDL_IsGameController(i)) {
    OpenOneJoystick(i);
    return;
  }
  {
    SDL_GameController *controller = SDL_GameControllerOpen(i);
    if (!controller) {
      fprintf(stderr, "Could not open gamepad %d: %s\n", i, SDL_GetError());
      return;
    }

    uint32 joystick_id = SDL_JoystickInstanceID(SDL_GameControllerGetJoystick(controller));
    if (GetGamepadInfo(joystick_id)) {
      SDL_GameControllerClose(controller);
      return;
    }

    uint8 scan_order[3] = { SDL_GameControllerGetPlayerIndex(controller), 0, 1 };

    int found_idx = -1;
    for (int i = 0; i < 3; i++) {
      uint8 j = scan_order[i];
      if (j < 2 && g_config.enable_gamepad[j] && (i == 0 || g_gamepad[j].joystick_id == -1)) {
        found_idx = j;
        break;
      }
    }

    printf("Found controller '%s' assigning to player %d\n", SDL_GameControllerName(controller), found_idx + 1);
    if (found_idx >= 0) {
      GamepadInfo *gi = &g_gamepad[found_idx];
      memset(gi, 0, sizeof(GamepadInfo));
      gi->index = found_idx;
      gi->joystick_id = joystick_id;
    }
  }
}

static void OpenOneJoystick(SDL_JoystickID i) {
  if (SDL_IsGameController(i)) return;
  SDL_Joystick *joystick = SDL_JoystickOpen(i);
  if (!joystick) {
    fprintf(stderr, "Could not open raw joystick %d: %s\n", i, SDL_GetError());
    return;
  }
  SDL_JoystickID id = SDL_JoystickInstanceID(joystick);
  if (GetGamepadInfo(id)) { SDL_JoystickClose(joystick); return; }
  int slot = -1;
  for (int j = 0; j < 2; ++j) {
    if (g_config.enable_gamepad[j] && g_gamepad[j].joystick_id == -1) {
      slot = j; break;
    }
  }
  if (slot < 0) { SDL_JoystickClose(joystick); return; }
  GamepadInfo *gi = &g_gamepad[slot];
  memset(gi, 0, sizeof(*gi));
  gi->joystick = joystick;
  gi->raw_joystick = true;
  gi->index = slot;
  gi->joystick_id = id;
  printf("Found unmapped raw joystick '%s' assigning to player %d\n",
         SDL_JoystickName(joystick), slot + 1);
}

static int RemapSdlButton(int button) {
  switch (button) {
  case SDL_CONTROLLER_BUTTON_A: return kGamepadBtn_A;
  case SDL_CONTROLLER_BUTTON_B: return kGamepadBtn_B;
  case SDL_CONTROLLER_BUTTON_X: return kGamepadBtn_X;
  case SDL_CONTROLLER_BUTTON_Y: return kGamepadBtn_Y;
  case SDL_CONTROLLER_BUTTON_BACK: return kGamepadBtn_Back;
  case SDL_CONTROLLER_BUTTON_GUIDE: return kGamepadBtn_Guide;
  case SDL_CONTROLLER_BUTTON_START: return kGamepadBtn_Start;
  case SDL_CONTROLLER_BUTTON_LEFTSTICK: return kGamepadBtn_L3;
  case SDL_CONTROLLER_BUTTON_RIGHTSTICK: return kGamepadBtn_R3;
  case SDL_CONTROLLER_BUTTON_LEFTSHOULDER: return kGamepadBtn_L1;
  case SDL_CONTROLLER_BUTTON_RIGHTSHOULDER: return kGamepadBtn_R1;
  case SDL_CONTROLLER_BUTTON_DPAD_UP: return kGamepadBtn_DpadUp;
  case SDL_CONTROLLER_BUTTON_DPAD_DOWN: return kGamepadBtn_DpadDown;
  case SDL_CONTROLLER_BUTTON_DPAD_LEFT: return kGamepadBtn_DpadLeft;
  case SDL_CONTROLLER_BUTTON_DPAD_RIGHT: return kGamepadBtn_DpadRight;
  default: return -1;
  }
}

/* Set/clear a SNES controller bit from a gamepad source. Mirrors
 * HandleCommand's kKeys_Controls / kKeys_ControlsP2 logic but writes to
 * g_pad_buttons so the per-frame keyboard polling can't clobber gamepad-set
 * bits. Non-controller commands fall through to HandleCommand so things like
 * state save/load on a gamepad button still work. */
static void SetPadButtonOrFallthrough(uint32 j, bool pressed) {
  static const uint8 kKbdRemap[] = { 4, 5, 6, 7, 2, 3, 8, 0, 9, 1, 10, 11 };
  if (j >= kKeys_Controls && j <= kKeys_Controls_Last) {
    uint32 m = 1u << kKbdRemap[j - kKeys_Controls];
    g_pad_buttons = pressed ? (g_pad_buttons | m) : (g_pad_buttons & ~m);
    return;
  }
  if (j >= kKeys_ControlsP2 && j <= kKeys_ControlsP2_Last) {
    uint32 m = 0x1000u << kKbdRemap[j - kKeys_ControlsP2];
    g_pad_buttons = pressed ? (g_pad_buttons | m) : (g_pad_buttons & ~m);
    return;
  }
  HandleCommand(j, pressed);
}

static void HandleGamepadInput(GamepadInfo *gi, int button, bool pressed) {
  if (!!(gi->modifiers & (1 << button)) == pressed)
    return;
  gi->modifiers ^= 1 << button;
  if (pressed)
    gi->last_cmd[button] = FindCmdForGamepadButton(button + gi->index * kGamepadBtn_Count, gi->modifiers);
  if (gi->last_cmd[button] != 0)
    SetPadButtonOrFallthrough(gi->last_cmd[button], pressed);
}

static void HandleVolumeAdjustment(int volume_adjustment) {
  g_sdl_audio_mixer_volume = IntMin(
      IntMax(0, g_sdl_audio_mixer_volume +
                    volume_adjustment *
                        (SNESRECOMP_SDL_MIX_MAXVOLUME >> 4)),
      SNESRECOMP_SDL_MIX_MAXVOLUME);
  printf("[SDL mixer volume]=%i\n", g_sdl_audio_mixer_volume);
}

/* Approximates atan2(y, x) normalized to the [0,4) range
 * with a maximum error of 0.1620 degrees. */
static float ApproximateAtan2(float y, float x) {
  uint32 sign_mask = 0x80000000;
  float b = 0.596227f;
  uint32 ux_s = sign_mask & *(uint32 *)&x;
  uint32 uy_s = sign_mask & *(uint32 *)&y;
  float q = (float)((~ux_s & uy_s) >> 29 | ux_s >> 30);
  float bxy_a = b * x * y;
  if (bxy_a < 0.0f) bxy_a = -bxy_a;
  float num = bxy_a + y * y;
  float atan_1q = num / (x * x + bxy_a + num + 0.000001f);
  uint32_t uatan_2q = (ux_s ^ uy_s) | *(uint32 *)&atan_1q;
  return q + *(float *)&uatan_2q;
}

static void HandleGamepadAxisInput(GamepadInfo *gi, int axis, Sint16 value) {
  if (axis == SDL_CONTROLLER_AXIS_LEFTX || axis == SDL_CONTROLLER_AXIS_LEFTY) {
    *(axis == SDL_CONTROLLER_AXIS_LEFTX ? &gi->last_axis_x : &gi->last_axis_y) = value;
    int buttons = 0;
    if (gi->last_axis_x * gi->last_axis_x + gi->last_axis_y * gi->last_axis_y >= g_config.gamepad_deadzone * g_config.gamepad_deadzone) {
      static const uint8 kSegmentToButtons[8] = {
        1 << 4,           // 0 = up
        1 << 4 | 1 << 7,  // 1 = up, right
        1 << 7,           // 2 = right
        1 << 7 | 1 << 5,  // 3 = right, down
        1 << 5,           // 4 = down
        1 << 5 | 1 << 6,  // 5 = down, left
        1 << 6,           // 6 = left
        1 << 6 | 1 << 4,  // 7 = left, up
      };
      uint8 angle = (uint8)(int)(ApproximateAtan2(gi->last_axis_y, gi->last_axis_x) * 64.0f + 0.5f);
      buttons = kSegmentToButtons[(uint8)(angle + 16 + 64) >> 5];
    }
    gi->axis_buttons = buttons;
  } else if ((axis == SDL_CONTROLLER_AXIS_TRIGGERLEFT || axis == SDL_CONTROLLER_AXIS_TRIGGERRIGHT)) {
    if (value < 12000 || value >= 16000)  // hysteresis
      HandleGamepadInput(gi, axis == SDL_CONTROLLER_AXIS_TRIGGERLEFT ? kGamepadBtn_L2 : kGamepadBtn_R2, value >= 12000);
  }
}

static const char kDefaultConfigIniContent[] =
  "[General]\n"
  "# Automatically save state on quit and reload on start\n"
  "Autosave = 0\n"
  "\n"
  "# Disable the SDL_Delay that paces each frame (slightly better perf if your\n"
  "# display is set to exactly 60hz; may desync audio on other displays)\n"
  "DisableFrameDelay = 0\n"
  "\n"
  "[Graphics]\n"
  "# Window size (Auto or WidthxHeight)\n"
  "WindowSize = Auto\n"
  "\n"
  "# Fullscreen mode (0=windowed, 1=desktop fullscreen, 2=fullscreen w/mode change)\n"
  "Fullscreen = 0\n"
  "\n"
  "# Window scale (1=100%, 2=200%, 3=300%, etc.)\n"
  "WindowScale = 3\n"
  "\n"
  "# Use the optimized SNES PPU implementation\n"
  "NewRenderer = 1\n"
  "\n"
  "# Use either SDL, SDL-Software, or OpenGL as the output method.\n"
  "OutputMethod = SDL\n"
  "\n"
  "# Don't keep the aspect ratio\n"
  "IgnoreAspectRatio = 0\n"
  "\n"
  "# Display aspect: 4:3 (CRT), 8:7 (square pixels), or 1:1 (square frame)\n"
  "DisplayAspect = 4:3\n"
  "\n"
  "# Set to true to use linear filtering. Gives less crisp pixels.\n"
  "LinearFiltering = 0\n"
  "\n"
  "# Remove the sprite limits per scan line\n"
  "NoSpriteLimits = 1\n"
  "\n"
  "[Sound]\n"
  "EnableAudio = 1\n"
  "AudioFreq = 32040\n"
  "AudioChannels = 2\n"
  "AudioSamples = 512\n"
  "\n"
  "[KeyMap]\n"
  "# This section is for system-level shortcuts (save/load state,\n"
  "# fullscreen, pause, etc.). The 12 SNES controller buttons live\n"
  "# in keybinds.ini next to the executable.\n"
  "Fullscreen = Alt+Return\n"
  "Reset = Ctrl+r\n"
  "Pause = Shift+p\n"
  "PauseDimmed = p\n"
  "Turbo = Tab\n"
  "WindowBigger = Ctrl+Up\n"
  "WindowSmaller = Ctrl+Down\n"
  "VolumeUp = Shift+=\n"
  "VolumeDown = Shift+-\n"
  "Load =      F1,     F2,     F3,     F4,     F5,     F6,     F7,     F8,     F9,     F10\n"
  "Save = Shift+F1,Shift+F2,Shift+F3,Shift+F4,Shift+F5,Shift+F6,Shift+F7,Shift+F8,Shift+F9,Shift+F10\n"
  "\n"
  "[GamepadMap]\n"
  "# Enable each player's gamepad slot.\n"
  "EnableGamepad1 = true\n"
  "EnableGamepad2 = true\n"
  "\n"
  "# Default Xbox-layout mapping. Order matches kKeys_Controls:\n"
  "#   Up, Down, Left, Right, Select, Start, A, B, X, Y, L, R\n"
  "Controls =   DpadUp, DpadDown, DpadLeft, DpadRight, Back, Start, B, A, Y, X, Lb, Rb\n"
  "ControlsP2 = DpadUp, DpadDown, DpadLeft, DpadRight, Back, Start, B, A, Y, X, Lb, Rb\n";

static void EnsureConfigIni(void) {
  FILE *f = fopen("config.ini", "rb");
  if (f) {
    fclose(f);
  } else {
    f = fopen("config.ini", "w");
    if (!f) {
      fprintf(stderr, "Warning: could not write default config.ini\n");
    } else {
      fputs(kDefaultConfigIniContent, f);
      fclose(f);
      printf("[config.ini] Generated default config next to the executable\n");
    }
  }
}

int main(int argc, char** argv) {
#ifndef _WIN32
    signal(SIGSEGV, crash_handler);
#endif
    signal(SIGABRT, crash_handler);
#ifdef _WIN32
    SetUnhandledExceptionFilter(seh_handler);
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
#endif
    atexit(post_mortem_atexit);
    host_report_init("Star Ocean (Japan)", "dev");
    cpu_trace_init();
    cpu_trace_arm_default_watches();
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);
#ifdef __SWITCH__
    SwitchImpl_Init();
#endif
    argc--, argv++;
    const char *config_file = NULL;
    if (argc >= 2 && strcmp(argv[0], "--config") == 0) {
        static char config_abs[1024];
        config_file = AbsolutizePathArg(argv[1], config_abs, sizeof(config_abs));
        argc -= 2, argv += 2;
    }
    int start_paused = 0;
    if (argc >= 1 && strcmp(argv[0], "--paused") == 0) {
        start_paused = 1;
        argc -= 1, argv += 1;
    }
    const char *script_file = NULL;
    if (argc >= 2 && strcmp(argv[0], "--script") == 0) {
        static char script_abs[1024];
        script_file = AbsolutizePathArg(argv[1], script_abs, sizeof(script_abs));
        argc -= 2, argv += 2;
    }
    const char *framedump_dir = NULL;
    if (argc >= 2 && strcmp(argv[0], "--framedump") == 0) {
        static char framedump_abs[1024];
        framedump_dir = AbsolutizePathArg(argv[1], framedump_abs, sizeof(framedump_abs));
        argc -= 2, argv += 2;
    }
    int force_launcher = 0;
    if (argc >= 1 && strcmp(argv[0], "--launcher") == 0) {
        force_launcher = 1;
        argc -= 1, argv += 1;
    }
    if (argc >= 1 && argv[0] && argv[0][0] != '-' && argv[0][0] != '\0') {
        static char rom_abs[1024];
        argv[0] = (char *)AbsolutizePathArg(argv[0], rom_abs, sizeof(rom_abs));
    }

    {
        extern int snesrecomp_anchor_to_exe_dir(void);
        int anchored = snesrecomp_anchor_to_exe_dir();
        host_report_breadcrumb("exe-dir anchor: %s",
                            anchored ? "ok" : "declined (cwd stays authoritative)");
    }

    {
        /* Passive input logger: only records (frame, joypad-state) changes when
         * SNESRECOMP_INPUT_LOG points at a file. Never overrides the keyboard. */
        const char *input_log_path = getenv("SNESRECOMP_INPUT_LOG");
        if (input_log_path && *input_log_path)
            g_input_log = fopen(input_log_path, "a");
        const char *replay_path = getenv("SNESRECOMP_REPLAY_FILE");
        if (replay_path && *replay_path)
            replay_load(replay_path);
    }

    if (!config_file)
        EnsureConfigIni();
    static char config_exe_path[1024];
    if (!config_file &&
        snesrecomp_exe_dir_path("config.ini", config_exe_path, sizeof(config_exe_path)))
        config_file = config_exe_path;
    ParseConfigFile(config_file);
    g_active_config_file = config_file;
    {
        FILE *f_local = fopen("config.local.ini", "rb");
        if (f_local) {
            fclose(f_local);
            ParseConfigFile("config.local.ini");
        }
    }
    host_report_breadcrumb(
        "config parsed: output=%d new_renderer=%d scale=%d fullscreen=%d "
        "audio=%d freq=%d samples=%d skip_launcher=%d",
        g_config.output_method, g_config.new_renderer, g_config.window_scale,
        g_config.fullscreen, g_config.enable_audio, g_config.audio_freq,
        g_config.audio_samples, g_config.skip_launcher);

    static char rom_path_buf[512];
    int mods_ready = 0;
    {
        int rom_resolved_by_launcher = 0;

#if defined(SNES_LAUNCHER) || defined(RECOMP_LAUNCHER)
        int headless = start_paused || (script_file != NULL) || (framedump_dir != NULL);
        int have_positional = (argc >= 1 && argv[0] && argv[0][0] != '-' && argv[0][0] != '\0');
        const char *no_launcher = getenv("SNESRECOMP_NO_LAUNCHER");
        int want_launcher = !headless && !have_positional && !(no_launcher && *no_launcher);

        if (want_launcher && g_config.skip_launcher && !force_launcher) {
            char cached[512]; cached[0] = '\0';
            if (snesrecomp_rom_cache_read(cached, sizeof(cached))) {
                FILE *probe = fopen(cached, "rb");
                if (probe) {
                    fclose(probe);
                    snprintf(rom_path_buf, sizeof(rom_path_buf), "%s", cached);
                    rom_resolved_by_launcher = 1;
                    want_launcher = 0;
                    host_report_breadcrumb("launcher skipped (SkipLauncher=1, cached rom)");
                }
            }
        }

        if (want_launcher) {
            // TODO: launcher GUI
            fprintf(stderr, "GUI launcher not implemented in minimal test build\n");
        }
#endif

        if (!rom_resolved_by_launcher) {
            char *la_argv[2] = {
                (char *)"so",
                (char *)((argc >= 1 && argv[0]) ? argv[0] : "")
            };
            int la_argc = (la_argv[1][0] != '\0') ? 2 : 1;
            static const uint8_t kSoRomSha256[32] = {
                0xEF, 0xAE, 0x37, 0xBE, 0x83, 0x2D, 0x0E, 0xA1,
                0x49, 0x07, 0x84, 0xD5, 0x7B, 0xEF, 0x00, 0x76,
                0x1A, 0x8B, 0xF0, 0xB5, 0xBC, 0xEF, 0x9C, 0x23,
                0xF5, 0x58, 0xE0, 0x63, 0x44, 0x1C, 0x38, 0x76
            };
            if (!snesrecomp_launcher_resolve_rom_sha256(la_argc, la_argv, rom_path_buf,
                                                        sizeof(rom_path_buf), kSoRomSha256)) {
                return 1;
            }
        }
    }
    if (!start_paused && script_file == NULL && framedump_dir == NULL) {
        if (RelocateRomToExeDir(rom_path_buf, sizeof(rom_path_buf))) {
            snesrecomp_rom_cache_write(rom_path_buf);
        }
    }

    static char *resolved_argv[2];
    resolved_argv[0] = rom_path_buf;
    resolved_argv[1] = NULL;
    argv = resolved_argv;
    argc = 1;
    host_report_breadcrumb("rom resolved: %s", rom_path_buf);

    {
        extern int debug_server_init(int port);
        extern void debug_server_set_ram(uint8_t *ram, uint32_t ram_size);
        if (debug_server_init(13308) == 0) {
#if SNESRECOMP_TRACE
            fprintf(stderr, "[main] Debug server ready on port %d\n", 13308);
#endif
        }
        if (start_paused) {
            debug_server_start_paused();
#if SNESRECOMP_TRACE
            fprintf(stderr, "[main] Started paused -- send 'step N' or 'continue' via TCP\n");
#endif
        }
    }

    g_gamepad[0].joystick_id = g_gamepad[1].joystick_id = -1;
    g_snes_width = 256;
    g_snes_height = 224;
    g_ppu_render_flags = g_config.new_renderer * kPpuRenderFlags_NewRenderer |
        g_config.no_sprite_limits * kPpuRenderFlags_NoSpriteLimits;

    if (g_config.fullscreen == 1)
        g_win_flags ^= SNESRECOMP_SDL_WINDOW_FULLSCREEN_DESKTOP;
    else if (g_config.fullscreen == 2)
        g_win_flags ^= SDL_WINDOW_FULLSCREEN;

    g_current_window_scale = (g_config.window_scale == 0) ? 2 : IntMin(g_config.window_scale, kMaxWindowScale);

    if (g_config.audio_freq < 11025 || g_config.audio_freq > 48000)
        g_config.audio_freq = kDefaultFreq;

    if (g_config.audio_channels < 1 || g_config.audio_channels > 2)
        g_config.audio_channels = kDefaultChannels;

    if (g_config.audio_samples <= 0 || ((g_config.audio_samples & (g_config.audio_samples - 1)) != 0))
        g_config.audio_samples = kDefaultSamples;

    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, "1");

    if (!snesrecomp_sdl_init(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_GAMECONTROLLER)) {
        host_report_breadcrumb("SDL_Init FAILED: %s", SDL_GetError());
        printf("Failed to init SDL: %s\n", SDL_GetError());
        return 1;
    }
    host_report_breadcrumb("SDL init ok: video=%s audio=%s",
                        SDL_GetCurrentVideoDriver() ? SDL_GetCurrentVideoDriver() : "(none)",
                        SDL_GetCurrentAudioDriver() ? SDL_GetCurrentAudioDriver() : "(none)");

    keybinds_init(NULL);

    bool custom_size = g_config.window_width != 0 && g_config.window_height != 0;
    int window_width = custom_size ? g_config.window_width :
        g_current_window_scale * 256;
    int window_height = custom_size ? g_config.window_height :
        g_current_window_scale * 224;

    if (g_config.output_method == kOutputMethod_OpenGL) {
        g_win_flags |= SDL_WINDOW_OPENGL;
        // OpenGLRenderer_Create(&g_renderer_funcs); // Not implemented in minimal test
    } else {
        g_renderer_funcs = kSdlRendererFuncs;
    }

    uint8 *kRom = NULL;
    uint32 kRom_SIZE = 0;
    if (argv[0]) {
        size_t size;
        kRom = ReadWholeFile(argv[0], &size);
        kRom_SIZE = (uint32)size;
        if (!kRom)
            goto error_reading;
    }
    host_report_breadcrumb("rom loaded: %u bytes", kRom_SIZE);

    extern const RtlGameInfo kSoGameInfo;
    RtlRegisterGame(&kSoGameInfo);
    Snes *snes = SnesInit(kRom, kRom_SIZE);
    host_report_breadcrumb("SnesInit: %s", snes ? "ok" : "FAILED");
    if (snes == NULL) {
error_reading:;
#ifdef __SWITCH__
        ThrowMissingROM();
#else
        char buf[256];
        snprintf(buf, sizeof(buf), "unable to load rom");
        Die(buf);
#endif
        return 1;
    }

    {
        extern void debug_server_set_ram(uint8_t *ram, uint32_t ram_size);
        debug_server_set_ram(snes->ram, 0x20000);
    }

    g_spc_player = SoSpcPlayer_Create();
    g_spc_player->initialize(g_spc_player);

    if (g_config.enable_audio) {
        g_audio_mutex = SDL_CreateMutex();
        if (!g_audio_mutex) Die("Failed to create audio mutex");

        g_audio_channels = (uint8)g_config.audio_channels;
        size_t audio_buffer_size = g_frames_per_block * g_audio_channels * sizeof(int16);

#if SNESRECOMP_SDL3
        SDL_AudioSpec spec = {0};
        spec.format = SDL_AUDIO_S16;
        spec.channels = g_audio_channels;
        spec.freq = g_config.audio_freq;
        g_audio_stream = SDL_CreateAudioStream(&spec, NULL);
        if (!g_audio_stream) Die("Failed to create audio stream");
        /* SDL3: open the device first, then bind the stream. */
        g_audio_device = SDL_OpenAudioDevice(SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK, &spec);
        if (!g_audio_device) Die("Failed to open audio device");
        if (!SDL_BindAudioStream(g_audio_device, g_audio_stream))
            Die("Failed to bind audio stream to device");
        /* Register a get-callback so SDL3 pulls audio data when the device
         * needs more samples. Without this the stream stays silent. */
        if (!SDL_SetAudioStreamGetCallback(g_audio_stream, AudioStreamCallback, NULL))
            Die("Failed to set audio stream callback");
        g_audio_stream_buffer_size = audio_buffer_size;
        g_audio_stream_buffer = (uint8 *)malloc(g_audio_stream_buffer_size);
        g_frames_per_block = (534 * spec.freq + 32040 / 2) / 32040;
        RtlSetAudioOutputRate(spec.freq);
#else
        SDL_AudioSpec want = {0}, have;
        want.freq = g_config.audio_freq;
        want.format = AUDIO_S16;
        want.channels = g_audio_channels;
        want.samples = g_config.audio_samples;
        want.callback = AudioCallback;
        want.userdata = NULL;
        g_audio_device = SDL_OpenAudioDevice(NULL, 0, &want, &have, SDL_AUDIO_ALLOW_FORMAT_CHANGE);
        if (g_audio_device == 0) Die("Failed to open audio device");
        SDL_PauseAudioDevice(g_audio_device, 0);
        /* One native DSP block is 534 samples at the SPC's true output rate
         * of 32040 Hz. Round the per-block frame count for the device rate. */
        g_frames_per_block = (534 * have.freq + 32040 / 2) / 32040;
        RtlSetAudioOutputRate(have.freq);
#endif
        audio_buffer_size = g_frames_per_block * g_audio_channels * sizeof(int16);
        g_audiobuffer = (uint8 *)malloc(audio_buffer_size * 2);
        g_audiobuffer_cur = g_audiobuffer;
        g_audiobuffer_end = g_audiobuffer;
    }

    if (g_config.output_method == kOutputMethod_OpenGL) {
        // OpenGLRenderer_Create(&g_renderer_funcs); // Not implemented
    } else {
        g_renderer_funcs = kSdlRendererFuncs;
    }

    g_window = snesrecomp_sdl_create_window(kWindowTitle, window_width, window_height, g_win_flags);
    if (!g_window) Die("Failed to create window");

    SDL_SetWindowHitTest(g_window, HitTestCallback, NULL);

    if (!g_renderer_funcs.Initialize(g_window))
        Die("Renderer init failed");

    MkDir("saves");
    RtlReadSram();

    {
#if SNESRECOMP_SDL3
        int njs_count = 0;
        SDL_JoystickID *njs_list = SDL_GetJoysticks(&njs_count);
        printf("[Gamepad] SDL reports %d joystick(s) at startup. enable_gamepad=[%d,%d]\n",
               njs_count, g_config.enable_gamepad[0], g_config.enable_gamepad[1]);
        for (int i = 0; i < njs_count; i++) {
            SDL_JoystickID joy_id = njs_list[i];
            const char *name = SDL_GetJoystickNameForID(joy_id);
            int is_gc = SDL_IsGamepad(joy_id);
            printf("[Gamepad]   #%d name=%s is_game_controller=%d\n",
                   i, name ? name : "(null)", is_gc);
            OpenOneGamepad(joy_id);
        }
        if (njs_count == 0) {
#else
        int njs = SDL_NumJoysticks();
        printf("[Gamepad] SDL reports %d joystick(s) at startup. enable_gamepad=[%d,%d]\n",
               njs, g_config.enable_gamepad[0], g_config.enable_gamepad[1]);
        for (int i = 0; i < njs; i++) {
            const char *name = SDL_JoystickNameForIndex(i);
            int is_gc = SDL_IsGameController(i);
            printf("[Gamepad]   #%d name=%s is_game_controller=%d\n",
                   i, name ? name : "(null)", is_gc);
            OpenOneGamepad(i);
        }
        if (njs == 0) {
#endif
            printf("[Gamepad] No joysticks detected. "
                   "On Windows, plug controller in BEFORE launching, "
                   "or check that XInput drivers are installed.\n");
        }
    }

    uint8 audiopaused = true;
    while (true) {
        uint64 frame_start = SDL_GetPerformanceCounter();

        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            switch (event.type) {
            case SDL_QUIT:
                goto quit;
            case SDL_CONTROLLERDEVICEADDED:
                OpenOneGamepad(SNESRECOMP_SDL_EVENT_DEVICE(event));
                break;
            case SDL_CONTROLLERDEVICEREMOVED: {
                GamepadInfo *gi = GetGamepadInfo(SNESRECOMP_SDL_EVENT_DEVICE(event));
                if (gi) {
                    memset(gi, 0, sizeof(GamepadInfo));
                    gi->joystick_id = -1;
                }
                break;
            }
            case SDL_CONTROLLERAXISMOTION: {
                GamepadInfo *gi = GetGamepadInfo(SNESRECOMP_SDL_EVENT_AXIS_DEVICE(event));
                if (gi) HandleGamepadAxisInput(gi, SNESRECOMP_SDL_EVENT_AXIS(event), SNESRECOMP_SDL_EVENT_AXIS_VALUE(event));
                break;
            }
            case SDL_CONTROLLERBUTTONDOWN:
            case SDL_CONTROLLERBUTTONUP: {
                GamepadInfo *gi = GetGamepadInfo(SNESRECOMP_SDL_EVENT_BUTTON_DEVICE(event));
                if (gi) {
                    int b = RemapSdlButton(SNESRECOMP_SDL_EVENT_BUTTON(event));
                    if (b >= 0)
                        HandleGamepadInput(gi, b, event.type == SDL_CONTROLLERBUTTONDOWN);
                }
                break;
            }
            case SDL_JOYDEVICEADDED:
                OpenOneJoystick(event.jdevice.which);
                break;
            case SDL_JOYDEVICEREMOVED: {
                GamepadInfo *gi = GetGamepadInfo(event.jdevice.which);
                if (gi) {
                    if (gi->joystick) SDL_JoystickClose(gi->joystick);
                    memset(gi, 0, sizeof(GamepadInfo));
                    gi->joystick_id = -1;
                }
                break;
            }
            case SDL_JOYAXISMOTION: {
                GamepadInfo *gi = GetGamepadInfo(event.jaxis.which);
                if (gi && gi->raw_joystick)
                    HandleGamepadAxisInput(gi, event.jaxis.axis, event.jaxis.value);
                break;
            }
            case SDL_JOYBUTTONDOWN:
            case SDL_JOYBUTTONUP: {
                GamepadInfo *gi = GetGamepadInfo(event.jbutton.which);
                if (gi && gi->raw_joystick && event.jbutton.button < 16) {
                    static const uint8 raw_buttons[] = {
                        kGamepadBtn_A, kGamepadBtn_B, kGamepadBtn_X, kGamepadBtn_Y,
                        kGamepadBtn_Back, kGamepadBtn_Guide, kGamepadBtn_Start,
                        kGamepadBtn_L3, kGamepadBtn_R3, kGamepadBtn_L1, kGamepadBtn_R1,
                        kGamepadBtn_DpadUp, kGamepadBtn_DpadDown,
                        kGamepadBtn_DpadLeft, kGamepadBtn_DpadRight
                    };
                    HandleGamepadInput(gi, raw_buttons[event.jbutton.button],
                                       event.type == SDL_JOYBUTTONDOWN);
                }
                break;
            }
            case SDL_MOUSEWHEEL:
                if (SDL_GetModState() & KMOD_CTRL && event.wheel.y != 0)
                    ChangeWindowScale(event.wheel.y > 0 ? 1 : -1);
                break;
            case SDL_KEYDOWN:
                HandleInput(SNESRECOMP_SDL_EVENT_KEY(event), SNESRECOMP_SDL_EVENT_MOD(event), true);
                break;
            case SDL_KEYUP:
                HandleInput(SNESRECOMP_SDL_EVENT_KEY(event), SNESRECOMP_SDL_EVENT_MOD(event), false);
                break;
#if SNESRECOMP_SDL3
            case SDL_EVENT_WINDOW_RESIZED: {
                int w = event.window.data1;
                int h = event.window.data2;
                if (g_renderer_funcs.GetOutputSize)
                    g_renderer_funcs.GetOutputSize(&w, &h);
                break;
            }
#else
            case SDL_WINDOWEVENT:
                if (event.window.event == SDL_WINDOWEVENT_RESIZED) {
                    int w = event.window.data1;
                    int h = event.window.data2;
                    if (g_renderer_funcs.GetOutputSize)
                        g_renderer_funcs.GetOutputSize(&w, &h);
                }
                break;
#endif
            }
        }

        if (g_paused != audiopaused) {
            audiopaused = g_paused;
            if (g_audio_device)
                SetAudioPaused(audiopaused != 0);
        }

        if (g_paused) {
            SDL_Delay(16);
            continue;
        }

        // Clear gamepad axis inputs when keyboard directions are pressed
        if (g_input_state & 0xf0)
            g_gamepad[0].axis_buttons = 0;
        if (g_input_state & 0xf0000)
            g_gamepad[1].axis_buttons = 0;

        /* Drive the SNES controller bits in g_input_state from keybinds.ini.
         * config.ini's [KeyMap] still owns system commands; the 12 controller
         * buttons per player come from keybinds.ini. */
        {
            const uint8_t *keys = snesrecomp_sdl_get_keyboard_state();
            uint16_t kb_p1 = keybinds_read_player(keys, 1);
            uint16_t kb_p2 = keybinds_read_player(keys, 2);
            static const uint8 kKb2CtrlsIdx[12] = { 7, 6, 5, 4, 9, 8, 3, 11, 2, 10, 1, 0 };
            for (int i = 0; i < 12; i++) {
                HandleCommand(kKeys_Controls + i, (kb_p1 >> kKb2CtrlsIdx[i]) & 1);
                HandleCommand(kKeys_ControlsP2 + i, (kb_p2 >> kKb2CtrlsIdx[i]) & 1);
            }
        }

        uint32 inputs = g_input_state | g_pad_buttons |
            g_gamepad[0].axis_buttons | g_gamepad[1].axis_buttons << 12;
        if (s_replay_loaded) {
            uint16_t rmask = replay_mask_for_frame(snes_frame_counter);
            uint16_t rprev = replay_mask_for_frame(snes_frame_counter - 1);
            inputs |= rmask;
            /* Pause once per Up-press transition so the scene change is
             * visible; SDL_Delay only sleeps the host, guest timing is
             * untouched (the phase log still measures real emu cost). */
            if ((rmask & 0x10) && !(rprev & 0x10) && s_replay_up_pause_ms > 0)
                SDL_Delay(s_replay_up_pause_ms);
        }
        if (g_input_log && inputs != g_last_logged_input) {
            fprintf(g_input_log, "%d %08x\n", snes_frame_counter, inputs);
            fflush(g_input_log);
            g_last_logged_input = inputs;
        }
        /* Phase timing (dev): SNESRECOMP_PHASE_MS=1 logs avg ms of
         * RtlRunFrame vs DrawPpuFrame every 120 frames to stderr. */
        uint64 t_emu0 = SDL_GetPerformanceCounter();
        RtlRunFrame(inputs | GetActiveControllers() |
                    debug_server_get_controller_inputs() |
                    debug_server_get_controller_active_mask());
        uint64 t_emu1 = SDL_GetPerformanceCounter();
        /* Per-frame guest master_cycles (dev): SNESRECOMP_MC_LOG=1 logs
         * "frame master" to stderr — used to A/B the VFF guards (VFF ON vs
         * SNESRECOMP_NO_VBLANK_FF=1 must yield identical masters if every
         * fast-forward is bit-exact). No effect in normal play. */
        { static int s_mc_on = -1;
          if (s_mc_on < 0) s_mc_on = getenv("SNESRECOMP_MC_LOG") ? 1 : 0;
          if (s_mc_on) {
            extern CpuState g_cpu;
            extern int snes_frame_counter;
            fprintf(stderr, "[mc] frame %d master=%llu\n", snes_frame_counter,
                    (unsigned long long)g_cpu.master_cycles);
          } }

        g_snes->disableRender = 0;
        DrawPpuFrameWithPerf();
        uint64 t_draw1 = SDL_GetPerformanceCounter();
        {
            static int s_phase_n = 0;
            static double s_phase_emu = 0, s_phase_draw = 0;
            static int s_phase_on = -1;
            if (s_phase_on < 0) s_phase_on = getenv("SNESRECOMP_PHASE_MS") ? 1 : 0;
            if (s_phase_on) {
                s_phase_emu += (double)(t_emu1 - t_emu0) * 1000.0 / SDL_GetPerformanceFrequency();
                s_phase_draw += (double)(t_draw1 - t_emu1) * 1000.0 / SDL_GetPerformanceFrequency();
#ifdef SNESRECOMP_INTERP_PROFILE
                extern void rtl_apu_perf_snapshot(uint64_t *, uint64_t *);
                static uint64_t s_p_apu_ns = 0, s_p_apu_calls = 0;
                uint64_t apu_ns = 0, apu_calls = 0;
                rtl_apu_perf_snapshot(&apu_ns, &apu_calls);
                if (s_phase_n == 0) {
                    s_p_apu_ns = apu_ns; s_p_apu_calls = apu_calls;
                }
#endif
                if (++s_phase_n >= 120) {
#ifdef SNESRECOMP_INTERP_PROFILE
                    double apu_ms = (double)(apu_ns - s_p_apu_ns) / 1e6;
                    fprintf(stderr, "[phase] emu=%.2fms draw=%.2fms total=%.2fms -> %.1f FPS | apuSync=%.2fms(%.0f%% emu,%llu calls)\n",
                            s_phase_emu / s_phase_n, s_phase_draw / s_phase_n,
                            (s_phase_emu + s_phase_draw) / s_phase_n,
                            1000.0 / ((s_phase_emu + s_phase_draw) / s_phase_n),
                            apu_ms,
                            s_phase_emu / s_phase_n > 0 ? 100.0 * apu_ms / (s_phase_emu / s_phase_n) : 0.0,
                            (unsigned long long)(apu_calls - s_p_apu_calls));
                    extern void interp816_perf_dump(void);
                    interp816_perf_dump();
                    extern void interp816_opcode_hist_dump(void);
                    interp816_opcode_hist_dump();
#else
                    fprintf(stderr, "[phase] emu=%.2fms draw=%.2fms total=%.2fms -> %.1f FPS\n",
                            s_phase_emu / s_phase_n, s_phase_draw / s_phase_n,
                            (s_phase_emu + s_phase_draw) / s_phase_n,
                            1000.0 / ((s_phase_emu + s_phase_draw) / s_phase_n));
#endif
                    s_phase_n = 0; s_phase_emu = s_phase_draw = 0;
                }
            }
        }

        /* Live FPS in the window title (like the bsnes-plus status bar). */
        {
            static int s_fps_frames = 0;
            static Uint64 s_fps_last = 0;
            s_fps_frames++;
            Uint64 now = SDL_GetTicks();
            double elapsed = (double)(now - s_fps_last) / 1000.0;
            if (elapsed >= 1.0) {
                g_curr_fps = (int)(s_fps_frames / elapsed + 0.5);
                s_fps_frames = 0;
                s_fps_last = now;
                char title[160];
                extern int snes_frame_counter;
                snprintf(title, sizeof(title), "%s | f%d | %d FPS",
                         kWindowTitle, snes_frame_counter, g_curr_fps);
                SDL_SetWindowTitle(g_window, title);
            }
        }

        if (g_turbo) {
            SDL_Delay(1);
        } else if (!g_config.disable_frame_delay) {
            uint64 frame_end = SDL_GetPerformanceCounter();
            double frame_ms = (double)(frame_end - frame_start) * 1000.0 / SDL_GetPerformanceFrequency();
            double target_ms = 1000.0 / 60.0;
            if (frame_ms < target_ms)
                SDL_Delay((Uint32)(target_ms - frame_ms));
        }
    }

quit:
    if (g_input_log) {
        fclose(g_input_log);
        g_input_log = NULL;
    }
    RtlWriteSram();
    SetAudioPaused(true);
    if (g_audio_device) {
#if SNESRECOMP_SDL3
        SDL_DestroyAudioStream(g_audio_stream);
        free(g_audio_stream_buffer);
        SDL_CloseAudioDevice(g_audio_device);
#else
        SDL_CloseAudioDevice(g_audio_device);
#endif
    }
    if (g_audiobuffer) free(g_audiobuffer);
    if (g_audio_mutex) SDL_DestroyMutex(g_audio_mutex);

    g_renderer_funcs.Destroy();
    SDL_DestroyWindow(g_window);
    SDL_Quit();
    return 0;
}
