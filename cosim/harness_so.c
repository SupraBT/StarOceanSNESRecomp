/*
 * harness_so.c -- headless, deterministic Star Ocean entry for the differential
 * co-simulation A-side (SNES_COSIM.md). Replaces the SDL main.c: NO window, NO
 * host audio sink, NO worker threads -- the Gate-1 determinism requirement,
 * satisfied by construction. Boots the ROM and loops RtlRunFrame(input); the
 * cosim engine (cosim_init/cosim_frame, hooked inside RtlRunFrame) drives the
 * checkpoint lockstep with the coordinator.
 *
 * Input is supplied as frame-keyed events (identical to ref_driver.c):
 *   --input start:duration:hexmask      (press `mask` during [start, start+dur))
 * e.g. the recorded name-screen walk: --input 76:7:100 --input 171:8:100
 *                                      --input 234:7:100
 *
 * DEV/DIAGNOSTICS ONLY (built only under SNES_COSIM).
 *
 * Usage: harness_so <rom.sfc> [--input start:duration:hexmask]...
 * env: SNES_COSIM_PORT / SNES_COSIM_STRIDE / SNES_COSIM_AUDIO / SNES_COSIM_DRAW_PPU
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

#include "common_rtl.h"
#include "common_cpu_infra.h"
#include "cpu_state.h"
#include "snes/snes.h"
#include "snes/ppu.h"
#include "snes/cart.h"
#include "snes/sdd1.h"
#include "spc_player.h"
#include "so_spc_player.h"

/* Provided by the Star Ocean game sources linked alongside this harness. */
extern const RtlGameInfo kSoGameInfo;

/* main.c normally defines this global; the runner references it extern. Here
 * the harness owns it. */
struct SpcPlayer *g_spc_player;

static uint64_t s_frames; /* completed frames (RtlRunFrame calls) */

typedef struct InputEvent {
    uint64_t start;
    uint64_t duration;
    uint16_t mask;
} InputEvent;

static InputEvent s_input_events[2048];
static uint32_t s_input_event_count;

static bool add_input_event(const char *text) {
    unsigned long long start = 0;
    unsigned long long duration = 0;
    unsigned mask = 0;
    char trailing = '\0';
    if (s_input_event_count >= 2048 ||
        sscanf(text, "%llu:%llu:%x%c",
               &start, &duration, &mask, &trailing) != 3 ||
        !duration || mask > 0xffffu)
        return false;
    s_input_events[s_input_event_count++] = (InputEvent){
        (uint64_t)start, (uint64_t)duration, (uint16_t)mask
    };
    return true;
}

static uint16_t apply_frame_input(void) {
    uint16_t input = 0;
    for (uint32_t i = 0; i < s_input_event_count; i++) {
        InputEvent *event = &s_input_events[i];
        if (s_frames >= event->start &&
            s_frames - event->start < event->duration)
            input |= event->mask;
    }
    return input;
}

static uint8_t *read_file(const char *path, uint32_t *size_out) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (n <= 0) { fclose(f); return NULL; }
    uint8_t *buf = (uint8_t *)malloc((size_t)n);
    if (buf && fread(buf, 1, (size_t)n, f) != (size_t)n) { free(buf); buf = NULL; }
    fclose(f);
    if (buf) *size_out = (uint32_t)n;
    return buf;
}

static uint8_t s_video_pixels[256 * 4 * 256];
static bool s_render_video;
#ifdef SNESRECOMP_INTERP_PROFILE
extern uint64_t sdd1_prof_blocks, sdd1_prof_bytes;
extern double sdd1_prof_ms;
extern uint64_t g_interp_total_steps;
extern uint64_t apu_prof_calls;
extern double apu_prof_ms;
extern uint64_t dma_prof_bytes;
extern double dma_prof_ms;
extern uint64_t apuw_prof_calls;
extern double apuw_prof_ms;
extern uint64_t ppu_prof_calls;
extern double ppu_prof_ms;
extern uint64_t bridgeq_prof_calls;
extern double bridgeq_prof_ms;
extern uint64_t apub_prof_calls;
extern double apub_prof_ms;
extern uint64_t apus_prof_calls;
extern double apus_prof_ms;
extern uint64_t apucyc_prof_calls;
extern double apucyc_prof_ms;
extern void snes_catchup_stats(uint64_t *calls, uint64_t *cycles);
extern void aot_prof_frame_end(int frame);
#endif

