#include "common_cpu_infra.h"
#include "so_rtl.h"

/* Framework-protocol frame counter.  Incremented once per run_frame().
 * Some generated code and the Falcon presentation mod reference this. */
uint16 counter_global_frames = 0;

const RtlGameInfo kSoGameInfo = {
  .title = "so",
  .initialize = NULL,
  .run_frame = &RunOneFrameOfGame,
  .draw_ppu_frame = &SoDrawPpuFrame,
  .save_name_prefix = "save",
  .state_save_extra = NULL,
  .state_load_extra = NULL,
  .on_state_loaded = NULL,
};