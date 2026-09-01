// state_file.c — F9/F10 savestate file I/O.
//
// The L3SN snapshot format serializes the full SNES state (CPU/PPU/DMA/APU/
// cart/WRAM) via snes_saveload plus the recompiler's own CpuState (g_cpu),
// which snes_saveload does NOT cover. Without that chunk the recompiler would
// resume with stale registers over restored memory.
//
// L3SN v2 also serializes host APU pacing state. That state is host-side
// bookkeeping, but after a load it must match the restored guest cycle or
// queued APU port writes can be scheduled far in the future and hang handshakes.
//
// These functions live here (always compiled) instead of in debug_server.c
// (TRACE-only) so the savestate hotkeys work in the production build too.

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include "snes/snes.h"
#include "snes/saveload.h"
#include "cpu_state.h"
#include "common_cpu_infra.h"
#include "common_rtl.h"

extern Snes *g_snes;
extern int snes_frame_counter;
extern uint64_t g_main_cpu_cycles_estimate;
extern uint64_t g_apu_pace_cycles_estimate;
extern uint64_t g_apu_last_sync_cycles;
extern uint64_t g_apu_last_sync_master;
extern CpuState g_cpu;

// 4-byte magic + 4-byte version lets us evolve the format.
#define L3_SNAP_MAGIC 0x4c33534e  /* "L3SN" */
#define L3_SNAP_VERSION 2

typedef struct FileSli {
    SaveLoadInfo sli;
    FILE *f;
    int is_save;
    int error;
    size_t total;
} FileSli;

static void _file_sli_func(SaveLoadInfo *info, void *data, size_t size) {
    FileSli *fs = (FileSli *)info;
    if (fs->error) return;
    size_t got;
    if (fs->is_save)
        got = fwrite(data, 1, size, fs->f);
    else
        got = fread(data, 1, size, fs->f);
    if (got != size) fs->error = 1;
    fs->total += size;
}

/* CPU snapshot helpers for F9/F10. Saves the recomp's CpuState (g_cpu)
 * which is separate from the SNES Cpu struct saved by snes_saveload. */
struct CpuSnapshot {
    uint16 A, X, Y, S, D;
    uint8  DB, PB, P, m_flag, x_flag, emulation;
    uint8  _flag_N, _flag_V, _flag_Z, _flag_C, _flag_I, _flag_D;
    uint8  open_bus, host_return_valid;
    uint64_t cycles, master_cycles;
    int frame_counter;  /* snes_frame_counter */
    uint32_t lle_resume_pc;  /* interp bridge resume PC */
};

static void cpu_save_snapshot(FILE *f) {
    struct CpuSnapshot snap;
    snap.A = g_cpu.A; snap.X = g_cpu.X; snap.Y = g_cpu.Y;
    snap.S = g_cpu.S; snap.D = g_cpu.D;
    snap.DB = g_cpu.DB; snap.PB = g_cpu.PB; snap.P = g_cpu.P;
    snap.m_flag = g_cpu.m_flag; snap.x_flag = g_cpu.x_flag;
    snap.emulation = g_cpu.emulation;
    snap._flag_N = g_cpu._flag_N; snap._flag_V = g_cpu._flag_V;
    snap._flag_Z = g_cpu._flag_Z; snap._flag_C = g_cpu._flag_C;
    snap._flag_I = g_cpu._flag_I; snap._flag_D = g_cpu._flag_D;
    snap.open_bus = g_cpu.open_bus;
    snap.host_return_valid = g_cpu.host_return_valid;
    snap.cycles = g_cpu.cycles;
    snap.master_cycles = g_cpu.master_cycles;
    snap.frame_counter = snes_frame_counter;
    extern uint32_t interp_bridge_lle_resume_pc(void);
    snap.lle_resume_pc = interp_bridge_lle_resume_pc();
    uint32_t sz = (uint32_t)sizeof(snap);
    fwrite(&sz, 4, 1, f);
    fwrite(&snap, sz, 1, f);
}

/* Returns 0 on success, 1 on truncated/corrupt chunk (g_cpu left untouched
 * on failure so a bad file cannot silently clobber live registers). */
