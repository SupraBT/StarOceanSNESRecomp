// drive_bsnesplus.cpp — Track-B oracle driver for bsnes-plus v0.5 (libsnes).
//
// Loads a ROM through the bsnes-plus heuristic (S-DD1 autodetected), feeds a
// per-frame joypad mask file (runner layout: bit k = JoypadID k, B..R), and
// runs N frames. The state record per frame is emitted by the SNESREF hook
// inside the core (env SNESREF_STATE_OUT=<path>), in the same layout as
// so_cosim --state-out, so cosim_trackb.py can diff them.
//
// Usage:
//   drive_bsnesplus.exe <rom.sfc> [--input start:duration:hexmask]...
//                       [--frames N] [--state-out <path>]
//
// Build (MSYS2):  g++ -O2 -I<bsnes>/snes/libsnes drive_bsnesplus.cpp \
//                   -L<bsnes> -llibsnes.a -o drive_bsnesplus.exe
//   (runtime needs snes.dll from the bsnes-plus library build next to the exe)

#include "libsnes.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

static std::vector<uint16_t> g_frame_masks;  // one 12-bit mask per frame (runner layout)
static unsigned g_frame_index = 0;

// ---------------------------------------------------------------------------
// libsnes interface callbacks
// ---------------------------------------------------------------------------

static int16_t input_state_cb(bool port, unsigned device, unsigned index, unsigned id) {
  (void)index;
  if (port == 0 && device == SNES_DEVICE_JOYPAD && id < 16) {
    uint16_t mask = (g_frame_index < g_frame_masks.size()) ? g_frame_masks[g_frame_index] : 0;
    if (id < 12) return (int16_t)((mask >> id) & 1);
    return 0;  // ids 12-15: no extra buttons on the recorded pads
  }
  return 0;  // port 2 always idle (the movie recorded no port-2 input)
}

static void input_poll_cb(void) {}
static void audio_sample_cb(uint16_t, uint16_t) {}

// Optional per-frame video capture: --video-out <prefix> saves raw BGR555
// 256x224 frames (512-byte rows) as <prefix>_%05u.raw for the frames in
// [video_first, video_last] (default: every frame).
static const char *g_video_prefix = 0;
static unsigned g_video_first = 0;
static unsigned g_video_last = 0xFFFFFFFFu;
static unsigned g_video_counter = 0;

static void video_refresh_cb(const uint16_t *data, unsigned width, unsigned height) {
  if (!g_video_prefix) return;
  if (g_video_counter < 3)
    fprintf(stderr, "[video_refresh_cb] counter=%u wxh=%ux%u prefix=%s\n",
            g_video_counter, width, height, g_video_prefix);
  if (g_video_counter < g_video_first || g_video_counter > g_video_last) {
    g_video_counter++;
    return;
  }
  if ((height == 224 || height == 239) && (width == 256 || width == 512)) {
    char name[512];
    snprintf(name, sizeof(name), "%s_%05u.raw", g_video_prefix, g_video_counter);
    FILE *f = fopen(name, "wb");
    if (f) {
      for (unsigned y = 0; y < height; y++)
        fwrite(data + y * 1024, 2, width, f);  // 1024-pixel row stride
      fclose(f);
    }
  }
  g_video_counter++;
}

// ---------------------------------------------------------------------------
// input events (same start:duration:hexmask contract as so_cosim --input)
// ---------------------------------------------------------------------------

static std::vector<std::pair<uint64_t, uint64_t>> s_event_ranges;  // start, duration
static std::vector<uint16_t> s_event_masks;

static bool add_input_event(const char *text) {
  unsigned long long start = 0, duration = 0;
  unsigned mask = 0;
  char trailing = '\0';
  if (sscanf(text, "%llu:%llu:%x%c", &start, &duration, &mask, &trailing) != 3 ||
      !duration || mask > 0xffffu)
    return false;
  s_event_ranges.push_back(std::make_pair(start, duration));
  s_event_masks.push_back((uint16_t)mask);
  return true;
}

static uint64_t total_needed_frames(uint64_t min_frames) {
  uint64_t n = min_frames;
  for (size_t i = 0; i < s_event_ranges.size(); i++)
    if (s_event_ranges[i].first + s_event_ranges[i].second > n)
      n = s_event_ranges[i].first + s_event_ranges[i].second;
  return n;
}

