#include "so_rtl.h"
#include "variables.h"
#include "common_cpu_infra.h"
#include "snes/snes.h"
#include "snes/ppu.h"
#include "cpu_state.h"
#include "funcs.h"
#include "snes/interp_bridge.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Star Ocean runs as a whole-program interpreter target: the recompiler
 * produced only a handful of entry stubs (I_NMI / I_IRQ / I_RESET plus the
 * bank $C0 entry), so the frame driver runs the real ROM under interp816 via
 * the auto-quiescent bridge. The bridge yields when the architectural state
 * reaches a deterministic read-only cycle (a WAI, or a tight read-only spin),
 * which is exactly the frame boundary where asynchronous hardware (NMI/IRQ)
 * must be delivered. The first frame enters cold at the RESET vector target
 * (LoROM $FFFC -> $00:FEC1); afterwards the bridge reports the resume PC and
 * whether the last yield was a WAI (sticky, consumed here). */

#ifdef SNESRECOMP_INTERP_PROFILE
#include <time.h>
uint64_t ppu_prof_calls = 0;
double ppu_prof_ms = 0.0;
#endif
void SoDrawPpuFrame(void) {
#ifdef SNESRECOMP_INTERP_PROFILE
  { extern uint64_t ppu_prof_calls; extern double ppu_prof_ms;
    clock_t _t0 = clock();
    ppu_prof_calls++; }
  clock_t _t1 = clock();
#endif
  SimpleHdma hdma_chans[8];

  Dma *dma = g_dma;

  dma_startDma(dma, g_snesrecomp_last_hdmaen, true);

  for (int i = 0; i < 8; i++)
    SimpleHdma_Init(&hdma_chans[i], &dma->channel[i]);

  int trigger = g_snes->vIrqEnabled ? g_snes->vTimer + 1 : -1;

  for (int i = 0; i <= 224; i++) {
    ppu_runLine(g_ppu, i);
    for (int ch = 0; ch < 8; ch++)
      SimpleHdma_DoLine(&hdma_chans[ch]);
    if (i == trigger) {
      g_snes->inIrq = true;

      const uint16_t saved_S = g_cpu.S;
      cpu_push_interrupt_frame(&g_cpu);
      interp_bridge_run_interrupt(&g_cpu, 0x00FEBD);
      g_cpu.S = saved_S;
      g_snes->inIrq = false;
      trigger = g_snes->vIrqEnabled ? g_snes->vTimer + 1 : -1;
    }
  }

  /* vblank-range vIRQ (VTIMER 225..261): the visible render loop only
   * covers lines 0-224, so a comparator parked in vblank never fires there.
   * On hardware the IRQ fires when the beam reaches vTimer inside vblank;
   * Star Ocean's battle engine alternates VTIMER 216 <-> 258 every frame
   * (bsnes trace: $C0:02BC restores $2100 from $DA at V:258, $C0:02E2
   * forces blank at V:216). The recomp delivered only the raster half
   * (line vTimer+1 <= 224), so the V:258 brightness restore never ran and
   * the battle screen stayed in forced blank forever (inidisp=$80, black
   * with music). Deliver the vblank comparator here exactly like the
   * raster path; the handler LLE advances the beam itself for any $4212
   * wait it performs. Gate: only when the game has actually enabled a
   * vblank-range vIRQ, so field/raster cases are untouched. */
  if (g_snes->vIrqEnabled && g_snes->vTimer >= 225u && g_snes->vTimer <= 261u) {
    g_snes->inIrq = true;

    const uint16_t saved_S = g_cpu.S;
    cpu_push_interrupt_frame(&g_cpu);
    interp_bridge_run_interrupt(&g_cpu, 0x00FEBD);
    g_cpu.S = saved_S;
    g_snes->inIrq = false;
  }
#ifdef SNESRECOMP_INTERP_PROFILE
  { extern uint64_t ppu_prof_calls; extern double ppu_prof_ms;
    ppu_prof_ms += 1000.0 * ((double)(clock() - _t1)) / CLOCKS_PER_SEC; }
#endif
}

