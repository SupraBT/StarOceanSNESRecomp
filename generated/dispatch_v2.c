/* Auto-generated from the authoritative LLE/AOT manifest. */
#include "cpu_state.h"

RecompReturn SpcUploadSetup_M1X1(CpuState *cpu);
RecompReturn SetupPpuAndDma_M1X1(CpuState *cpu);
RecompReturn bank_00_83B3_M1X1(CpuState *cpu);
RecompReturn PpuConfigB_M1X1(CpuState *cpu);
RecompReturn ShortWait_M1X1(CpuState *cpu);
RecompReturn bank_00_856A_M1X1(CpuState *cpu);
RecompReturn DecompressAndUpload_M1X1(CpuState *cpu);
RecompReturn bank_00_8E9F_M1X1(CpuState *cpu);
RecompReturn SendSpcCommand_M1X1(CpuState *cpu);
RecompReturn ReadSpcResponse_M1X1(CpuState *cpu);
RecompReturn ConfigurePpuRegisters_M1X1(CpuState *cpu);
RecompReturn FadePalette_M1X1(CpuState *cpu);
RecompReturn bank_00_98CF_M1X1(CpuState *cpu);
RecompReturn UploadTilemaps_M1X1(CpuState *cpu);
RecompReturn bank_00_9A11_M1X1(CpuState *cpu);
RecompReturn DecompressGraphics_M1X1(CpuState *cpu);
RecompReturn bank_00_9C73_M1X1(CpuState *cpu);
RecompReturn LoadStripeImages_M1X1(CpuState *cpu);
RecompReturn bank_00_9CA7_M1X1(CpuState *cpu);
RecompReturn PollControllers_M1X1(CpuState *cpu);
RecompReturn bank_00_9D8B_M1X1(CpuState *cpu);
RecompReturn UpdateStatusBar_M1X1(CpuState *cpu);
RecompReturn bank_00_9F2C_M1X1(CpuState *cpu);
RecompReturn ModeHelper1_M1X1(CpuState *cpu);
RecompReturn bank_00_9FB7_M1X1(CpuState *cpu);
RecompReturn ProcessLevelData_M1X1(CpuState *cpu);
RecompReturn Utility1_M1X1(CpuState *cpu);
RecompReturn bank_00_AB8C_M1X1(CpuState *cpu);
RecompReturn Utility2_M1X1(CpuState *cpu);
RecompReturn bank_00_B03E_M1X1(CpuState *cpu);
RecompReturn LoadString_M1X1(CpuState *cpu);
RecompReturn bank_00_B9A8_M1X1(CpuState *cpu);
RecompReturn DecompressEngine_M1X1(CpuState *cpu);
RecompReturn NmiTrampoline_M0X0(CpuState *cpu);
RecompReturn NmiTrampoline_M0X1(CpuState *cpu);
RecompReturn NmiTrampoline_M1X0(CpuState *cpu);
RecompReturn NmiTrampoline_M1X1(CpuState *cpu);
RecompReturn IrqTrampoline_M0X0(CpuState *cpu);
RecompReturn IrqTrampoline_M0X1(CpuState *cpu);
RecompReturn IrqTrampoline_M1X0(CpuState *cpu);
RecompReturn IrqTrampoline_M1X1(CpuState *cpu);
RecompReturn ResetHandler_M1X1(CpuState *cpu);
RecompReturn BootMmcEntry_M0X0(CpuState *cpu);
RecompReturn BootMmcEntry_M1X1(CpuState *cpu);
RecompReturn NmiHandler_M1X1(CpuState *cpu);
RecompReturn Sdd1Init_M1X1(CpuState *cpu);
RecompReturn SpcUpload_M1X1(CpuState *cpu);
RecompReturn GameInit_M1X1(CpuState *cpu);
RecompReturn TaskDispatch_M1X1(CpuState *cpu);
RecompReturn DmaSetupForSdd1_M1X1(CpuState *cpu);
RecompReturn CheckSdd1Status_M1X1(CpuState *cpu);
RecompReturn VBlankHandler_M1X1(CpuState *cpu);
RecompReturn UploadTilemap_M1X1(CpuState *cpu);
RecompReturn BattleMain_M1X1(CpuState *cpu);
RecompReturn BattleUpdate_M1X1(CpuState *cpu);
RecompReturn FieldRender_M1X1(CpuState *cpu);
RecompReturn FieldUpdate_M1X1(CpuState *cpu);
RecompReturn BlitMenuTiles_M1X0(CpuState *cpu);
RecompReturn bank_C2_FDF0_M1X0(CpuState *cpu);
RecompReturn bank_C2_FEE5_M0X0(CpuState *cpu);
RecompReturn bank_C3_9B46_M1X0(CpuState *cpu);
RecompReturn bank_C3_9D44_M1X0(CpuState *cpu);
RecompReturn bank_C3_AD6E_M0X0(CpuState *cpu);
RecompReturn bank_C3_ADAC_M0X0(CpuState *cpu);
RecompReturn bank_C9_D9EF_M1X1(CpuState *cpu);
RecompReturn LayoutTableIndexA_M1X1(CpuState *cpu);
RecompReturn LayoutTableIndexB_M1X1(CpuState *cpu);