static void build_frame_masks() {
  uint64_t n = total_needed_frames(0);
  g_frame_masks.assign((size_t)n, 0);
  for (size_t e = 0; e < s_event_ranges.size(); e++) {
    uint64_t start = s_event_ranges[e].first;
    uint64_t dur = s_event_ranges[e].second;
    for (uint64_t f = start; f < start + dur && f < n; f++)
      g_frame_masks[(size_t)f] |= s_event_masks[e];
  }
}

static uint8_t *read_file(const char *path, size_t *size_out) {
  FILE *f = fopen(path, "rb");
  if (!f) return NULL;
  fseek(f, 0, SEEK_END);
  long n = ftell(f);
  fseek(f, 0, SEEK_SET);
  if (n <= 0) { fclose(f); return NULL; }
  uint8_t *buf = (uint8_t *)malloc((size_t)n);
  if (buf && fread(buf, 1, (size_t)n, f) != (size_t)n) { free(buf); buf = NULL; }
  fclose(f);
  if (buf) *size_out = (size_t)n;
  return buf;
}

int main(int argc, char **argv) {
  if (argc < 2) {
    fprintf(stderr,
      "usage: %s <rom.sfc> [--input start:duration:hexmask]... [--frames N]"
      " [--state-out <path>] [--video-out <prefix>] [--video-window A B]\n", argv[0]);
    return 2;
  }
  const char *rom = argv[1];
  const char *state_out = NULL;
  uint64_t frames = 0;
  const char *video_out = NULL;

  for (int i = 2; i < argc; i++) {
    if (!strcmp(argv[i], "--input") && i + 1 < argc) {
      if (!add_input_event(argv[++i])) {
        fprintf(stderr, "drive_bsnesplus: invalid input event '%s'\n", argv[i]);
        return 2;
      }
    } else if (!strcmp(argv[i], "--frames") && i + 1 < argc) {
      frames = strtoull(argv[++i], NULL, 0);
    } else if (!strcmp(argv[i], "--state-out") && i + 1 < argc) {
      state_out = argv[++i];
    } else if (!strcmp(argv[i], "--video-out") && i + 1 < argc) {
      video_out = argv[++i];
    } else if (!strcmp(argv[i], "--video-window") && i + 2 < argc) {
      g_video_first = (unsigned)strtoul(argv[++i], NULL, 0);
      g_video_last = (unsigned)strtoul(argv[++i], NULL, 0);
    } else {
      fprintf(stderr, "drive_bsnesplus: unknown arg '%s'\n", argv[i]);
      return 2;
    }
  }

  if (state_out) {
    char envbuf[2048];
    snprintf(envbuf, sizeof(envbuf), "SNESREF_STATE_OUT=%s", state_out);
    _putenv(envbuf);
  }
  g_video_prefix = video_out;

  build_frame_masks();
  if (!frames) frames = total_needed_frames(1);
  fprintf(stderr, "drive_bsnesplus: %llu frames, %zu input events, %zu masks\n",
          (unsigned long long)frames, s_event_ranges.size(), g_frame_masks.size());

  size_t rom_size = 0;
  uint8_t *rom_data = read_file(rom, &rom_size);
  if (!rom_data) {
    fprintf(stderr, "drive_bsnesplus: cannot read ROM '%s'\n", rom);
    return 1;
  }

  snes_set_video_refresh(video_refresh_cb);
  snes_set_audio_sample(audio_sample_cb);
  snes_set_input_poll(input_poll_cb);
  snes_set_input_state(input_state_cb);

  snes_init();
  snes_set_controller_port_device(0, SNES_DEVICE_JOYPAD);
  snes_set_controller_port_device(1, SNES_DEVICE_JOYPAD);

  if (!snes_load_cartridge_normal(NULL, rom_data, (unsigned)rom_size)) {
    fprintf(stderr, "drive_bsnesplus: snes_load_cartridge_normal failed\n");
    return 1;
  }
  fprintf(stderr, "drive_bsnesplus: ROM loaded (%u bytes), region=%s\n",
          (unsigned)rom_size, snes_get_region() == SNES_REGION_NTSC ? "NTSC" : "PAL");

  for (uint64_t f = 0; f < frames; f++) {
    g_frame_index = (unsigned)f;
    snes_run();
  }

  snes_unload_cartridge();
  snes_term();
  free(rom_data);
  fprintf(stderr, "drive_bsnesplus: done, %llu frames\n", (unsigned long long)frames);
  return 0;
}
