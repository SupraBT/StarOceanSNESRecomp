#include "so_rtl.h"
#include "variables.h"
#include "common_cpu_infra.h"
#include "snes/snes.h"
#include "snes/ppu.h"
#include "cpu_state.h"
#include "funcs.h"
#include "snes/interp_bridge.h"

/* Handler-entry counters (interp_bridge.c): dev instrumentation for the
 * per-frame IRQ/NMI delivery rate. */
extern uint64_t g_interp_irq_entries;
extern uint64_t g_interp_nmi_entries;
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
/* Stubs TEMPORALES (solo con SNESRECOMP_INTERP_PROFILE, que no usa build-dev):
 * main.c declara los contadores del runtime AOT v2 pero ese runtime no forma
 * parte de este ejecutable, asi que el enlace falla sin ellos. Medir un
 * presupuesto de frame no necesita esos numeros; si algun dia se integra el
 * runtime AOT en esta build, borrar este bloque. */
uint64_t aotq_prof_calls = 0;
uint64_t aotq_prof_cycles = 0;
double aotq_prof_ms = 0.0;
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
#ifndef SNESRECOMP_CLEAN_BUILD
    fprintf(stderr, "[so_rtl] cpu_state_init done\n");
#endif
  }

  counter_global_frames++;
#ifndef SNESRECOMP_CLEAN_BUILD
  if (counter_global_frames <= 5 || (counter_global_frames % 600) == 0)
    fprintf(stderr, "[so_rtl] frame %d nmiEn=%d resume=$%06X\n",
            counter_global_frames, g_snes->nmiEnabled,
            (unsigned)interp_bridge_lle_resume_pc());
