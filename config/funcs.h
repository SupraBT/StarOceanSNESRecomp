/* Function declarations for Star Ocean recompiled code.
 * This file provides forward declarations for functions in the generated code.
 * Star Ocean (Japan) uses the S-DD1 decompression chip on a LoROM mapper.
 */

#ifndef FUNCS_H
#define FUNCS_H

#include "cpu_state.h"

/* Bank 00 interrupt handler variants */
RecompReturn I_IRQ_M0X0(CpuState *cpu);
RecompReturn I_IRQ_M0X1(CpuState *cpu);
RecompReturn I_IRQ_M1X0(CpuState *cpu);
RecompReturn I_IRQ_M1X1(CpuState *cpu);
RecompReturn I_NMI_M0X0(CpuState *cpu);
RecompReturn I_NMI_M0X1(CpuState *cpu);
RecompReturn I_NMI_M1X0(CpuState *cpu);
RecompReturn I_NMI_M1X1(CpuState *cpu);
RecompReturn I_RESET_M1X1(CpuState *cpu);

/* Bank 00 function declarations */
RecompReturn ResetHandler_M1X1(CpuState *cpu);
RecompReturn NmiTrampoline_M1X1(CpuState *cpu);
RecompReturn IrqTrampoline_M1X1(CpuState *cpu);

/* SPC upload routines */
RecompReturn SpcUploadInner_M1X1(CpuState *cpu);
RecompReturn SpcUploadEntry_M1X1(CpuState *cpu);
RecompReturn SpcUploadData_M1X1(CpuState *cpu);
RecompReturn SpcUploadSamples_M1X1(CpuState *cpu);

/* PPU/DMA setup */
RecompReturn SetupPpuSettings_M1X1(CpuState *cpu);
RecompReturn TurnOffIO_M1X1(CpuState *cpu);

/* Palette routines */
RecompReturn LoadPalette_M1X1(CpuState *cpu);
RecompReturn UpdatePalette_M1X1(CpuState *cpu);

/* Stripe/image loading */
RecompReturn LoadStripeImage_M1X1(CpuState *cpu);
RecompReturn ClearLayer3Tilemap_M1X1(CpuState *cpu);

/* Input handling */
RecompReturn PollJoypadInputs_M1X1(CpuState *cpu);

/* Status bar */
RecompReturn UpdateStatusBar_M1X1(CpuState *cpu);
RecompReturn UploadStatusBarTilemap_M1X1(CpuState *cpu);

/* Graphics decompression */
RecompReturn DecompressGraphics_M1X1(CpuState *cpu);
RecompReturn GenerateTile_M1X1(CpuState *cpu);

/* Level loading helpers */
RecompReturn LoadLevelData_M1X1(CpuState *cpu);
RecompReturn InitLevelRAM_M1X1(CpuState *cpu);

/* Bank $C0 (MMC window) function declarations */
RecompReturn NmiHandler_M1X1(CpuState *cpu);
RecompReturn IrqHandler_M1X1(CpuState *cpu);
RecompReturn Sdd1Init_M1X1(CpuState *cpu);
RecompReturn SpcUpload_M1X1(CpuState *cpu);
RecompReturn GameInit_M1X1(CpuState *cpu);
RecompReturn MainLoop_M1X1(CpuState *cpu);
RecompReturn TaskDispatch_M1X1(CpuState *cpu);
RecompReturn DmaSetupForSdd1_M1X1(CpuState *cpu);
RecompReturn CheckSdd1Status_M1X1(CpuState *cpu);
RecompReturn VBlankHandler_M1X1(CpuState *cpu);
RecompReturn UploadTilemap_M1X1(CpuState *cpu);
RecompReturn UpdatePaletteVBlank_M1X1(CpuState *cpu);
RecompReturn BattleMain_M1X1(CpuState *cpu);
RecompReturn BattleUpdate_M1X1(CpuState *cpu);
RecompReturn FieldRender_M1X1(CpuState *cpu);
RecompReturn FieldUpdate_M1X1(CpuState *cpu);
RecompReturn MenuMain_M1X1(CpuState *cpu);
RecompReturn MenuUpdate_M1X1(CpuState *cpu);
RecompReturn AcknowledgeIrq_M1X1(CpuState *cpu);
RecompReturn NmiComplete_M1X1(CpuState *cpu);

/* Add more function declarations as needed by the generated code */

#endif /* FUNCS_H */