/* ── Track-B per-frame state export (binary, shared with the bsnes oracle ──
 * Layout (little-endian), see bsnes target-libretro/state_snapshot.hpp:
 *   u32 frame; cpu 18B; dev 16B; ppu 66B; u64 ppuValid; sdd1 6B;
 *   wram 0x20000B; vram 0x10000B (0x8000 words); cgram 0x200B (0x100 words)
 * recordSize = 197238. */
static FILE *s_state_out;
static uint64_t s_state_frames;

static void put_u32(FILE *f, uint32_t v) { fwrite(&v, 4, 1, f); }
static void put_u16(FILE *f, uint16_t v) { fwrite(&v, 2, 1, f); }
static void put_u8(FILE *f, uint8_t v) { fwrite(&v, 1, 1, f); }

static bool state_open(const char *path) {
    if (!path || !path[0]) return true;
    s_state_out = fopen(path, "wb");
    if (!s_state_out) return false;
    char magic[4] = {'S', 'O', 'C', 'O'};
    uint32_t version = 1;
    uint32_t recordSize = 4 + 18 + 16 + 66 + 8 + 6 + 0x20000 + 0x10000 + 0x200;
    fwrite(magic, 1, 4, s_state_out);
    put_u32(s_state_out, version);
    put_u32(s_state_out, recordSize);
    return true;
}

static void state_record(const Snes *snes) {
    if (!s_state_out) return;
    extern CpuState g_cpu;
    extern uint8_t g_ram[0x20000];
    const CpuState *c = &g_cpu;
    const Ppu *p = g_ppu;

    put_u32(s_state_out, (uint32_t)s_frames);
    /* cpu */
    put_u32(s_state_out, 0);  /* pc24 unavailable on the recomp side */
    put_u16(s_state_out, c->A); put_u16(s_state_out, c->X); put_u16(s_state_out, c->Y);
    put_u16(s_state_out, c->S); put_u16(s_state_out, c->D);
    put_u8(s_state_out, c->DB); put_u8(s_state_out, c->P);
    put_u8(s_state_out, c->emulation ? 1 : 0); put_u8(s_state_out, 0);
    /* dev */
    put_u16(s_state_out, snes->hPos); put_u16(s_state_out, snes->vPos);
    put_u8(s_state_out, snes->inNmi ? 1 : 0);
    put_u8(s_state_out, snes->inIrq ? 1 : 0);
    put_u8(s_state_out, snes->inVblank ? 1 : 0);
    put_u8(s_state_out, snes->nmiEnabled ? 1 : 0);
    put_u8(s_state_out, snes->hIrqEnabled ? 1 : 0);
    put_u8(s_state_out, snes->vIrqEnabled ? 1 : 0);
    put_u16(s_state_out, snes->hTimer); put_u16(s_state_out, snes->vTimer);
    put_u16(s_state_out, 0);  /* pad: dev block is 16 B */
    /* ppu summary (66B) */
    put_u8(s_state_out, p->inidisp);
    put_u8(s_state_out, p->obsel);
    put_u8(s_state_out, p->oamaddl);
    put_u8(s_state_out, p->oamaddh);
    put_u8(s_state_out, p->bgmode);
    put_u8(s_state_out, p->mosaic);
    for (int i = 0; i < 4; i++) put_u8(s_state_out, p->bgXsc[i]);
    put_u16(s_state_out, p->bgTileAdr);
    put_u8(s_state_out, p->m7sel);
    put_u8(s_state_out, p->setini);
    for (int i = 0; i < 4; i++) put_u16(s_state_out, p->hScroll[i]);
    for (int i = 0; i < 4; i++) put_u16(s_state_out, p->vScroll[i]);
    for (int i = 0; i < 8; i++) put_u16(s_state_out, (uint16_t)p->m7matrix[i]);
    put_u16(s_state_out, p->fixedColor);
    put_u8(s_state_out, p->cgadsub);
    put_u8(s_state_out, p->cgwsel);
    put_u8(s_state_out, p->screenEnabled[0]);
    put_u8(s_state_out, p->screenEnabled[1]);
    put_u8(s_state_out, p->window1left);
    put_u8(s_state_out, p->window1right);
    put_u8(s_state_out, p->window2left);
    put_u8(s_state_out, p->window2right);
    put_u16(s_state_out, p->wbgobjlog);
    put_u16(s_state_out, p->vramPointer);
    put_u32(s_state_out, 0); put_u16(s_state_out, 0);  /* pad 6 */
    /* ppuValid: every byte above is filled from a real field on this side */
    uint64_t mask = ~0ull;
    fwrite(&mask, 8, 1, s_state_out);
    /* sdd1 mmio */
    const Sdd1 *sdd1 = cart_has_sdd1(snes->cart) ? snes->cart->sdd1 : NULL;
    uint8_t sm[6] = {0, 0, 0, 0, 0, 0};
    if (sdd1) {
        sm[0] = sdd1->r4800; sm[1] = sdd1->r4801;
        sm[2] = sdd1->r4804; sm[3] = sdd1->r4805;
        sm[4] = sdd1->r4806; sm[5] = sdd1->r4807;
    }
    fwrite(sm, 1, 6, s_state_out);
    /* wram / vram / cgram */
    fwrite(g_ram, 1, 0x20000, s_state_out);
    for (int i = 0; i < 0x8000; i++) put_u16(s_state_out, p->vram[i]);
    for (int i = 0; i < 0x100; i++) put_u16(s_state_out, p->cgram[i]);
    fflush(s_state_out);
}