#endif

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

  /* Deadline de frame de invitado: un frame de host = 1 frame de invitado
   * (357368 ciclos master).  Ver ENCICLOPEDIA §22.
   *
   * El mecanismo ya existia -interp_bridge_set_master_deadline() y lo consultan
   * tanto el puente como el codigo AOT generado- pero NADIE lo fijaba, asi que
   * el invitado corria "hasta quiescencia" sin mas tope.  En los tramos no
   * quiescentes (los bucles de handshake sobre $40/$2140) eso dejaba que UN
   * frame de host consumiera 4, 7 o hasta 66 frames de invitado de un tiron, y
   * el invitado se adelantaba en tiempo real (medido 2026-09-29): el primer
   * fundido caia en el frame de host 712 sin deadline y en el 791 con deadline
   * 1 (hardware: 841), mientras su posicion en reloj de invitado no cambiaba
   * (~790 gf).  Con la deadline el invitado consume exactamente 357368 ciclos
   * master por frame de host en todos los frames menos los 3 de arranque, y el
   * guion de $2100 coincide hueco a hueco con la traza de hardware.
   *
   * Env SNESRECOMP_FRAME_DEADLINE=<n> (frames de master; ausente = 1.0, 0 =
   * comportamiento historico ilimitado). */
  static double s_frame_deadline = -2.0;
  if (s_frame_deadline < -1.0) {
    const char *e = getenv("SNESRECOMP_FRAME_DEADLINE");
    /* DEFAULT 0 (audio) desde 2026-09-29, ver ENCICLOPEDIA §22.13.
     *
     * Con la deadline activa el invitado cede el frame por DEADLINE en vez de
     * por QUIESCENCIA, y el tick del driver de sonido del juego vive en el
     * handler de V-IRQ por frame (C0:032D, ver §19). Medido con volcado del PCM
     * que se entrega al dispositivo (`SNESRECOMP_PCM_DUMP`): con cualquier
     * deadline > 0 el DSP no toca NADA en toda la intro (pico 0 en 0-13 s y
     * pico 2 despues del unico chasquido de f790), mientras que con 0 toca
     * musica continua desde el segundo 7 (picos 2000-4500). No es efecto de
     * "cuanto tiempo" -0,25 frames ya silencia todo- sino de POR DONDE sale el
     * frame. Los arreglos de audio (tasa del consumidor, colchon inicial,
     * recorte de exceso, §22.12) son independientes y siguen activos.
     *
     * La fidelidad del modelo de tiempo queda disponible con
     * SNESRECOMP_FRAME_DEADLINE=1 (y el A/B byte-exacto de §22 la valida), pero
     * NO se activa por defecto hasta que el camino de deadline entregue tambien
     * el NMI/IRQ del frame como hace el camino de quiescencia. */
    s_frame_deadline = (e && e[0]) ? atof(e) : 0.0;
    if (s_frame_deadline < 0.0) s_frame_deadline = 0.0;
  }
  /* Absoluta para todo el frame de host: la deadline es una propiedad del
   * frame, no de cada vuelta del guard.  Recalcularla por vuelta permitiria
   * que el camino del handshake de batalla ($C084B2/B4) consuma hasta 8 frames
   * de invitado en un solo frame de host. */
  const uint64_t frame_deadline_master =
      g_cpu.master_cycles + (uint64_t)(s_frame_deadline * 357368.0);

  /* Sonda de presupuesto de frame (SNESRECOMP_FRAME_BUDGET=1, dev): una linea
   * por frame de host con cuantos frames de invitado (dgf) y cuanto reloj
   * master (dmaster) acaba de consumir, mas el PC de reanudacion antes/despues.
   * dgf != 1 es exactamente el defecto que la deadline corrige. */
  {
    extern unsigned long long snes_guest_frame_count(void);
    static unsigned long long prev_gf, prev_m;
    static uint32_t prev_res;
    static int initialized;
    static int fb = -1;
    if (fb < 0) { const char *e = getenv("SNESRECOMP_FRAME_BUDGET");
                  fb = (e && e[0] && e[0] != '0') ? 1 : 0; }
    const unsigned long long gf_now = snes_guest_frame_count();
    const unsigned long long m_now  = g_cpu.master_cycles;
    if (fb && initialized && s_frame_deadline > 0.0) {
      fprintf(stderr, "[fbudget] f=%d dgf=%llu dmaster=%llu res0=%06X res1=%06X\n",
              counter_global_frames - 1, gf_now - prev_gf, m_now - prev_m,
              (unsigned)prev_res, (unsigned)interp_bridge_lle_resume_pc());
    }
    prev_gf = gf_now; prev_m = m_now;
    prev_res = interp_bridge_lle_resume_pc(); initialized = 1;
  }

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
    if (s_frame_deadline > 0.0)
      interp_bridge_set_master_deadline(frame_deadline_master);
    interp_bridge_run_until_quiescent(&g_cpu, resume);
    if (s_frame_deadline > 0.0)
      interp_bridge_set_master_deadline(0);

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
      /* Guest-clock + observable state per frame, so a recording made on
       * hardware can be aligned on the guest clock instead of the host frame
       * index (a host frame may cover many guest frames). Fields appended
       * after inidisp keep prefix parsers working. pad/r4200 mirror the
       * oracle columns: the pad word the guest reads this frame and the
       * reconstructed $4200 byte (NMI/hIRQ/vIRQ/auto-joypad). */
      fprintf(stderr, "[fstate] f=%d nmiEn=%d resume=%06X inidisp=%02X "
                      "cpu=%llu master=%llu pad=%04X r4200=%02X hIrq=%d vIrq=%d "
                      "irq=%llu nmi=%llu vTimer=%u E4=%04X DA=%02X AFB=%02X "
                      "AFD=%04X D01=%02X DB=%02X PB=%02X DP=%04X S=%04X "
                      "A=%04X X=%04X Y=%04X P=%02X\n",
              counter_global_frames, g_snes->nmiEnabled,
              (unsigned)interp_bridge_lle_resume_pc(),
              g_ppu ? (int)g_ppu->inidisp : -1,
              (unsigned long long)g_cpu.cycles,
              (unsigned long long)g_cpu.master_cycles,
              (unsigned)g_snes->input1_currentState,
              (unsigned)((g_snes->nmiEnabled   ? 0x80u : 0u) |
                         (g_snes->vIrqEnabled  ? 0x20u : 0u) |
                         (g_snes->hIrqEnabled  ? 0x10u : 0u) |
                         (g_snes->autoJoyRead  ? 0x01u : 0u)),
              (int)g_snes->hIrqEnabled, (int)g_snes->vIrqEnabled,
              (unsigned long long)g_interp_irq_entries,
              (unsigned long long)g_interp_nmi_entries,
              (unsigned)g_snes->vTimer,
              (unsigned)cpu_read16(&g_cpu, 0x00, 0x00E4),
              (unsigned)cpu_read8(&g_cpu, 0x00, 0x00DA),
              (unsigned)cpu_read8(&g_cpu, 0x00, 0x0AFB),
              (unsigned)cpu_read16(&g_cpu, 0x00, 0x0AFD),
              (unsigned)cpu_read8(&g_cpu, 0x00, 0x0D01),
              /* DB (banco de datos) decide a que espacio van los accesos
               * absolutos del invitado: `LDA $4806` (registro S-DD1) sale por
               * I/O con DB=$00 y cae en WRAM con DB=$7E/$7F.  Hardware
               * sostiene DB=$00 en los 2000 frames de la traza, asi que
               * cualquier DB != 0 aqui es divergencia de banco, no de flujo. */
              (unsigned)g_cpu.DB, (unsigned)g_cpu.PB,
              (unsigned)g_cpu.D, (unsigned)g_cpu.S,
              /* Oraculo de estado: el trace de Mesen trae a/x/y/sp/d/db/p por
               * frame, y el recomp no tiene PC que comparar (CpuState no
               * guarda PC: el codigo AOT usa control de flujo nativo y el LLE
               * solo publica su punto de reanudacion). Los registros SI son
               * estado del invitado y se pueden alinear por reloj: si se
               * mantienen iguales durante miles de frames y en un punto se
               * despegan, ese punto es la divergencia (no el ruido de ±1
               * instruccion del instante de muestreo). */
              (unsigned)g_cpu.A, (unsigned)g_cpu.X, (unsigned)g_cpu.Y,
              (unsigned)g_cpu.P);
      /* Ramo del handler de V-IRQ $C0:0221 (medido por desensamblado, no
       * supuesto):
       *   $C0:0229 TCD #$0000      -> DP=$0000 ; $C0:022F/0230 -> DB=$00
       *   $C0:0234 LDA $D8          tipo de IRQ (1 -> JMP $02B0, 2 -> JMP $025F)
       *   $C0:0244 LDA $F7/EOR #1/STA $F7   conmutador de medio-frame
       *   $C0:024C INC $E1          contador de ticks del handler
       * Si la columna `irq` sube pero $E1 no, el vector entra y el handler se
       * queda dentro ANTES del INC: ahi esta el cuelgue, y ningun cfg lo
       * arregla porque $C0:0221 cae a interp_tier_dispatch (LLE), sin cuerpo
       * AOT. Diagnostico puro; coste cero si SNESRECOMP_FRAME_STATE no esta. */
      fprintf(stderr, "[irqstate] f=%d D8=%02X E1=%02X F7=%02X AF8=%02X\n",
              counter_global_frames,
              (unsigned)cpu_read8(&g_cpu, 0x00, 0x00D8),
              (unsigned)cpu_read8(&g_cpu, 0x00, 0x00E1),
              (unsigned)cpu_read8(&g_cpu, 0x00, 0x00F7),
              (unsigned)cpu_read8(&g_cpu, 0x00, 0x0AF8));
    }
  }

  /* env-gated object-table dump (SNESRECOMP_FRAME_OBJTABLE=<n_slots>).
   *
   * The per-frame dispatcher at $C6:2D45 walks 0x40 slots of 0x40 bytes from
   * WRAM $7E:2000 and runs the update routine of every slot whose flag word
   * has bit 15 set; that is the code that actually moves the player. The
   * hardware trace we have carries registers, PC, DB and pad, but NOT WRAM, so
   * the object table is ours to observe: dumping the first N slots once per
   * guest frame is what lets us find the exact frame where a guided walk
   * leaves the path and which field changed first.
   *
   * SNESRECOMP_FRAME_OBJTABLE_FROM/_TO bound the window (guest frames) so a
   * run only pays for the frames that matter. Diagnostic only; zero cost when
   * the variable is unset.
   *
   * Reads the RAW WRAM array, not cpu_read8(): cpu_read8 latches open_bus and
   * calls cart_note_cpu_bus, so a 4 KB-per-frame dump perturbs the very state
   * it is trying to observe (measured: with 64 slots the table read as zero,
   * with 1 slot it was alive). $7E:xxxx is g_ram[xxxx]. */
  { static int obj_n = -1; static long obj_from = 0, obj_to = -1;
    if (obj_n < 0) {
      const char *e = getenv("SNESRECOMP_FRAME_OBJTABLE");
      obj_n = (e && e[0] && e[0] != '0') ? atoi(e) : 0;
      if (obj_n < 0) obj_n = 0;
      if (obj_n > 0x40) obj_n = 0x40;   /* the whole table, 0x2000-0x2FFF */
      const char *fr = getenv("SNESRECOMP_FRAME_OBJTABLE_FROM");
      if (fr && fr[0]) obj_from = atol(fr);
      const char *to = getenv("SNESRECOMP_FRAME_OBJTABLE_TO");
      if (to && to[0]) obj_to = atol(to);
    }
    if (obj_n > 0 && counter_global_frames >= obj_from
        && (obj_to < 0 || counter_global_frames <= obj_to)) {
      fprintf(stderr, "[objtab] f=%d", counter_global_frames);
      for (int s = 0; s < obj_n; s++) {
        unsigned base = 0x2000u + (unsigned)s * 0x40u;
        fprintf(stderr, " %02X:", s);
        for (int b = 0; b < 0x40; b++)
          fprintf(stderr, "%02X",
                  (unsigned)g_cpu.ram[(base + b) & 0x1FFFFu]);
      }
      fputc('\n', stderr);
    }
  }
}