void RunOneFrameOfGame(void) {
  static bool g_did_reset = false;
  if (!g_did_reset) {
    cpu_state_init(&g_cpu, g_ram);
    g_did_reset = true;
    fprintf(stderr, "[so_rtl] cpu_state_init done\n");
  }

  counter_global_frames++;
  if (counter_global_frames <= 5 || (counter_global_frames % 600) == 0)
    fprintf(stderr, "[so_rtl] frame %d nmiEn=%d resume=$%06X\n",
            counter_global_frames, g_snes->nmiEnabled,
            (unsigned)interp_bridge_lle_resume_pc());

  /* Deliver NMI if the game has enabled it. */
  g_snes->inNmi = true;

  if (g_snes->nmiEnabled) {
    const uint16_t saved_S = g_cpu.S;
    cpu_push_interrupt_frame(&g_cpu);
    interp_bridge_run_interrupt(&g_cpu, 0x00FEB9);
    g_cpu.S = saved_S;
  }

  uint32_t resume = interp_bridge_lle_resume_pc();
  if (!resume)
    resume = 0x00FEC1;

  /* Battle $D9 handshake (see HANDOFF §12.8): the frame task waits on the
   * WRAM latch $D9 ($80 = forced blank at V:216, 0 = restored at V:258) at
   * $C084AE/B2/B4 (LDA $D9 / BNE / LDA $D9 / BEQ). The wait is a pure WRAM
   * read loop, so the quiescent detector yields after 2 iterations — before
   * the raster IRQ is delivered — and the frame task (battle tick + fade-in
   * $CC:0B44) never runs, freezing the battle at fade-in brightness. When
   * the LLE stops in the SECOND wait (C084B2/B4, waiting for $D9 != 0) with
   * a vIRQ active, deliver the forced-blank IRQ here and resume so the spin
   * completes and the task runs; the end-of-frame vblank IRQ then delivers
   * the brightness restore. Field/intro never reach this spin (no vIRQ
   * cycle), so the validated A/B path is untouched. */
  for (int guard = 0; guard < 8; guard++) {
    interp_bridge_run_until_quiescent(&g_cpu, resume);

    uint32_t pc = interp_bridge_lle_resume_pc();
    if ((pc == 0xC084B2u || pc == 0xC084B4u) && g_snes->vIrqEnabled) {
      g_snes->inIrq = true;
      const uint16_t saved_S = g_cpu.S;
      cpu_push_interrupt_frame(&g_cpu);
      interp_bridge_run_interrupt(&g_cpu, 0x00FEBD);
      g_cpu.S = saved_S;
      g_snes->inIrq = false;
      resume = interp_bridge_lle_resume_pc();
      if (!resume) resume = 0x00FEC1;
      continue;
    }
    break;
  }

  /* Conditional VBLANK sync: if the CPU is stuck waiting for IRQ
   * at $00FEBD (the IRQ vector) after frame 10, force the beam
   * to VBLANK so the NMI handler can fire and unblock the game.
   * During frames 1-5 the game is still booting, so we skip this. */
  uint32_t pc = interp_bridge_lle_resume_pc();
  if (pc == 0x00FEBD && counter_global_frames > 10) {
    snes_sync_master_clock(g_snes, 225 * 1364);
  }

  /* env-gated per-frame render-state trace (SNESRECOMP_FRAME_STATE=1):
   * logged just before SoDrawPpuFrame, so inidisp is exactly what the
   * renderer will see. Diagnostic only; zero cost when unset. */
  { static int fs = -1; static long fs_from = 0;
    if (fs < 0) { const char *e = getenv("SNESRECOMP_FRAME_STATE");
                  fs = (e && e[0] && e[0] != '0') ? 1 : 0;
                  const char *fr = getenv("SNESRECOMP_FRAME_STATE_FROM");
                  if (fr && fr[0]) fs_from = atol(fr); }
    if (fs && counter_global_frames >= fs_from) {
      fprintf(stderr, "[fstate] f=%d nmiEn=%d resume=%06X inidisp=%02X\n",
              counter_global_frames, g_snes->nmiEnabled,
              (unsigned)interp_bridge_lle_resume_pc(),
              g_ppu ? (int)g_ppu->inidisp : -1);
    }
  }
}