static bool write_ppm(const char *path, const uint8_t *source) {
    if (!path || !path[0]) return true;
    FILE *f = fopen(path, "wb");
    if (!f) return false;
    fprintf(f, "P6\n256 224\n255\n");
    const uint32_t *pixels = (const uint32_t *)source;
    for (size_t i = 0; i < (size_t)256 * 224; i++) {
        uint8_t rgb[3] = {
            (uint8_t)(pixels[i] >> 16),
            (uint8_t)(pixels[i] >> 8),
            (uint8_t)pixels[i],
        };
        if (fwrite(rgb, 1, sizeof(rgb), f) != sizeof(rgb)) {
            fclose(f);
            return false;
        }
    }
    return fclose(f) == 0;
}

int main(int argc, char **argv) {
    const char *rom = (argc > 1) ? argv[1] : "so.sfc";
    const char *final_frame_dump = NULL;
    const char *state_out = NULL;
    uint64_t standalone_frames = 0;
    for (int i = 2; i < argc; i++) {
        if (!strcmp(argv[i], "--input") && i + 1 < argc) {
            if (!add_input_event(argv[++i])) {
                fprintf(stderr,
                        "cosim-harness: invalid input event; expected start:duration:hexmask\n");
                return 2;
            }
        } else if (!strcmp(argv[i], "--frames") && i + 1 < argc) {
            standalone_frames = strtoull(argv[++i], NULL, 0);
        } else if (!strcmp(argv[i], "--final-frame-dump") && i + 1 < argc) {
            final_frame_dump = argv[++i];
        } else if (!strcmp(argv[i], "--state-out") && i + 1 < argc) {
            state_out = argv[++i];
        } else {
            fprintf(stderr,
                    "usage: %s [rom.sfc] [--input start:duration:hexmask]... "
                    "[--frames N] [--final-frame-dump path] [--state-out path]\n",
                    argv[0]);
            return 2;
        }
    }
    if (!state_open(state_out)) {
        fprintf(stderr, "cosim-harness: cannot open --state-out '%s'\n", state_out);
        return 1;
    }
    s_render_video = standalone_frames != 0;
    uint32_t size = 0;
    uint8_t *data = read_file(rom, &size);
    if (!data) { fprintf(stderr, "cosim-harness: cannot read ROM '%s'\n", rom); return 1; }

    RtlRegisterGame(&kSoGameInfo);
    Snes *snes = SnesInit(data, (int)size);
    if (!snes) { fprintf(stderr, "cosim-harness: SnesInit failed\n"); return 1; }

    g_spc_player = SoSpcPlayer_Create();
    g_spc_player->initialize(g_spc_player);

    /* Point the PPU at a render buffer so draw_ppu_frame() (which renders PPU
     * lines + drives HDMA + fires the raster IRQ) can run headlessly under
     * SNES_COSIM_DRAW_PPU=1 without a NULL renderBuffer deref. Matches main.c's
     * PpuBeginDrawing(g_ppu, g_my_pixels, 256*4, 0). We never present the
     * pixels; we only need the IRQ/HDMA side effects for co-sim fidelity. */
    { extern Ppu *g_ppu;
      /* Use the same renderer the game ships (config new_renderer=1), so the
       * PPU phase split measures the path 2.Beta actually runs. Flags only
       * select the host renderer; they never touch guest state. */
      uint32_t rflags = 1u; /* kPpuRenderFlags_NewRenderer, ppu.h */
      if (g_ppu) PpuBeginDrawing(g_ppu, s_video_pixels, 256 * 4, rflags);
    }

    fprintf(stderr, "cosim-harness(so): booted headless; %u input event(s)\n",
            s_input_event_count);
    if (!standalone_frames)
        for (;;) {
            uint16_t input = apply_frame_input();
            RtlRunFrame(input);
            s_frames++;
        }
    /* Per-frame host-time diagnostic: SNESRECOMP_FRAME_TIMING=1 records the
     * slowest frames (guest frame -> ms) and a ms-histogram, dumped at exit.
     * Dev-only harness instrumentation; the desktop builds never see it. */
    struct { uint64_t frame; double ms; uint64_t steps; } slow[32];
    unsigned slow_n = 0;
    int ft_hist[64];
    memset(ft_hist, 0, sizeof ft_hist);
    const int frame_timing = getenv("SNESRECOMP_FRAME_TIMING") != NULL;
    for (; s_frames < standalone_frames; s_frames++) {
        uint16_t input = apply_frame_input();
        double _t0 = 0.0;
        if (frame_timing) _t0 = (double)clock() / CLOCKS_PER_SEC;
        RtlRunFrame(input);
#ifdef SNESRECOMP_INTERP_PROFILE
        aot_prof_frame_end((int)s_frames);
#endif
        { static int _mc = -1;
          if (_mc < 0) { const char *_e = getenv("SNESRECOMP_MC_LOG");
                         _mc = (_e && _e[0] && _e[0] != '0') ? 1 : 0; }
          if (_mc) { extern CpuState g_cpu;
                     fprintf(stderr, "[mc] frame %llu master=%llu\n",
                             (unsigned long long)s_frames,
                             (unsigned long long)g_cpu.master_cycles); } }
        if (frame_timing) {
            double ms = 1000.0 * ((double)clock() / CLOCKS_PER_SEC - _t0);
            uint64_t steps_this = 0; /* step counter not exposed by the runner */
            int b = (int)(ms / 2.0);
            if (b >= 64) b = 63;
            if (b < 0) b = 0;
            ft_hist[b]++;
            if (ms >= 8.0) {
                if (slow_n < 32) {
                    slow[slow_n].frame = s_frames; slow[slow_n].ms = ms;
                    slow[slow_n].steps = steps_this; slow_n++;
                } else {
                    unsigned k = 0;
                    for (unsigned j = 1; j < slow_n; j++)
                        if (slow[j].ms > slow[k].ms) k = j;
                    if (ms > slow[k].ms) { slow[k].frame = s_frames; slow[k].ms = ms; slow[k].steps = steps_this; }
                }
            }
        }
        state_record(snes);
    }
    if (frame_timing) {
        fprintf(stderr, "\n[frame_timing] ms histogram (bucket=2ms):\n");
        for (int b = 0; b < 64; b++)
            if (ft_hist[b])
                fprintf(stderr, "  %4d-%4d ms: %d\n", b * 2, b * 2 + 1, ft_hist[b]);
        fprintf(stderr, "[frame_timing] top slow frames (frame, ms, interp-steps):\n");
        for (unsigned j = 0; j < slow_n; j++)
            fprintf(stderr, "  f%llu  %.1f ms  %llu steps\n",
                    (unsigned long long)slow[j].frame, slow[j].ms,
                    (unsigned long long)slow[j].steps);
    }
#ifdef SNESRECOMP_INTERP_PROFILE
    if (sdd1_prof_blocks)
        fprintf(stderr, "[sdd1_profile] %llu blocks, %llu bytes, %.1f ms host over %llu frames (~%llu B/frame, %.2f ms/frame sdd1)\n",
                (unsigned long long)sdd1_prof_blocks,
                (unsigned long long)sdd1_prof_bytes,
                sdd1_prof_ms,
                (unsigned long long)s_frames,
                (unsigned long long)(s_frames ? sdd1_prof_bytes / s_frames : 0),
                s_frames ? sdd1_prof_ms / (double)s_frames : 0.0);
    if (apu_prof_calls)
        fprintf(stderr, "[apu_profile] %llu flush calls, %.1f ms host over %llu frames (~%.2f ms/frame)\n",
                (unsigned long long)apu_prof_calls, apu_prof_ms,
                (unsigned long long)s_frames,
                s_frames ? apu_prof_ms / (double)s_frames : 0.0);
    if (dma_prof_bytes)
        fprintf(stderr, "[dma_profile] %llu bytes, %.1f ms host over %llu frames (~%.2f ms/frame)\n",
                (unsigned long long)dma_prof_bytes, dma_prof_ms,
                (unsigned long long)s_frames,
                s_frames ? dma_prof_ms / (double)s_frames : 0.0);
    if (apuw_prof_calls)
        fprintf(stderr, "[apuw_profile] %llu RtlApuWrite calls, %.1f ms host over %llu frames (~%.2f ms/frame)\n",
                (unsigned long long)apuw_prof_calls, apuw_prof_ms,
                (unsigned long long)s_frames,
                s_frames ? apuw_prof_ms / (double)s_frames : 0.0);
    if (ppu_prof_calls)
        fprintf(stderr, "[ppu_profile] %llu draw calls, %.1f ms host over %llu frames (~%.2f ms/frame)\n",
                (unsigned long long)ppu_prof_calls, ppu_prof_ms,
                (unsigned long long)s_frames,
                s_frames ? ppu_prof_ms / (double)s_frames : 0.0);
    if (bridgeq_prof_calls)
        fprintf(stderr, "[bridgeq_profile] %llu calls, %.1f ms host over %llu frames (~%.2f ms/frame)\n",
                (unsigned long long)bridgeq_prof_calls, bridgeq_prof_ms,
                (unsigned long long)s_frames,
                s_frames ? bridgeq_prof_ms / (double)s_frames : 0.0);
    if (apub_prof_calls)
        fprintf(stderr, "[apub_profile] %llu boundary calls, %.1f ms host over %llu frames (~%.2f ms/frame)\n",
                (unsigned long long)apub_prof_calls, apub_prof_ms,
                (unsigned long long)s_frames,
                s_frames ? apub_prof_ms / (double)s_frames : 0.0);
    if (apus_prof_calls)        fprintf(stderr, "[apus_profile] %llu cpu-sync calls, %.1f ms host over %llu frames (~%.2f ms/frame)\n",
                (unsigned long long)apus_prof_calls,
                apus_prof_ms,
                (unsigned long long)s_frames,
                s_frames ? apus_prof_ms / (double)s_frames : 0.0);
        fprintf(stderr, "[apucyc_profile] %llu catchup calls, %.1f ms host (apu_cycle loops) over %llu frames (~%.2f ms/frame)\n",
                (unsigned long long)apucyc_prof_calls,
                apucyc_prof_ms,
                (unsigned long long)s_frames,
                s_frames ? apucyc_prof_ms / (double)s_frames : 0.0);
    { uint64_t cc = 0, cy = 0;
      snes_catchup_stats(&cc, &cy);
      fprintf(stderr, "[apu_catchup] %llu calls, %llu SPC cycles over %llu frames (~%llu SPC cyc/frame)\n",
              (unsigned long long)cc, (unsigned long long)cy,
              (unsigned long long)s_frames,
              s_frames ? (unsigned long long)(cy / s_frames) : 0);
    }
#endif
    if (s_state_out) { fclose(s_state_out); s_state_out = NULL; }
    if (s_render_video && !write_ppm(final_frame_dump, s_video_pixels)) {
        fprintf(stderr, "cosim-harness: cannot write final frame dump '%s'\n",
                final_frame_dump ? final_frame_dump : "(null)");
        return 1;
    }
    {
        extern void interp816_opcode_hist_dump(void);
        interp816_opcode_hist_dump();
    }
    fprintf(stderr, "cosim-harness(so): standalone %llu frames done\n",
            (unsigned long long)s_frames);
    return 0;
}
