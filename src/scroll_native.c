/* scroll_native.c - Native C implementations for scroll register writes
 *
 * These bypass the recompiler's LLE limitation by directly implementing
 * the scroll register writes in C. The game calls these via the dispatch
 * table when entering bank $C0 scroll functions.
 *
 * Each function writes to the SNES scroll registers ($210D-$2112)
 * using the PPU state structure directly.
 *
 * PPU scroll layout (from ppu.h):
 *   hScroll[4] - horizontal scroll for BG1-BG4
 *   vScroll[4] - vertical scroll for BG1-BG4
 *   m7matrix[8] - Mode 7 matrix (a, b, c, d, x, y, h, v)
 */
#include "snes/snes.h"
#include "snes/ppu.h"
#include "cpu_state.h"
#include <stdint.h>

extern Snes *g_snes;
extern CpuState g_cpu;

/* Write BG1HOFS ($210D) */
void scroll_bg1hofs(uint16_t value) {
    if (!g_snes || !g_snes->ppu) return;
    g_snes->ppu->hScroll[0] = value;
}

/* Write BG1VOFS ($210E) */
void scroll_bg1vofs(uint16_t value) {
    if (!g_snes || !g_snes->ppu) return;
    g_snes->ppu->vScroll[0] = value;
}

/* Write BG2HOFS ($210F) */
void scroll_bg2hofs(uint16_t value) {
    if (!g_snes || !g_snes->ppu) return;
    g_snes->ppu->hScroll[1] = value;
}

/* Write BG2VOFS ($2110) */
void scroll_bg2vofs(uint16_t value) {
    if (!g_snes || !g_snes->ppu) return;
    g_snes->ppu->vScroll[1] = value;
}

/* Write BG3HOFS ($2111) */
void scroll_bg3hofs(uint16_t value) {
    if (!g_snes || !g_snes->ppu) return;
    g_snes->ppu->hScroll[2] = value;
}

/* Write BG3VOFS ($2112) */
void scroll_bg3vofs(uint16_t value) {
    if (!g_snes || !g_snes->ppu) return;
    g_snes->ppu->vScroll[2] = value;
}

/* Write Mode7 registers ($211A-$2120) */
void scroll_mode7_a(int16_t value) {
    if (!g_snes || !g_snes->ppu) return;
    g_snes->ppu->m7matrix[0] = value;
}

void scroll_mode7_b(int16_t value) {
    if (!g_snes || !g_snes->ppu) return;
    g_snes->ppu->m7matrix[1] = value;
}

void scroll_mode7_c(int16_t value) {
    if (!g_snes || !g_snes->ppu) return;
    g_snes->ppu->m7matrix[2] = value;
}

void scroll_mode7_d(int16_t value) {
    if (!g_snes || !g_snes->ppu) return;
    g_snes->ppu->m7matrix[3] = value;
}

void scroll_mode7_x0(uint16_t value) {
    if (!g_snes || !g_snes->ppu) return;
    g_snes->ppu->m7matrix[4] = value;
}

void scroll_mode7_y0(uint16_t value) {
    if (!g_snes || !g_snes->ppu) return;
    g_snes->ppu->m7matrix[5] = value;
}

/* Block scroll update - updates all scroll registers at once
 * This is called from the NMI handler or game loop */
void scroll_update_all(uint16_t bg1h, uint16_t bg1v,
                       uint16_t bg2h, uint16_t bg2v,
                       uint16_t bg3h, uint16_t bg3v) {
    scroll_bg1hofs(bg1h);
    scroll_bg1vofs(bg1v);
    scroll_bg2hofs(bg2h);
    scroll_bg2vofs(bg2v);
    scroll_bg3hofs(bg3h);
    scroll_bg3vofs(bg3v);
}