const DispatchEntry g_dispatch_table[] = {
    { 0x008079u, { NULL, NULL, NULL, NULL }, 0 },  /* SpcUploadInit */
    { 0x0080E8u, { NULL, NULL, NULL, SpcUploadSetup_M1X1 }, 0 },  /* SpcUploadSetup */
    { 0x0080F7u, { NULL, NULL, NULL, NULL }, 0 },  /* SpcUploadData */
    { 0x008319u, { NULL, NULL, NULL, SetupPpuAndDma_M1X1 }, 0 },  /* SetupPpuAndDma */
    { 0x00832Du, { NULL, NULL, NULL, NULL }, 0 },  /* bank_00_832D */
    { 0x008364u, { NULL, NULL, NULL, NULL }, 0 },  /* PpuConfigA */
    { 0x0083B3u, { NULL, NULL, NULL, bank_00_83B3_M1X1 }, 0 },  /* bank_00_83B3 */
    { 0x008419u, { NULL, NULL, NULL, PpuConfigB_M1X1 }, 0 },  /* PpuConfigB */
    { 0x00843Bu, { NULL, NULL, NULL, NULL }, 0 },  /* NmiSubEntry1 */
    { 0x008449u, { NULL, NULL, NULL, NULL }, 0 },  /* NmiSubEntry2 */
    { 0x008500u, { NULL, NULL, NULL, NULL }, 0 },  /* WaitForVBlank */
    { 0x008568u, { NULL, NULL, NULL, ShortWait_M1X1 }, 0 },  /* ShortWait */
    { 0x00856Au, { NULL, NULL, NULL, bank_00_856A_M1X1 }, 0 },  /* bank_00_856A */
    { 0x008A00u, { NULL, NULL, NULL, NULL }, 0 },  /* MainInit */
    { 0x008CADu, { NULL, NULL, NULL, NULL }, 0 },  /* LoadCompressedData */
    { 0x008D7Bu, { NULL, NULL, NULL, DecompressAndUpload_M1X1 }, 0 },  /* DecompressAndUpload */
    { 0x008E9Fu, { NULL, NULL, NULL, bank_00_8E9F_M1X1 }, 0 },  /* bank_00_8E9F */
    { 0x008F7Bu, { NULL, NULL, NULL, SendSpcCommand_M1X1 }, 0 },  /* SendSpcCommand */
    { 0x009043u, { NULL, NULL, NULL, ReadSpcResponse_M1X1 }, 0 },  /* ReadSpcResponse */
    { 0x0095ADu, { NULL, NULL, NULL, ConfigurePpuRegisters_M1X1 }, 0 },  /* ConfigurePpuRegisters */
    { 0x00985Au, { NULL, NULL, NULL, NULL }, 0 },  /* LoadPalettes */
    { 0x0098A5u, { NULL, NULL, NULL, FadePalette_M1X1 }, 0 },  /* FadePalette */
    { 0x0098CFu, { NULL, NULL, NULL, bank_00_98CF_M1X1 }, 0 },  /* bank_00_98CF */
    { 0x009900u, { NULL, NULL, NULL, NULL }, 0 },  /* SetupHdma */
    { 0x0099E6u, { NULL, NULL, NULL, UploadTilemaps_M1X1 }, 0 },  /* UploadTilemaps */
    { 0x009A11u, { NULL, NULL, NULL, bank_00_9A11_M1X1 }, 0 },  /* bank_00_9A11 */
    { 0x009AADu, { NULL, NULL, NULL, DecompressGraphics_M1X1 }, 0 },  /* DecompressGraphics */
    { 0x009C73u, { NULL, NULL, NULL, bank_00_9C73_M1X1 }, 0 },  /* bank_00_9C73 */
    { 0x009CA5u, { NULL, NULL, NULL, LoadStripeImages_M1X1 }, 0 },  /* LoadStripeImages */
    { 0x009CA7u, { NULL, NULL, NULL, bank_00_9CA7_M1X1 }, 0 },  /* bank_00_9CA7 */
    { 0x009D00u, { NULL, NULL, NULL, NULL }, 0 },  /* UpdateOam */
    { 0x009D7Bu, { NULL, NULL, NULL, PollControllers_M1X1 }, 0 },  /* PollControllers */
    { 0x009D8Bu, { NULL, NULL, NULL, bank_00_9D8B_M1X1 }, 0 },  /* bank_00_9D8B */
    { 0x009EA0u, { NULL, NULL, NULL, UpdateStatusBar_M1X1 }, 0 },  /* UpdateStatusBar */
    { 0x009F2Cu, { NULL, NULL, NULL, bank_00_9F2C_M1X1 }, 0 },  /* bank_00_9F2C */
    { 0x009FADu, { NULL, NULL, NULL, ModeHelper1_M1X1 }, 0 },  /* ModeHelper1 */
    { 0x009FB7u, { NULL, NULL, NULL, bank_00_9FB7_M1X1 }, 0 },  /* bank_00_9FB7 */
    { 0x00A1A5u, { NULL, NULL, NULL, NULL }, 0 },  /* LoadLevelData */
    { 0x00A28Bu, { NULL, NULL, NULL, ProcessLevelData_M1X1 }, 0 },  /* ProcessLevelData */
    { 0x00A2F6u, { NULL, NULL, NULL, NULL }, 0 },  /* bank_00_A2F6 */
    { 0x00A500u, { NULL, NULL, NULL, NULL }, 0 },  /* ProcessObjects */
    { 0x00A58Bu, { NULL, NULL, NULL, NULL }, 0 },  /* UpdateSprites */
    { 0x00A98Bu, { NULL, NULL, NULL, NULL }, 0 },  /* CheckCollisions */
    { 0x00AA00u, { NULL, NULL, NULL, NULL }, 0 },  /* SendSoundCommand */
    { 0x00AB48u, { NULL, NULL, NULL, Utility1_M1X1 }, 0 },  /* Utility1 */
    { 0x00AB8Cu, { NULL, NULL, NULL, bank_00_AB8C_M1X1 }, 0 },  /* bank_00_AB8C */
    { 0x00B022u, { NULL, NULL, NULL, Utility2_M1X1 }, 0 },  /* Utility2 */
    { 0x00B03Eu, { NULL, NULL, NULL, bank_00_B03E_M1X1 }, 0 },  /* bank_00_B03E */
    { 0x00B164u, { NULL, NULL, NULL, NULL }, 0 },  /* LoadMapData */
    { 0x00B2A0u, { NULL, NULL, NULL, NULL }, 0 },  /* UpdateMap */
    { 0x00B983u, { NULL, NULL, NULL, NULL }, 0 },  /* DecompressFetchByte */
    { 0x00B99Bu, { NULL, NULL, NULL, LoadString_M1X1 }, 0 },  /* LoadString */
    { 0x00B9A8u, { NULL, NULL, NULL, bank_00_B9A8_M1X1 }, 0 },  /* bank_00_B9A8 */
    { 0x00BC5Au, { NULL, NULL, NULL, NULL }, 0 },  /* SetupDmaTransfer */
    { 0x00BDE8u, { NULL, NULL, NULL, DecompressEngine_M1X1 }, 0 },  /* DecompressEngine */
    { 0x00BEA5u, { NULL, NULL, NULL, NULL }, 0 },  /* FinalizeLoad */
    { 0x00FEB9u, { NmiTrampoline_M0X0, NmiTrampoline_M0X1, NmiTrampoline_M1X0, NmiTrampoline_M1X1 }, 0 },  /* NmiTrampoline */
    { 0x00FEBDu, { IrqTrampoline_M0X0, IrqTrampoline_M0X1, IrqTrampoline_M1X0, IrqTrampoline_M1X1 }, 0 },  /* IrqTrampoline */
    { 0x00FEC1u, { NULL, NULL, NULL, ResetHandler_M1X1 }, 0 },  /* ResetHandler */
    { 0x00FF96u, { BootMmcEntry_M0X0, NULL, NULL, BootMmcEntry_M1X1 }, 0 },  /* BootMmcEntry */
    { 0xC00000u, { NULL, NULL, NULL, NmiHandler_M1X1 }, 0 },  /* NmiHandler */
    { 0xC00221u, { NULL, NULL, NULL, NULL }, 0 },  /* IrqHandler */
    { 0xC00400u, { NULL, NULL, NULL, Sdd1Init_M1X1 }, 0 },  /* Sdd1Init */
    { 0xC00600u, { NULL, NULL, NULL, SpcUpload_M1X1 }, 0 },  /* SpcUpload */
    { 0xC00800u, { NULL, NULL, NULL, GameInit_M1X1 }, 0 },  /* GameInit */
    { 0xC00A00u, { NULL, NULL, NULL, NULL }, 0 },  /* MainLoop */
    { 0xC00C00u, { NULL, NULL, NULL, TaskDispatch_M1X1 }, 0 },  /* TaskDispatch */
    { 0xC00E00u, { NULL, NULL, NULL, DmaSetupForSdd1_M1X1 }, 0 },  /* DmaSetupForSdd1 */
    { 0xC01000u, { NULL, NULL, NULL, CheckSdd1Status_M1X1 }, 0 },  /* CheckSdd1Status */
    { 0xC01200u, { NULL, NULL, NULL, VBlankHandler_M1X1 }, 0 },  /* VBlankHandler */
    { 0xC01400u, { NULL, NULL, NULL, UploadTilemap_M1X1 }, 0 },  /* UploadTilemap */
    { 0xC01600u, { NULL, NULL, NULL, NULL }, 0 },  /* UpdatePaletteVBlank */
    { 0xC01800u, { NULL, NULL, NULL, BattleMain_M1X1 }, 0 },  /* BattleMain */
    { 0xC01A00u, { NULL, NULL, NULL, BattleUpdate_M1X1 }, 0 },  /* BattleUpdate */
    { 0xC01C00u, { NULL, NULL, NULL, FieldRender_M1X1 }, 0 },  /* FieldRender */
    { 0xC01E00u, { NULL, NULL, NULL, FieldUpdate_M1X1 }, 0 },  /* FieldUpdate */
    { 0xC02000u, { NULL, NULL, NULL, NULL }, 0 },  /* MenuMain */
    { 0xC02200u, { NULL, NULL, NULL, NULL }, 0 },  /* MenuUpdate */
    { 0xC02400u, { NULL, NULL, NULL, NULL }, 0 },  /* AcknowledgeIrq */
    { 0xC02600u, { NULL, NULL, NULL, NULL }, 0 },  /* NmiComplete */
    { 0xC2FC43u, { NULL, NULL, BlitMenuTiles_M1X0, NULL }, 0 },  /* BlitMenuTiles */
    { 0xC2FDF0u, { NULL, NULL, bank_C2_FDF0_M1X0, NULL }, 0 },  /* bank_C2_FDF0 */
    { 0xC2FEE5u, { bank_C2_FEE5_M0X0, NULL, NULL, NULL }, 0 },  /* bank_C2_FEE5 */
    { 0xC38F50u, { NULL, NULL, NULL, NULL }, 0 },  /* StarField */
    { 0xC3917Cu, { NULL, NULL, NULL, NULL }, 0 },  /* bank_C3_917C */
    { 0xC39B46u, { NULL, NULL, bank_C3_9B46_M1X0, NULL }, 0 },  /* bank_C3_9B46 */
    { 0xC39D44u, { NULL, NULL, bank_C3_9D44_M1X0, NULL }, 0 },  /* bank_C3_9D44 */
    { 0xC3AD6Eu, { bank_C3_AD6E_M0X0, NULL, NULL, NULL }, 0 },  /* bank_C3_AD6E */
    { 0xC3ADACu, { bank_C3_ADAC_M0X0, NULL, NULL, NULL }, 0 },  /* bank_C3_ADAC */
    { 0xC9D9EFu, { NULL, NULL, NULL, bank_C9_D9EF_M1X1 }, 0 },  /* bank_C9_D9EF */
    { 0xC9E4DCu, { NULL, NULL, NULL, LayoutTableIndexA_M1X1 }, 0 },  /* LayoutTableIndexA */
    { 0xC9E57Bu, { NULL, NULL, NULL, LayoutTableIndexB_M1X1 }, 0 },  /* LayoutTableIndexB */
};

const unsigned g_dispatch_table_count =
    (unsigned)(sizeof(g_dispatch_table) / sizeof(g_dispatch_table[0]));

const RamRoutineGuard g_ram_routine_guards[] = {
    { 0xFFFFFFFFu, 0u, 0u },
};

const unsigned g_ram_routine_guard_count =
    (unsigned)(sizeof(g_ram_routine_guards) / sizeof(g_ram_routine_guards[0]));