static int cpu_load_snapshot(FILE *f) {
    uint32_t sz = 0;
    if (fread(&sz, 4, 1, f) != 1) return 1;
    /* Only accept the exact snapshot size we know. A shorter/longer chunk
     * means a truncated or foreign-format file; applying a partial snapshot
     * would clobber live g_cpu registers with zeros. */
    if (sz != sizeof(struct CpuSnapshot)) return 1;
    struct CpuSnapshot snap;
    memset(&snap, 0, sizeof(snap));
    if (fread(&snap, sizeof(snap), 1, f) != 1) return 1;
    g_cpu.A = snap.A; g_cpu.X = snap.X; g_cpu.Y = snap.Y;
    g_cpu.S = snap.S; g_cpu.D = snap.D;
    g_cpu.DB = snap.DB; g_cpu.PB = snap.PB; g_cpu.P = snap.P;
    g_cpu.m_flag = snap.m_flag; g_cpu.x_flag = snap.x_flag;
    g_cpu.emulation = snap.emulation;
    g_cpu._flag_N = snap._flag_N; g_cpu._flag_V = snap._flag_V;
    g_cpu._flag_Z = snap._flag_Z; g_cpu._flag_C = snap._flag_C;
    g_cpu._flag_I = snap._flag_I; g_cpu._flag_D = snap._flag_D;
    g_cpu.open_bus = snap.open_bus;
    g_cpu.host_return_valid = snap.host_return_valid;
    g_cpu.cycles = snap.cycles;
    g_cpu.master_cycles = snap.master_cycles;
    snes_frame_counter = snap.frame_counter;
    /* Restore the interp bridge resume PC so RunOneFrameOfGame resumes
     * at the correct location instead of booting from RESET vector. */
    extern void interp_bridge_set_lle_resume_pc(uint32_t pc);
    interp_bridge_set_lle_resume_pc(snap.lle_resume_pc);
    return 0;
}

static void apu_pace_save_snapshot(FILE *f) {
    Apu *apu = g_snes->apu;
    uint64_t frame_start_master;
    uint8_t frame_time_valid;
    rtl_apu_snapshot_pacing(&frame_start_master, &frame_time_valid);
    uint32_t head = apu->portQHead;
    uint32_t tail = apu->portQTail;
    uint32_t count = tail - head;
    if (count > APU_PORT_QUEUE_LEN) count = APU_PORT_QUEUE_LEN;

    fwrite(&g_apu_pace_cycles_estimate, 8, 1, f);
    fwrite(&g_main_cpu_cycles_estimate, 8, 1, f);
    fwrite(&frame_start_master, 8, 1, f);
    fwrite(&frame_time_valid, 1, 1, f);
    fwrite(&head, 4, 1, f);
    fwrite(&tail, 4, 1, f);
    fwrite(&apu->portClock, 8, 1, f);
    fwrite(&apu->portGuestAnchor, 8, 1, f);
    fwrite(&apu->portTargetAnchor, 8, 1, f);
    fwrite(&apu->portLastGuest, 8, 1, f);
    fwrite(&apu->portLastTarget, 8, 1, f);
    fwrite(&apu->portTimeValid, 1, 1, f);
    fwrite(&count, 4, 1, f);
    for (uint32_t i = head; i < head + count; i++) {
        ApuPortWrite *w = &apu->portQueue[i & (APU_PORT_QUEUE_LEN - 1)];
        fwrite(&w->target_cycle, 8, 1, f);
        fwrite(&w->port, 1, 1, f);
        fwrite(&w->val, 1, 1, f);
    }
}

static int apu_pace_load_snapshot(FILE *f) {
    Apu *apu = g_snes->apu;
    uint64_t pace, main_est, frame_start_master;
    uint64_t portClock, portGuestAnchor, portTargetAnchor;
    uint64_t portLastGuest, portLastTarget;
    uint8_t frame_time_valid, portTimeValid;
    uint32_t head, tail, count;
    if (fread(&pace, 8, 1, f) != 1) return 1;
    if (fread(&main_est, 8, 1, f) != 1) return 1;
    if (fread(&frame_start_master, 8, 1, f) != 1) return 1;
    if (fread(&frame_time_valid, 1, 1, f) != 1) return 1;
    if (fread(&head, 4, 1, f) != 1) return 1;
    if (fread(&tail, 4, 1, f) != 1) return 1;
    if (fread(&portClock, 8, 1, f) != 1) return 1;
    if (fread(&portGuestAnchor, 8, 1, f) != 1) return 1;
    if (fread(&portTargetAnchor, 8, 1, f) != 1) return 1;
    if (fread(&portLastGuest, 8, 1, f) != 1) return 1;
    if (fread(&portLastTarget, 8, 1, f) != 1) return 1;
    if (fread(&portTimeValid, 1, 1, f) != 1) return 1;
    if (fread(&count, 4, 1, f) != 1) return 1;
    if (count > APU_PORT_QUEUE_LEN) return 1;
    if (tail - head != count) return 1;

    ApuPortWrite pending[APU_PORT_QUEUE_LEN];
    for (uint32_t i = 0; i < count; i++) {
        uint64_t t;
        uint8_t p, v;
        if (fread(&t, 8, 1, f) != 1) return 1;
        if (fread(&p, 1, 1, f) != 1) return 1;
        if (fread(&v, 1, 1, f) != 1) return 1;
        pending[i].target_cycle = t;
        pending[i].port = p;
        pending[i].val = v;
    }

    apu->portClock = portClock;
    apu->portGuestAnchor = portGuestAnchor;
    apu->portTargetAnchor = portTargetAnchor;
    apu->portLastGuest = portLastGuest;
    apu->portLastTarget = portLastTarget;
    apu->portTimeValid = portTimeValid != 0;
    apu->portQHead = head;
    apu->portQTail = head;
    for (uint32_t i = 0; i < count; i++) {
        apu->portQueue[apu->portQTail & (APU_PORT_QUEUE_LEN - 1)] = pending[i];
        apu->portQTail++;
    }

    g_apu_pace_cycles_estimate = pace;
    g_main_cpu_cycles_estimate = main_est;
    rtl_apu_restore_pacing(frame_start_master, frame_time_valid);
    return 0;
}

