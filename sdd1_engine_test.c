/* Standalone S-DD1 engine test.
 *
 * Exercises the exact engine the game uses (snesrecomp/runner/src/snes/sdd1.c)
 * through all three entry points:
 *   1. sdd1_decompress_to_buf   (whole-block, MMC reads)
 *   2. sdd1_dma_init/get_byte   (streaming DMA path used by dma.c)
 *   3. sdd1_cpu_read            (CPU-read path used by cart.c)
 *
 * Output (stdout) is hex dumps that sdd1_compare.py diffs against the
 * independent bsnes Python reference (sdd1_ref.py).
 *
 * Build (MSVC):
 *   cl /nologo /O2 /I snesrecomp/runner/src/snes sdd1_engine_test.c /Fe:sdd1_engine_test.exe
 * Run:
 *   sdd1_engine_test.exe "Star Ocean (Japan).sfc" > sdd1_engine_out.txt
 * (stderr carries the engine's debug logs; redirect to /dev/null if noisy.)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include "sdd1.h"

static uint8_t *g_rom;
static uint32_t g_rom_size;

static int load_rom(const char *path) {
  FILE *f = fopen(path, "rb");
  if (!f) { fprintf(stderr, "cannot open %s\n", path); return 0; }
  fseek(f, 0, SEEK_END);
  long sz = ftell(f);
  fseek(f, 0, SEEK_SET);
  g_rom = (uint8_t *)malloc((size_t)sz);
  if (!g_rom) { fclose(f); return 0; }
  if (fread(g_rom, 1, (size_t)sz, f) != (size_t)sz) { fclose(f); return 0; }
  fclose(f);
  g_rom_size = (uint32_t)sz;
  return 1;
}

static void dump_hex(const uint8_t *buf, uint32_t n) {
  for (uint32_t i = 0; i < n; i++)
    printf("%02X", buf[i]);
  printf("\n");
}

int main(int argc, char **argv) {
  if (argc < 2) { fprintf(stderr, "usage: %s rom.sfc\n", argv[0]); return 1; }
  if (!load_rom(argv[1])) return 1;

  Sdd1 *s = sdd1_create(g_rom, g_rom_size, NULL, 0);
  if (!s) { fprintf(stderr, "sdd1_create failed\n"); return 1; }
  sdd1_reset(s);

  /* ---- Case set: each line is: name addr24 size r4804 r4805 r4806 r4807 ----
   * r4807=05 matches the register state the game had during the FF:D0AB DMA
   * (see sdd1_debug6.log). Defaults 0,1,2,3 are the chip reset state. */
  struct Case { const char *name; uint32_t addr; uint32_t size;
                uint8_t r4, r5, r6, r7; } cases[] = {
    { "FFD0AB_0824", 0xFFD0AB, 0x0824, 0x00, 0x01, 0x04, 0x05 },
    { "FE612F_1902", 0xFE612F, 1902,    0x00, 0x01, 0x04, 0x05 },
    { "FE5CF0_1900", 0xFE5CF0, 1900,    0x00, 0x01, 0x04, 0x05 },
    { "FE63A1_4096", 0xFE63A1, 4096,    0x00, 0x01, 0x04, 0x05 },
    { "CD0001_4096", 0xCD0001, 4096,    0x00, 0x01, 0x02, 0x03 },
    { "CE0000_8192", 0xCE0000, 8192,    0x00, 0x01, 0x02, 0x03 },
    { "D00000_8192", 0xD00000, 8192,    0x00, 0x01, 0x02, 0x03 },
    { "F00000_8192", 0xF00000, 8192,    0x00, 0x01, 0x02, 0x03 },
  };

  /* 1) whole-block path (sdd1_decompress_to_buf) */
  for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
    struct Case *c = &cases[i];
    s->r4804 = c->r4; s->r4805 = c->r5; s->r4806 = c->r6; s->r4807 = c->r7;
    uint8_t *buf = (uint8_t *)malloc(c->size);
    uint32_t got = sdd1_decompress_to_buf(s, c->addr, c->size, buf, c->size);
    printf("BLOCK %s %u\n", c->name, got);
    dump_hex(buf, got);
    free(buf);
  }

  /* 2) DMA streaming path (as dma.c arms it) */
  for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
    struct Case *c = &cases[i];
    s->r4804 = c->r4; s->r4805 = c->r5; s->r4806 = c->r6; s->r4807 = c->r7;
    s->r4800 = 0x01; s->r4801 = 0x01;   /* channel 0 hard+soft enable */
    sdd1_dma_init(s, 0, c->addr, c->size);
    if (!sdd1_dma_active(s, 0)) {
      printf("DMA %s NOT_ARMED\n", c->name);
      continue;
    }
    uint8_t *buf = (uint8_t *)malloc(c->size);
    for (uint32_t k = 0; k < c->size; k++)
      buf[k] = sdd1_dma_get_byte(s, 0);
    printf("DMA %s %u\n", c->name, c->size);
    dump_hex(buf, c->size);
    free(buf);
    /* disarm for next case */
    s->r4801 = 0x00;
  }

  /* 3) CPU-read path (as cart.c uses it): capture channel regs via
   * sdd1_dma_channel_write, then read one byte at a time from the
   * matching address. */
  for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
    struct Case *c = &cases[i];
    s->r4804 = c->r4; s->r4805 = c->r5; s->r4806 = c->r6; s->r4807 = c->r7;
    s->r4800 = 0x01; s->r4801 = 0x01;
    /* game writes $43x2-$43x6: addr lo, addr hi, bank, size lo, size hi */
    sdd1_dma_channel_write(s, 0x4302, (uint8_t)(c->addr & 0xff));
    sdd1_dma_channel_write(s, 0x4303, (uint8_t)((c->addr >> 8) & 0xff));
    sdd1_dma_channel_write(s, 0x4304, (uint8_t)((c->addr >> 16) & 0xff));
    sdd1_dma_channel_write(s, 0x4305, (uint8_t)(c->size & 0xff));
    sdd1_dma_channel_write(s, 0x4306, (uint8_t)((c->size >> 8) & 0xff));
    uint8_t *buf = (uint8_t *)malloc(c->size);
    uint32_t n = 0;
    for (uint32_t k = 0; k < c->size; k++) {
      uint8_t v = 0;
      if (!sdd1_cpu_read(s, c->addr, &v)) break;
      buf[n++] = v;
    }
    printf("CPU %s %u\n", c->name, n);
    dump_hex(buf, n);
    free(buf);
    s->r4801 = 0x00;
  }

  sdd1_destroy(s);
  free(g_rom);
  return 0;
}