int debug_server_save_state_file(const char *path) {
    if (!g_snes) return 1;
    FILE *f = fopen(path, "wb");
    if (!f) { fprintf(stderr, "[save] fopen failed: %s\n", path); return 1; }
    uint32_t magic = L3_SNAP_MAGIC, version = L3_SNAP_VERSION;
    fwrite(&magic, 4, 1, f); fwrite(&version, 4, 1, f);
    RtlApuLock();
    FileSli fs = {{_file_sli_func}, f, 1, 0, 0};
    snes_saveload(g_snes, &fs.sli);
    cpu_save_snapshot(f);
    apu_pace_save_snapshot(f);
    RtlApuUnlock();
    fclose(f);
    if (fs.error) {
        fprintf(stderr, "[save] write error: %s\n", path);
        return 1;
    }
    fprintf(stderr, "[save] %zu bytes -> %s\n", fs.total + 8, path);
    return 0;
}

void RtlPostLoadReanchorApu(void) {
    g_apu_last_sync_master = g_cpu.master_cycles;
    g_apu_last_sync_cycles = g_apu_pace_cycles_estimate;
    extern void interp_bridge_reset_dynamic_cache(void);
    interp_bridge_reset_dynamic_cache();
}

void sync_g_cpu_to_snes_cpu(void) {
    Cpu *gcpu = g_snes->cpu;
    gcpu->a = g_cpu.A;  gcpu->x = g_cpu.X;  gcpu->y = g_cpu.Y;
    gcpu->sp = g_cpu.S; gcpu->dp = g_cpu.D; gcpu->db = g_cpu.DB; gcpu->k = g_cpu.PB;
    gcpu->c = g_cpu._flag_C; gcpu->z = g_cpu._flag_Z; gcpu->v = g_cpu._flag_V;
    gcpu->n = g_cpu._flag_N; gcpu->i = g_cpu._flag_I; gcpu->d = g_cpu._flag_D;
    gcpu->xf = g_cpu.x_flag; gcpu->mf = g_cpu.m_flag; gcpu->e = g_cpu.emulation;
}

int debug_server_load_state_file(const char *path) {
    if (!g_snes) return 1;
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "[load] fopen failed: %s\n", path); return 1; }
    uint32_t magic = 0, version = 0;
    if (fread(&magic, 4, 1, f) != 1 || magic != L3_SNAP_MAGIC) {
        fclose(f); fprintf(stderr, "[load] bad magic\n"); return 1;
    }
    if (fread(&version, 4, 1, f) != 1 || version < 1 || version > L3_SNAP_VERSION) {
        fclose(f); fprintf(stderr, "[load] bad version\n"); return 1;
    }
    RtlApuLock();
    FileSli fs = {{_file_sli_func}, f, 0, 0, 0};
    snes_saveload(g_snes, &fs.sli);
    int cpu_err = cpu_load_snapshot(f);
    int pace_err = 0;
    if (version >= 2)
        pace_err = apu_pace_load_snapshot(f);
    RtlApuUnlock();
    fclose(f);
    if (!fs.error && !cpu_err && !pace_err) RtlPostLoadReanchorApu();
    if (fs.error || cpu_err || pace_err) {
        fprintf(stderr, "[load] %s: read failed (fs_err=%d cpu_err=%d pace_err=%d)\n",
                path, fs.error, cpu_err, pace_err);
        return 1;
    }
    /* Sync recompiled CpuState -> LLE Cpu so PPU/DMA/timing agree */
    sync_g_cpu_to_snes_cpu();
    fprintf(stderr, "[load] %zu bytes <- %s\n", fs.total + 8, path);
    return 0;
}
