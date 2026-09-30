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
RecompReturn bank_23_CD77_M1X1(CpuState *cpu);
RecompReturn bank_2E_8220_M1X1(CpuState *cpu);
RecompReturn Ghidra_8114_M1X1(CpuState *cpu);
RecompReturn Ghidra_824E_M1X1(CpuState *cpu);
RecompReturn Ghidra_8496_M1X1(CpuState *cpu);
RecompReturn bank_C0_84AB_M1X1(CpuState *cpu);
RecompReturn Ghidra_84B8_M1X1(CpuState *cpu);
RecompReturn Ghidra_8594_M1X1(CpuState *cpu);
RecompReturn bank_C0_85CC_M1X1(CpuState *cpu);
RecompReturn Ghidra_85FE_M1X1(CpuState *cpu);
RecompReturn Ghidra_862A_M1X1(CpuState *cpu);
RecompReturn Ghidra_878C_M1X1(CpuState *cpu);
RecompReturn bank_C0_E630_M1X1(CpuState *cpu);
RecompReturn Call_C28000_M1X1(CpuState *cpu);
RecompReturn Call_C2809D_M1X1(CpuState *cpu);
RecompReturn Call_C280A9_M1X1(CpuState *cpu);
RecompReturn Call_C280AB_M1X1(CpuState *cpu);
RecompReturn Call_C280AD_M1X1(CpuState *cpu);
RecompReturn Call_C280C8_M1X1(CpuState *cpu);
RecompReturn Call_C2813F_M1X1(CpuState *cpu);
RecompReturn Call_C2817A_M1X1(CpuState *cpu);
RecompReturn Call_C281A9_M1X1(CpuState *cpu);
RecompReturn Call_C28201_M1X1(CpuState *cpu);
RecompReturn Call_C2829E_M1X1(CpuState *cpu);
RecompReturn Call_C282BF_M1X1(CpuState *cpu);
RecompReturn Call_C2830C_M1X1(CpuState *cpu);
RecompReturn Call_C28B46_M1X1(CpuState *cpu);
RecompReturn Call_C28B5A_M1X1(CpuState *cpu);
RecompReturn Call_C28C88_M1X1(CpuState *cpu);
RecompReturn Call_C28C8D_M1X1(CpuState *cpu);
RecompReturn Call_C28CAD_M1X1(CpuState *cpu);
RecompReturn Call_C28D4A_M1X1(CpuState *cpu);
RecompReturn Call_C28E01_M1X1(CpuState *cpu);
RecompReturn Call_C28E04_M1X1(CpuState *cpu);
RecompReturn Call_C28E20_M1X1(CpuState *cpu);
RecompReturn Call_C28E22_M1X1(CpuState *cpu);
RecompReturn Call_C28E9C_M1X1(CpuState *cpu);
RecompReturn Call_C28EAD_M1X1(CpuState *cpu);
RecompReturn Call_C28EBB_M1X1(CpuState *cpu);
RecompReturn Call_C29DBA_M1X1(CpuState *cpu);
RecompReturn Call_C29DC8_M1X1(CpuState *cpu);
RecompReturn Call_C29DDF_M1X1(CpuState *cpu);
RecompReturn Call_C29E65_M1X1(CpuState *cpu);
RecompReturn Call_C29EAA_M1X1(CpuState *cpu);
RecompReturn Call_C29EB4_M1X1(CpuState *cpu);
RecompReturn Call_C29F07_M1X1(CpuState *cpu);
RecompReturn Call_C29F58_M1X1(CpuState *cpu);
RecompReturn Call_C29F7E_M1X1(CpuState *cpu);
RecompReturn Call_C2A084_M1X1(CpuState *cpu);
RecompReturn Call_C2A089_M1X1(CpuState *cpu);
RecompReturn Call_C2A0A2_M1X1(CpuState *cpu);
RecompReturn Call_C2A0A3_M1X1(CpuState *cpu);
RecompReturn Call_C2A0A9_M1X1(CpuState *cpu);
RecompReturn Call_C2A2A4_M1X1(CpuState *cpu);
RecompReturn Call_C2A2E9_M1X1(CpuState *cpu);
RecompReturn bank_C2_BB73_M1X1(CpuState *cpu);
RecompReturn Call_C2CD7F_M1X1(CpuState *cpu);
RecompReturn Call_C2CD9C_M1X1(CpuState *cpu);
RecompReturn Call_C2CDD0_M1X1(CpuState *cpu);
RecompReturn Call_C2D7F6_M1X1(CpuState *cpu);
RecompReturn Call_C2D88C_M1X1(CpuState *cpu);
RecompReturn Call_C2D8AC_M1X1(CpuState *cpu);
RecompReturn Call_C2D8AD_M1X1(CpuState *cpu);
RecompReturn Call_C2D8C3_M1X1(CpuState *cpu);
RecompReturn Call_C2D9A5_M1X1(CpuState *cpu);
RecompReturn Call_C2D9BF_M1X1(CpuState *cpu);
RecompReturn Call_C2DAD9_M1X1(CpuState *cpu);
RecompReturn Call_C2DB33_M1X1(CpuState *cpu);
RecompReturn Call_C2DDAD_M1X1(CpuState *cpu);
RecompReturn Call_C2DF88_M1X1(CpuState *cpu);
RecompReturn Call_C2DFAD_M1X1(CpuState *cpu);
RecompReturn Call_C2DFCE_M1X1(CpuState *cpu);
RecompReturn Call_C2DFEE_M1X1(CpuState *cpu);
RecompReturn Call_C2FC2F_M1X1(CpuState *cpu);
RecompReturn Call_C2FC81_M1X1(CpuState *cpu);
RecompReturn Call_C2FD29_M1X1(CpuState *cpu);
RecompReturn Call_C2FDF0_M1X1(CpuState *cpu);
RecompReturn Call_C2FE73_M1X1(CpuState *cpu);
RecompReturn Call_C2FE92_M1X1(CpuState *cpu);
RecompReturn Call_C2FEA9_M1X1(CpuState *cpu);
RecompReturn Call_C2FEC6_M1X1(CpuState *cpu);
RecompReturn Call_C2FEC9_M1X1(CpuState *cpu);
RecompReturn Call_C2FEE5_M1X1(CpuState *cpu);
RecompReturn bank_C2_FFE2_M1X1(CpuState *cpu);
RecompReturn Call_C38BCF_M1X1(CpuState *cpu);
RecompReturn Call_C38CB3_M1X1(CpuState *cpu);
RecompReturn Call_C38CB9_M1X1(CpuState *cpu);
RecompReturn Call_C38D02_M1X1(CpuState *cpu);
RecompReturn Call_C38D3D_M1X1(CpuState *cpu);
RecompReturn Call_C38DCD_M1X1(CpuState *cpu);
RecompReturn Call_C38E00_M1X1(CpuState *cpu);
RecompReturn Call_C38F5E_M1X1(CpuState *cpu);
RecompReturn Call_C39022_M1X1(CpuState *cpu);
RecompReturn Call_C3908F_M1X1(CpuState *cpu);
RecompReturn Call_C39090_M1X1(CpuState *cpu);
RecompReturn Call_C39098_M1X1(CpuState *cpu);
RecompReturn Call_C390B9_M1X1(CpuState *cpu);
RecompReturn Call_C391DF_M1X1(CpuState *cpu);
RecompReturn Call_C3926E_M1X1(CpuState *cpu);
RecompReturn Call_C392A2_M1X1(CpuState *cpu);
RecompReturn Call_C39336_M1X1(CpuState *cpu);
RecompReturn Call_C394B9_M1X1(CpuState *cpu);
RecompReturn Call_C3951D_M1X1(CpuState *cpu);
RecompReturn bank_C3_9B37_M1X1(CpuState *cpu);
RecompReturn bank_C3_9DBE_M1X1(CpuState *cpu);
RecompReturn bank_C3_A7B7_M1X1(CpuState *cpu);
RecompReturn Call_C3AE11_M1X1(CpuState *cpu);
RecompReturn Call_C3AE22_M1X1(CpuState *cpu);
RecompReturn bank_C3_BD6C_M1X1(CpuState *cpu);
RecompReturn bank_C3_CB6C_M1X1(CpuState *cpu);
RecompReturn bank_C3_CBA5_M1X1(CpuState *cpu);
RecompReturn bank_C3_DF7F_M1X1(CpuState *cpu);
RecompReturn bank_C3_F46D_M1X1(CpuState *cpu);
RecompReturn bank_C3_FDCB_M1X1(CpuState *cpu);
RecompReturn Call_C4F4D0_M1X1(CpuState *cpu);
RecompReturn Call_C4F4D4_M1X1(CpuState *cpu);
RecompReturn Call_C4F4D8_M1X1(CpuState *cpu);
RecompReturn Call_C4F4E0_M1X1(CpuState *cpu);
RecompReturn Call_C4F4E4_M1X1(CpuState *cpu);
RecompReturn Call_C4F4EE_M1X1(CpuState *cpu);
RecompReturn bank_C4_F501_M1X1(CpuState *cpu);
RecompReturn Call_C4F53E_M1X1(CpuState *cpu);
RecompReturn Call_C4F542_M1X1(CpuState *cpu);
RecompReturn Call_C4F559_M1X1(CpuState *cpu);
RecompReturn Call_C4F572_M1X1(CpuState *cpu);
RecompReturn Call_C4F584_M1X1(CpuState *cpu);
RecompReturn Call_C4F58B_M1X1(CpuState *cpu);
RecompReturn Call_C4F59F_M1X1(CpuState *cpu);
RecompReturn Call_C4F673_M1X1(CpuState *cpu);
RecompReturn Call_C4F920_M1X1(CpuState *cpu);
RecompReturn Call_C4F932_M1X1(CpuState *cpu);
RecompReturn Call_C6E2B9_M1X1(CpuState *cpu);
RecompReturn Call_C6F6F9_M1X1(CpuState *cpu);
RecompReturn Call_C6F700_M1X1(CpuState *cpu);
RecompReturn Call_C6F77F_M1X1(CpuState *cpu);
RecompReturn Call_C6F7B0_M1X1(CpuState *cpu);
RecompReturn Call_C6F7D1_M1X1(CpuState *cpu);
RecompReturn Call_C6F800_M1X1(CpuState *cpu);
RecompReturn Call_C6F801_M1X1(CpuState *cpu);
RecompReturn Call_C6F83E_M1X1(CpuState *cpu);
RecompReturn Call_C8F4B7_M1X1(CpuState *cpu);
RecompReturn Call_C8F4D0_M1X1(CpuState *cpu);
RecompReturn Call_C8F8DA_M1X1(CpuState *cpu);
RecompReturn LayoutTableIndexA_M1X1(CpuState *cpu);
RecompReturn LayoutTableIndexB_M1X1(CpuState *cpu);
RecompReturn Call_CA88A9_M1X1(CpuState *cpu);
RecompReturn Call_CA8916_M1X1(CpuState *cpu);
RecompReturn Call_CA8EAD_M1X1(CpuState *cpu);
RecompReturn Call_CA8EB3_M1X1(CpuState *cpu);
RecompReturn Call_CAA941_M1X1(CpuState *cpu);
RecompReturn Call_CAA943_M1X1(CpuState *cpu);
RecompReturn Call_CAA9EB_M1X1(CpuState *cpu);
RecompReturn Call_CAAA00_M1X1(CpuState *cpu);
RecompReturn Call_CAAD23_M1X1(CpuState *cpu);
RecompReturn Call_CAAD2A_M1X1(CpuState *cpu);
RecompReturn Call_CAB48D_M1X1(CpuState *cpu);
RecompReturn Call_CAB9A1_M1X1(CpuState *cpu);
RecompReturn Call_CABA16_M1X1(CpuState *cpu);
RecompReturn Call_CABA1B_M1X1(CpuState *cpu);
RecompReturn Call_CABBCF_M1X1(CpuState *cpu);
RecompReturn Call_CABCAD_M1X1(CpuState *cpu);
RecompReturn Call_CAC0F1_M1X1(CpuState *cpu);
RecompReturn Call_CAC120_M1X1(CpuState *cpu);
RecompReturn Call_CAC640_M1X1(CpuState *cpu);
RecompReturn Call_CAC686_M1X1(CpuState *cpu);
RecompReturn bank_CC_B7ED_M1X1(CpuState *cpu);
RecompReturn Call_CCE584_M1X1(CpuState *cpu);
RecompReturn bank_CE_A9D8_M1X1(CpuState *cpu);

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
    { 0x0BC837u, { NULL, NULL, NULL, NULL }, 0 },  /* bank_0B_C837 */
    { 0x0FC1B1u, { NULL, NULL, NULL, NULL }, 0 },  /* bank_0F_C1B1 */
    { 0x12DFF4u, { NULL, NULL, NULL, NULL }, 0 },  /* bank_12_DFF4 */
    { 0x1C8000u, { NULL, NULL, NULL, NULL }, 0 },  /* bank_1C_8000 */
    { 0x23CD77u, { NULL, NULL, NULL, bank_23_CD77_M1X1 }, 0 },  /* bank_23_CD77 */
    { 0x2E8220u, { NULL, NULL, NULL, bank_2E_8220_M1X1 }, 0 },  /* bank_2E_8220 */
    { 0x82D297u, { NULL, NULL, NULL, NULL }, 0 },  /* bank_82_D297 */
    { 0x839EADu, { NULL, NULL, NULL, NULL }, 0 },  /* bank_83_9EAD */
    { 0xB9EE3Cu, { NULL, NULL, NULL, NULL }, 0 },  /* bank_B9_EE3C */
    { 0xC00221u, { NULL, NULL, NULL, NULL }, 0 },  /* IrqHandler */
    { 0xC002F6u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_02F6 */
    { 0xC0032Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_032C */
    { 0xC0035Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_035B */
    { 0xC00387u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_0387 */
    { 0xC01E64u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_1E64 */
    { 0xC02AB2u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_2AB2 */
    { 0xC03F76u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_3F76 */
    { 0xC0431Du, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_431D */
    { 0xC043B1u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_43B1 */
    { 0xC04C53u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_4C53 */
    { 0xC04D39u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_4D39 */
    { 0xC04EB0u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_4EB0 */
    { 0xC04F22u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_4F22 */
    { 0xC05193u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_5193 */
    { 0xC051F3u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_51F3 */
    { 0xC05202u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_5202 */
    { 0xC05220u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_5220 */
    { 0xC05233u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_5233 */
    { 0xC0524Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_524F */
    { 0xC05262u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_5262 */
    { 0xC08001u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_8001 */
    { 0xC08114u, { NULL, NULL, NULL, Ghidra_8114_M1X1 }, 0 },  /* Ghidra_8114 */
    { 0xC0824Eu, { NULL, NULL, NULL, Ghidra_824E_M1X1 }, 0 },  /* Ghidra_824E */
    { 0xC08496u, { NULL, NULL, NULL, Ghidra_8496_M1X1 }, 0 },  /* Ghidra_8496 */
    { 0xC084ABu, { NULL, NULL, NULL, bank_C0_84AB_M1X1 }, 0 },  /* bank_C0_84AB */
    { 0xC084B8u, { NULL, NULL, NULL, Ghidra_84B8_M1X1 }, 0 },  /* Ghidra_84B8 */
    { 0xC08594u, { NULL, NULL, NULL, Ghidra_8594_M1X1 }, 0 },  /* Ghidra_8594 */
    { 0xC085CCu, { NULL, NULL, NULL, bank_C0_85CC_M1X1 }, 0 },  /* bank_C0_85CC */
    { 0xC085FEu, { NULL, NULL, NULL, Ghidra_85FE_M1X1 }, 0 },  /* Ghidra_85FE */
    { 0xC0862Au, { NULL, NULL, NULL, Ghidra_862A_M1X1 }, 0 },  /* Ghidra_862A */
    { 0xC0878Cu, { NULL, NULL, NULL, Ghidra_878C_M1X1 }, 0 },  /* Ghidra_878C */
    { 0xC087B7u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_87B7 */
    { 0xC08812u, { NULL, NULL, NULL, NULL }, 0 },  /* Ghidra_8812 */
    { 0xC0E630u, { NULL, NULL, NULL, bank_C0_E630_M1X1 }, 0 },  /* bank_C0_E630 */
    { 0xC200A0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C200A0 */
    { 0xC200A2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C200A2 */
    { 0xC200A6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C200A6 */
    { 0xC200A7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C200A7 */
    { 0xC200A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C200A9 */
    { 0xC200ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C200AD */
    { 0xC200B9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C200B9 */
    { 0xC200BDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C200BD */
    { 0xC200C9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C200C9 */
    { 0xC200D4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C200D4 */
    { 0xC200E6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C200E6 */
    { 0xC200F4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C200F4 */
    { 0xC200FAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C200FA */
    { 0xC20101u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C20101 */
    { 0xC20110u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C20110 */
    { 0xC20164u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C20164 */
    { 0xC20168u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C20168 */
    { 0xC2017Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2017E */
    { 0xC20B51u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C20B51 */
    { 0xC20B5Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C20B5E */
    { 0xC21258u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C21258 */
    { 0xC21288u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C21288 */
    { 0xC21290u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C21290 */
    { 0xC2129Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2129D */
    { 0xC212F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C212F0 */
    { 0xC217DEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C217DE */
    { 0xC217F7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C217F7 */
    { 0xC217FEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C217FE */
    { 0xC2180Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2180A */
    { 0xC21822u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C21822 */
    { 0xC21C72u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C21C72 */
    { 0xC21CA4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C21CA4 */
    { 0xC21CBFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C21CBF */
    { 0xC21CD0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C21CD0 */
    { 0xC21DF0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C21DF0 */
    { 0xC22510u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C22510 */
    { 0xC225ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C225AD */
    { 0xC22622u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C22622 */
    { 0xC22685u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C22685 */
    { 0xC226A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C226A5 */
    { 0xC226A6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C226A6 */
    { 0xC226A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C226A9 */
    { 0xC226BFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C226BF */
    { 0xC228A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C228A5 */
    { 0xC228A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C228A9 */
    { 0xC22C99u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C22C99 */
    { 0xC22C9Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C22C9E */
    { 0xC22CA5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C22CA5 */
    { 0xC22CFEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C22CFE */
    { 0xC22DBDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C22DBD */
    { 0xC2310Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2310C */
    { 0xC23180u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C23180 */
    { 0xC2319Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2319C */
    { 0xC231F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C231F0 */
    { 0xC236A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C236A9 */
    { 0xC236ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C236AD */
    { 0xC23720u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C23720 */
    { 0xC23741u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C23741 */
    { 0xC238ABu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C238AB */
    { 0xC238ACu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C238AC */
    { 0xC238ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C238AD */
    { 0xC238BDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C238BD */
    { 0xC238BFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C238BF */
    { 0xC238C6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C238C6 */
    { 0xC2390Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2390C */
    { 0xC2391Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2391C */
    { 0xC2398Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2398D */
    { 0xC239DBu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C239DB */
    { 0xC23A4Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C23A4D */
    { 0xC23A9Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C23A9C */
    { 0xC23AADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C23AAD */
    { 0xC23BAEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C23BAE */
    { 0xC23CA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C23CA9 */
    { 0xC24053u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24053 */
    { 0xC24070u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24070 */
    { 0xC24089u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24089 */
    { 0xC240EDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C240ED */
    { 0xC240F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C240F0 */
    { 0xC24131u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24131 */
    { 0xC24134u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24134 */
    { 0xC24181u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24181 */
    { 0xC24220u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24220 */
    { 0xC2423Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2423E */
    { 0xC24269u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24269 */
    { 0xC24E71u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24E71 */
    { 0xC24F17u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24F17 */
    { 0xC24F18u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24F18 */
    { 0xC24F38u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24F38 */
    { 0xC24F50u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24F50 */
    { 0xC24F60u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24F60 */
    { 0xC24F66u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C24F66 */
    { 0xC25020u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25020 */
    { 0xC251ECu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C251EC */
    { 0xC2529Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2529E */
    { 0xC252BDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C252BD */
    { 0xC253A2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C253A2 */
    { 0xC253A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C253A9 */
    { 0xC25520u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25520 */
    { 0xC256AAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C256AA */
    { 0xC256BDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C256BD */
    { 0xC256C8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C256C8 */
    { 0xC25706u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25706 */
    { 0xC2572Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2572C */
    { 0xC2579Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2579C */
    { 0xC257F4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C257F4 */
    { 0xC25804u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25804 */
    { 0xC2580Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2580C */
    { 0xC25870u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25870 */
    { 0xC2594Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2594D */
    { 0xC25A31u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25A31 */
    { 0xC25A35u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25A35 */
    { 0xC25CC1u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25CC1 */
    { 0xC25CF0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25CF0 */
    { 0xC25D27u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25D27 */
    { 0xC25DC3u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25DC3 */
    { 0xC25EADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25EAD */
    { 0xC25EB7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25EB7 */
    { 0xC25ED0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25ED0 */
    { 0xC25F8Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C25F8C */
    { 0xC26000u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C26000 */
    { 0xC26038u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C26038 */
    { 0xC26060u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C26060 */
    { 0xC26068u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C26068 */
    { 0xC26071u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C26071 */
    { 0xC2607Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2607A */
    { 0xC2607Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2607E */
    { 0xC2608Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2608D */
    { 0xC2609Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2609C */
    { 0xC260ABu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C260AB */
    { 0xC260CBu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C260CB */
    { 0xC2678Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2678D */
    { 0xC26791u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C26791 */
    { 0xC267AEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C267AE */
    { 0xC267AFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C267AF */
    { 0xC27EEDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C27EED */
    { 0xC27F29u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C27F29 */
    { 0xC27F49u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C27F49 */
    { 0xC27FA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C27FA9 */
    { 0xC27FD4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C27FD4 */
    { 0xC27FF8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C27FF8 */
    { 0xC28000u, { NULL, NULL, NULL, Call_C28000_M1X1 }, 0 },  /* Call_C28000 */
    { 0xC28040u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C28040 */
    { 0xC2805Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2805E */
    { 0xC28060u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C28060 */
    { 0xC2809Du, { NULL, NULL, NULL, Call_C2809D_M1X1 }, 0 },  /* Call_C2809D */
    { 0xC280A9u, { NULL, NULL, NULL, Call_C280A9_M1X1 }, 0 },  /* Call_C280A9 */
    { 0xC280ABu, { NULL, NULL, NULL, Call_C280AB_M1X1 }, 0 },  /* Call_C280AB */
    { 0xC280ADu, { NULL, NULL, NULL, Call_C280AD_M1X1 }, 0 },  /* Call_C280AD */
    { 0xC280C8u, { NULL, NULL, NULL, Call_C280C8_M1X1 }, 0 },  /* Call_C280C8 */
    { 0xC2813Fu, { NULL, NULL, NULL, Call_C2813F_M1X1 }, 0 },  /* Call_C2813F */
    { 0xC2817Au, { NULL, NULL, NULL, Call_C2817A_M1X1 }, 0 },  /* Call_C2817A */
    { 0xC281A9u, { NULL, NULL, NULL, Call_C281A9_M1X1 }, 0 },  /* Call_C281A9 */
    { 0xC28201u, { NULL, NULL, NULL, Call_C28201_M1X1 }, 0 },  /* Call_C28201 */
    { 0xC2829Eu, { NULL, NULL, NULL, Call_C2829E_M1X1 }, 0 },  /* Call_C2829E */
    { 0xC282BFu, { NULL, NULL, NULL, Call_C282BF_M1X1 }, 0 },  /* Call_C282BF */
    { 0xC2830Cu, { NULL, NULL, NULL, Call_C2830C_M1X1 }, 0 },  /* Call_C2830C */
    { 0xC28B46u, { NULL, NULL, NULL, Call_C28B46_M1X1 }, 0 },  /* Call_C28B46 */
    { 0xC28B5Au, { NULL, NULL, NULL, Call_C28B5A_M1X1 }, 0 },  /* Call_C28B5A */
    { 0xC28C88u, { NULL, NULL, NULL, Call_C28C88_M1X1 }, 0 },  /* Call_C28C88 */
    { 0xC28C8Du, { NULL, NULL, NULL, Call_C28C8D_M1X1 }, 0 },  /* Call_C28C8D */
    { 0xC28CADu, { NULL, NULL, NULL, Call_C28CAD_M1X1 }, 0 },  /* Call_C28CAD */
    { 0xC28D3Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C28D3A */
    { 0xC28D4Au, { NULL, NULL, NULL, Call_C28D4A_M1X1 }, 0 },  /* Call_C28D4A */
    { 0xC28E00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C28E00 */
    { 0xC28E01u, { NULL, NULL, NULL, Call_C28E01_M1X1 }, 0 },  /* Call_C28E01 */
    { 0xC28E02u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C28E02 */
    { 0xC28E04u, { NULL, NULL, NULL, Call_C28E04_M1X1 }, 0 },  /* Call_C28E04 */
    { 0xC28E20u, { NULL, NULL, NULL, Call_C28E20_M1X1 }, 0 },  /* Call_C28E20 */
    { 0xC28E22u, { NULL, NULL, NULL, Call_C28E22_M1X1 }, 0 },  /* Call_C28E22 */
    { 0xC28E9Cu, { NULL, NULL, NULL, Call_C28E9C_M1X1 }, 0 },  /* Call_C28E9C */
    { 0xC28EADu, { NULL, NULL, NULL, Call_C28EAD_M1X1 }, 0 },  /* Call_C28EAD */
    { 0xC28EBBu, { NULL, NULL, NULL, Call_C28EBB_M1X1 }, 0 },  /* Call_C28EBB */
    { 0xC29DBAu, { NULL, NULL, NULL, Call_C29DBA_M1X1 }, 0 },  /* Call_C29DBA */
    { 0xC29DC8u, { NULL, NULL, NULL, Call_C29DC8_M1X1 }, 0 },  /* Call_C29DC8 */
    { 0xC29DDFu, { NULL, NULL, NULL, Call_C29DDF_M1X1 }, 0 },  /* Call_C29DDF */
    { 0xC29E65u, { NULL, NULL, NULL, Call_C29E65_M1X1 }, 0 },  /* Call_C29E65 */
    { 0xC29EAAu, { NULL, NULL, NULL, Call_C29EAA_M1X1 }, 0 },  /* Call_C29EAA */
    { 0xC29EB4u, { NULL, NULL, NULL, Call_C29EB4_M1X1 }, 0 },  /* Call_C29EB4 */
    { 0xC29F07u, { NULL, NULL, NULL, Call_C29F07_M1X1 }, 0 },  /* Call_C29F07 */
    { 0xC29F58u, { NULL, NULL, NULL, Call_C29F58_M1X1 }, 0 },  /* Call_C29F58 */
    { 0xC29F7Eu, { NULL, NULL, NULL, Call_C29F7E_M1X1 }, 0 },  /* Call_C29F7E */
    { 0xC2A084u, { NULL, NULL, NULL, Call_C2A084_M1X1 }, 0 },  /* Call_C2A084 */
    { 0xC2A089u, { NULL, NULL, NULL, Call_C2A089_M1X1 }, 0 },  /* Call_C2A089 */
    { 0xC2A0A2u, { NULL, NULL, NULL, Call_C2A0A2_M1X1 }, 0 },  /* Call_C2A0A2 */
    { 0xC2A0A3u, { NULL, NULL, NULL, Call_C2A0A3_M1X1 }, 0 },  /* Call_C2A0A3 */
    { 0xC2A0A9u, { NULL, NULL, NULL, Call_C2A0A9_M1X1 }, 0 },  /* Call_C2A0A9 */
    { 0xC2A2A4u, { NULL, NULL, NULL, Call_C2A2A4_M1X1 }, 0 },  /* Call_C2A2A4 */
    { 0xC2A2E9u, { NULL, NULL, NULL, Call_C2A2E9_M1X1 }, 0 },  /* Call_C2A2E9 */
    { 0xC2BB73u, { NULL, NULL, NULL, bank_C2_BB73_M1X1 }, 0 },  /* bank_C2_BB73 */
    { 0xC2CD7Fu, { NULL, NULL, NULL, Call_C2CD7F_M1X1 }, 0 },  /* Call_C2CD7F */
    { 0xC2CD9Cu, { NULL, NULL, NULL, Call_C2CD9C_M1X1 }, 0 },  /* Call_C2CD9C */
    { 0xC2CDBEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2CDBE */
    { 0xC2CDD0u, { NULL, NULL, NULL, Call_C2CDD0_M1X1 }, 0 },  /* Call_C2CDD0 */
    { 0xC2CE1Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2CE1B */
    { 0xC2CE52u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2CE52 */
    { 0xC2CE7Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2CE7C */
    { 0xC2D000u, { NULL, NULL, NULL, NULL }, 0 },  /* bank_C2_D000 */
    { 0xC2D7F6u, { NULL, NULL, NULL, Call_C2D7F6_M1X1 }, 0 },  /* Call_C2D7F6 */
    { 0xC2D85Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2D85C */
    { 0xC2D88Cu, { NULL, NULL, NULL, Call_C2D88C_M1X1 }, 0 },  /* Call_C2D88C */
    { 0xC2D8ACu, { NULL, NULL, NULL, Call_C2D8AC_M1X1 }, 0 },  /* Call_C2D8AC */
    { 0xC2D8ADu, { NULL, NULL, NULL, Call_C2D8AD_M1X1 }, 0 },  /* Call_C2D8AD */
    { 0xC2D8C3u, { NULL, NULL, NULL, Call_C2D8C3_M1X1 }, 0 },  /* Call_C2D8C3 */
    { 0xC2D9A5u, { NULL, NULL, NULL, Call_C2D9A5_M1X1 }, 0 },  /* Call_C2D9A5 */
    { 0xC2D9BFu, { NULL, NULL, NULL, Call_C2D9BF_M1X1 }, 0 },  /* Call_C2D9BF */
    { 0xC2DAD9u, { NULL, NULL, NULL, Call_C2DAD9_M1X1 }, 0 },  /* Call_C2DAD9 */
    { 0xC2DB33u, { NULL, NULL, NULL, Call_C2DB33_M1X1 }, 0 },  /* Call_C2DB33 */
    { 0xC2DB9Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2DB9C */
    { 0xC2DDADu, { NULL, NULL, NULL, Call_C2DDAD_M1X1 }, 0 },  /* Call_C2DDAD */
    { 0xC2DF88u, { NULL, NULL, NULL, Call_C2DF88_M1X1 }, 0 },  /* Call_C2DF88 */
    { 0xC2DFADu, { NULL, NULL, NULL, Call_C2DFAD_M1X1 }, 0 },  /* Call_C2DFAD */
    { 0xC2DFCEu, { NULL, NULL, NULL, Call_C2DFCE_M1X1 }, 0 },  /* Call_C2DFCE */
    { 0xC2DFEEu, { NULL, NULL, NULL, Call_C2DFEE_M1X1 }, 0 },  /* Call_C2DFEE */
    { 0xC2E09Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2E09C */
    { 0xC2E0A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2E0A9 */
    { 0xC2E0ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2E0AD */
    { 0xC2E0D0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2E0D0 */
    { 0xC2FC2Fu, { NULL, NULL, NULL, Call_C2FC2F_M1X1 }, 0 },  /* Call_C2FC2F */
    { 0xC2FC81u, { NULL, NULL, NULL, Call_C2FC81_M1X1 }, 0 },  /* Call_C2FC81 */
    { 0xC2FD29u, { NULL, NULL, NULL, Call_C2FD29_M1X1 }, 0 },  /* Call_C2FD29 */
    { 0xC2FD77u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2FD77 */
    { 0xC2FD80u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2FD80 */
    { 0xC2FD9Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2FD9C */
    { 0xC2FD9Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C2FD9F */
    { 0xC2FDF0u, { NULL, NULL, NULL, Call_C2FDF0_M1X1 }, 0 },  /* Call_C2FDF0 */
    { 0xC2FE73u, { NULL, NULL, NULL, Call_C2FE73_M1X1 }, 0 },  /* Call_C2FE73 */
    { 0xC2FE92u, { NULL, NULL, NULL, Call_C2FE92_M1X1 }, 0 },  /* Call_C2FE92 */
    { 0xC2FEA9u, { NULL, NULL, NULL, Call_C2FEA9_M1X1 }, 0 },  /* Call_C2FEA9 */
    { 0xC2FEC6u, { NULL, NULL, NULL, Call_C2FEC6_M1X1 }, 0 },  /* Call_C2FEC6 */
    { 0xC2FEC9u, { NULL, NULL, NULL, Call_C2FEC9_M1X1 }, 0 },  /* Call_C2FEC9 */
    { 0xC2FEE5u, { NULL, NULL, NULL, Call_C2FEE5_M1X1 }, 0 },  /* Call_C2FEE5 */
    { 0xC2FFE2u, { NULL, NULL, NULL, bank_C2_FFE2_M1X1 }, 0 },  /* bank_C2_FFE2 */
    { 0xC38BB7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C38BB7 */
    { 0xC38BCFu, { NULL, NULL, NULL, Call_C38BCF_M1X1 }, 0 },  /* Call_C38BCF */
    { 0xC38CB3u, { NULL, NULL, NULL, Call_C38CB3_M1X1 }, 0 },  /* Call_C38CB3 */
    { 0xC38CB9u, { NULL, NULL, NULL, Call_C38CB9_M1X1 }, 0 },  /* Call_C38CB9 */
    { 0xC38D02u, { NULL, NULL, NULL, Call_C38D02_M1X1 }, 0 },  /* Call_C38D02 */
    { 0xC38D3Du, { NULL, NULL, NULL, Call_C38D3D_M1X1 }, 0 },  /* Call_C38D3D */
    { 0xC38D93u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C38D93 */
    { 0xC38DCDu, { NULL, NULL, NULL, Call_C38DCD_M1X1 }, 0 },  /* Call_C38DCD */
    { 0xC38E00u, { NULL, NULL, NULL, Call_C38E00_M1X1 }, 0 },  /* Call_C38E00 */
    { 0xC38EADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C38EAD */
    { 0xC38EB9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C38EB9 */
    { 0xC38ECDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C38ECD */
    { 0xC38F00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C38F00 */
    { 0xC38F5Eu, { NULL, NULL, NULL, Call_C38F5E_M1X1 }, 0 },  /* Call_C38F5E */
    { 0xC39022u, { NULL, NULL, NULL, Call_C39022_M1X1 }, 0 },  /* Call_C39022 */
    { 0xC3904Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C3904E */
    { 0xC3908Fu, { NULL, NULL, NULL, Call_C3908F_M1X1 }, 0 },  /* Call_C3908F */
    { 0xC39090u, { NULL, NULL, NULL, Call_C39090_M1X1 }, 0 },  /* Call_C39090 */
    { 0xC39098u, { NULL, NULL, NULL, Call_C39098_M1X1 }, 0 },  /* Call_C39098 */
    { 0xC390B9u, { NULL, NULL, NULL, Call_C390B9_M1X1 }, 0 },  /* Call_C390B9 */
    { 0xC3917Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C3917C */
    { 0xC391DFu, { NULL, NULL, NULL, Call_C391DF_M1X1 }, 0 },  /* Call_C391DF */
    { 0xC3926Eu, { NULL, NULL, NULL, Call_C3926E_M1X1 }, 0 },  /* Call_C3926E */
    { 0xC392A2u, { NULL, NULL, NULL, Call_C392A2_M1X1 }, 0 },  /* Call_C392A2 */
    { 0xC39336u, { NULL, NULL, NULL, Call_C39336_M1X1 }, 0 },  /* Call_C39336 */
    { 0xC394B9u, { NULL, NULL, NULL, Call_C394B9_M1X1 }, 0 },  /* Call_C394B9 */
    { 0xC3951Du, { NULL, NULL, NULL, Call_C3951D_M1X1 }, 0 },  /* Call_C3951D */
    { 0xC39B37u, { NULL, NULL, NULL, bank_C3_9B37_M1X1 }, 0 },  /* bank_C3_9B37 */
    { 0xC39DBEu, { NULL, NULL, NULL, bank_C3_9DBE_M1X1 }, 0 },  /* bank_C3_9DBE */
    { 0xC39E7Cu, { NULL, NULL, NULL, NULL }, 0 },  /* bank_C3_9E7C */
    { 0xC3A7B7u, { NULL, NULL, NULL, bank_C3_A7B7_M1X1 }, 0 },  /* bank_C3_A7B7 */
    { 0xC3AE11u, { NULL, NULL, NULL, Call_C3AE11_M1X1 }, 0 },  /* Call_C3AE11 */
    { 0xC3AE22u, { NULL, NULL, NULL, Call_C3AE22_M1X1 }, 0 },  /* Call_C3AE22 */
    { 0xC3BD6Cu, { NULL, NULL, NULL, bank_C3_BD6C_M1X1 }, 0 },  /* bank_C3_BD6C */
    { 0xC3CB6Cu, { NULL, NULL, NULL, bank_C3_CB6C_M1X1 }, 0 },  /* bank_C3_CB6C */
    { 0xC3CBA5u, { NULL, NULL, NULL, bank_C3_CBA5_M1X1 }, 0 },  /* bank_C3_CBA5 */
    { 0xC3DF7Fu, { NULL, NULL, NULL, bank_C3_DF7F_M1X1 }, 0 },  /* bank_C3_DF7F */
    { 0xC3E719u, { NULL, NULL, NULL, NULL }, 0 },  /* bank_C3_E719 */
    { 0xC3E75Du, { NULL, NULL, NULL, NULL }, 0 },  /* bank_C3_E75D */
    { 0xC3EFFCu, { NULL, NULL, NULL, NULL }, 0 },  /* bank_C3_EFFC */
    { 0xC3F46Du, { NULL, NULL, NULL, bank_C3_F46D_M1X1 }, 0 },  /* bank_C3_F46D */
    { 0xC3FC5Bu, { NULL, NULL, NULL, NULL }, 0 },  /* bank_C3_FC5B */
    { 0xC3FDCBu, { NULL, NULL, NULL, bank_C3_FDCB_M1X1 }, 0 },  /* bank_C3_FDCB */
    { 0xC49CA4u, { NULL, NULL, NULL, NULL }, 0 },  /* bank_C4_9CA4 */
    { 0xC4EF4Bu, { NULL, NULL, NULL, NULL }, 0 },  /* bank_C4_EF4B */
    { 0xC4F4D0u, { NULL, NULL, NULL, Call_C4F4D0_M1X1 }, 0 },  /* Call_C4F4D0 */
    { 0xC4F4D4u, { NULL, NULL, NULL, Call_C4F4D4_M1X1 }, 0 },  /* Call_C4F4D4 */
    { 0xC4F4D8u, { NULL, NULL, NULL, Call_C4F4D8_M1X1 }, 0 },  /* Call_C4F4D8 */
    { 0xC4F4E0u, { NULL, NULL, NULL, Call_C4F4E0_M1X1 }, 0 },  /* Call_C4F4E0 */
    { 0xC4F4E4u, { NULL, NULL, NULL, Call_C4F4E4_M1X1 }, 0 },  /* Call_C4F4E4 */
    { 0xC4F4EEu, { NULL, NULL, NULL, Call_C4F4EE_M1X1 }, 0 },  /* Call_C4F4EE */
    { 0xC4F501u, { NULL, NULL, NULL, bank_C4_F501_M1X1 }, 0 },  /* bank_C4_F501 */
    { 0xC4F53Eu, { NULL, NULL, NULL, Call_C4F53E_M1X1 }, 0 },  /* Call_C4F53E */
    { 0xC4F542u, { NULL, NULL, NULL, Call_C4F542_M1X1 }, 0 },  /* Call_C4F542 */
    { 0xC4F559u, { NULL, NULL, NULL, Call_C4F559_M1X1 }, 0 },  /* Call_C4F559 */
    { 0xC4F572u, { NULL, NULL, NULL, Call_C4F572_M1X1 }, 0 },  /* Call_C4F572 */
    { 0xC4F584u, { NULL, NULL, NULL, Call_C4F584_M1X1 }, 0 },  /* Call_C4F584 */
    { 0xC4F58Bu, { NULL, NULL, NULL, Call_C4F58B_M1X1 }, 0 },  /* Call_C4F58B */
    { 0xC4F59Fu, { NULL, NULL, NULL, Call_C4F59F_M1X1 }, 0 },  /* Call_C4F59F */
    { 0xC4F673u, { NULL, NULL, NULL, Call_C4F673_M1X1 }, 0 },  /* Call_C4F673 */
    { 0xC4F920u, { NULL, NULL, NULL, Call_C4F920_M1X1 }, 0 },  /* Call_C4F920 */
    { 0xC4F932u, { NULL, NULL, NULL, Call_C4F932_M1X1 }, 0 },  /* Call_C4F932 */
    { 0xC4F94Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C4F94B */
    { 0xC4F94Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C4F94F */
    { 0xC5035Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C5035D */
    { 0xC503AAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C503AA */
    { 0xC60000u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60000 */
    { 0xC60001u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60001 */
    { 0xC60009u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60009 */
    { 0xC6001Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6001A */
    { 0xC60020u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60020 */
    { 0xC60022u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60022 */
    { 0xC60064u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60064 */
    { 0xC60075u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60075 */
    { 0xC60086u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60086 */
    { 0xC60099u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60099 */
    { 0xC6009Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6009D */
    { 0xC6009Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6009E */
    { 0xC6009Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6009F */
    { 0xC600A0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600A0 */
    { 0xC600A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600A5 */
    { 0xC600A6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600A6 */
    { 0xC600A7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600A7 */
    { 0xC600A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600A9 */
    { 0xC600B7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600B7 */
    { 0xC600B9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600B9 */
    { 0xC600BDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600BD */
    { 0xC600BFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600BF */
    { 0xC600C6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600C6 */
    { 0xC600D4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600D4 */
    { 0xC600D6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600D6 */
    { 0xC600E0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600E0 */
    { 0xC600E6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C600E6 */
    { 0xC60100u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60100 */
    { 0xC60101u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60101 */
    { 0xC60127u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60127 */
    { 0xC6018Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6018D */
    { 0xC6019Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6019D */
    { 0xC6019Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6019E */
    { 0xC6019Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6019F */
    { 0xC601A2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C601A2 */
    { 0xC601A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C601A9 */
    { 0xC601B9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C601B9 */
    { 0xC601BDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C601BD */
    { 0xC60264u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60264 */
    { 0xC60285u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60285 */
    { 0xC6029Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6029D */
    { 0xC602A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C602A9 */
    { 0xC602ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C602AD */
    { 0xC602B6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C602B6 */
    { 0xC602B9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C602B9 */
    { 0xC602BDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C602BD */
    { 0xC602C6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C602C6 */
    { 0xC602CAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C602CA */
    { 0xC602E6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C602E6 */
    { 0xC60300u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60300 */
    { 0xC60301u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60301 */
    { 0xC60302u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60302 */
    { 0xC60329u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60329 */
    { 0xC60330u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60330 */
    { 0xC60336u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60336 */
    { 0xC603A2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C603A2 */
    { 0xC603A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C603A9 */
    { 0xC603B9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C603B9 */
    { 0xC603BDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C603BD */
    { 0xC603BFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C603BF */
    { 0xC603C6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C603C6 */
    { 0xC603D0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C603D0 */
    { 0xC603E6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C603E6 */
    { 0xC603F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C603F0 */
    { 0xC60400u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60400 */
    { 0xC60410u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60410 */
    { 0xC60464u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60464 */
    { 0xC6047Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6047F */
    { 0xC606C6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C606C6 */
    { 0xC606D0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C606D0 */
    { 0xC606E6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C606E6 */
    { 0xC606F8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C606F8 */
    { 0xC60701u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60701 */
    { 0xC60704u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60704 */
    { 0xC60730u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60730 */
    { 0xC6079Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6079E */
    { 0xC607A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C607A5 */
    { 0xC607B9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C607B9 */
    { 0xC607D0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C607D0 */
    { 0xC607F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C607F0 */
    { 0xC60800u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60800 */
    { 0xC60805u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60805 */
    { 0xC60886u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60886 */
    { 0xC60899u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60899 */
    { 0xC608A2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C608A2 */
    { 0xC608A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C608A5 */
    { 0xC608A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C608A9 */
    { 0xC608B7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C608B7 */
    { 0xC608BDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C608BD */
    { 0xC608D0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C608D0 */
    { 0xC60900u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60900 */
    { 0xC60911u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60911 */
    { 0xC60978u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60978 */
    { 0xC609C9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C609C9 */
    { 0xC609F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C609F0 */
    { 0xC609FCu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C609FC */
    { 0xC60A00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60A00 */
    { 0xC60A0Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60A0A */
    { 0xC60A75u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60A75 */
    { 0xC60AA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60AA9 */
    { 0xC60AB1u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60AB1 */
    { 0xC60AB9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60AB9 */
    { 0xC60AD6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60AD6 */
    { 0xC60AF0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60AF0 */
    { 0xC60B07u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60B07 */
    { 0xC60B0Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60B0A */
    { 0xC60B10u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60B10 */
    { 0xC60B60u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60B60 */
    { 0xC60B61u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60B61 */
    { 0xC60BB0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60BB0 */
    { 0xC60C29u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60C29 */
    { 0xC60CA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60CA9 */
    { 0xC60D41u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60D41 */
    { 0xC60DA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60DA9 */
    { 0xC60DBFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60DBF */
    { 0xC60DC9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60DC9 */
    { 0xC60DD0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60DD0 */
    { 0xC60DF8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60DF8 */
    { 0xC60E00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60E00 */
    { 0xC60E01u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60E01 */
    { 0xC60E10u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60E10 */
    { 0xC60E90u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60E90 */
    { 0xC60E9Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60E9D */
    { 0xC60EBDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60EBD */
    { 0xC60EC6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60EC6 */
    { 0xC60EEFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60EEF */
    { 0xC60F00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60F00 */
    { 0xC60FA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60FA9 */
    { 0xC60FB9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C60FB9 */
    { 0xC61000u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61000 */
    { 0xC61001u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61001 */
    { 0xC6102Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6102E */
    { 0xC61072u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61072 */
    { 0xC61085u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61085 */
    { 0xC6109Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6109D */
    { 0xC610B1u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C610B1 */
    { 0xC610D0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C610D0 */
    { 0xC610F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C610F0 */
    { 0xC61105u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61105 */
    { 0xC61164u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61164 */
    { 0xC611A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C611A5 */
    { 0xC611A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C611A9 */
    { 0xC611B0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C611B0 */
    { 0xC611F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C611F0 */
    { 0xC61280u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61280 */
    { 0xC612CDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C612CD */
    { 0xC612FFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C612FF */
    { 0xC61300u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61300 */
    { 0xC6166Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6166E */
    { 0xC6168Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6168D */
    { 0xC6169Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6169D */
    { 0xC616A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C616A5 */
    { 0xC616AFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C616AF */
    { 0xC616B2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C616B2 */
    { 0xC616B9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C616B9 */
    { 0xC616CDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C616CD */
    { 0xC616F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C616F0 */
    { 0xC61710u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61710 */
    { 0xC6178Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6178F */
    { 0xC617A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C617A5 */
    { 0xC617B0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C617B0 */
    { 0xC617DEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C617DE */
    { 0xC617FEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C617FE */
    { 0xC61800u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61800 */
    { 0xC61801u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61801 */
    { 0xC6180Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6180A */
    { 0xC61868u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61868 */
    { 0xC6187Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6187A */
    { 0xC61880u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61880 */
    { 0xC61885u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61885 */
    { 0xC6188Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6188A */
    { 0xC61890u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61890 */
    { 0xC61898u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61898 */
    { 0xC6189Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6189D */
    { 0xC6189Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6189E */
    { 0xC618CDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C618CD */
    { 0xC618D1u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C618D1 */
    { 0xC618FAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C618FA */
    { 0xC619D4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C619D4 */
    { 0xC619EFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C619EF */
    { 0xC619F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C619F0 */
    { 0xC61A00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61A00 */
    { 0xC61A1Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61A1A */
    { 0xC61A20u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61A20 */
    { 0xC61AADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61AAD */
    { 0xC61ABDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61ABD */
    { 0xC61B1Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61B1C */
    { 0xC61B96u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61B96 */
    { 0xC61C00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61C00 */
    { 0xC61C0Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61C0A */
    { 0xC61C66u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61C66 */
    { 0xC61C75u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61C75 */
    { 0xC61C9Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61C9D */
    { 0xC61C9Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61C9E */
    { 0xC61CA7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61CA7 */
    { 0xC61CDEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C61CDE */
    { 0xC62085u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C62085 */
    { 0xC62093u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C62093 */
    { 0xC620A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C620A5 */
    { 0xC620A6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C620A6 */
    { 0xC620A7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C620A7 */
    { 0xC620A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C620A9 */
    { 0xC620B0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C620B0 */
    { 0xC620C0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C620C0 */
    { 0xC620C2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C620C2 */
    { 0xC620C6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C620C6 */
    { 0xC620D5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C620D5 */
    { 0xC62133u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C62133 */
    { 0xC62D45u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C62D45 */
    { 0xC62DAEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C62DAE */
    { 0xC62DCDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C62DCD */
    { 0xC631EEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C631EE */
    { 0xC631FAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C631FA */
    { 0xC6329Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6329E */
    { 0xC64002u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64002 */
    { 0xC640F1u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C640F1 */
    { 0xC6418Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6418D */
    { 0xC641F3u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C641F3 */
    { 0xC642A4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C642A4 */
    { 0xC6432Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6432D */
    { 0xC644F1u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C644F1 */
    { 0xC64500u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64500 */
    { 0xC64515u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64515 */
    { 0xC646A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C646A9 */
    { 0xC646BEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C646BE */
    { 0xC64A9Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64A9B */
    { 0xC64A9Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64A9F */
    { 0xC64B00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64B00 */
    { 0xC64B77u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64B77 */
    { 0xC64B91u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64B91 */
    { 0xC64C32u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64C32 */
    { 0xC64C36u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64C36 */
    { 0xC64C38u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64C38 */
    { 0xC64CA4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64CA4 */
    { 0xC64CBBu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64CBB */
    { 0xC64DCBu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64DCB */
    { 0xC64ECEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64ECE */
    { 0xC64ED3u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64ED3 */
    { 0xC64F00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C64F00 */
    { 0xC65168u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C65168 */
    { 0xC652D7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C652D7 */
    { 0xC6535Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6535B */
    { 0xC65557u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C65557 */
    { 0xC6557Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6557F */
    { 0xC655BFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C655BF */
    { 0xC65600u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C65600 */
    { 0xC656DCu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C656DC */
    { 0xC656DEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C656DE */
    { 0xC657F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C657F0 */
    { 0xC6E280u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6E280 */
    { 0xC6E295u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6E295 */
    { 0xC6E2B9u, { NULL, NULL, NULL, Call_C6E2B9_M1X1 }, 0 },  /* Call_C6E2B9 */
    { 0xC6F6F9u, { NULL, NULL, NULL, Call_C6F6F9_M1X1 }, 0 },  /* Call_C6F6F9 */
    { 0xC6F700u, { NULL, NULL, NULL, Call_C6F700_M1X1 }, 0 },  /* Call_C6F700 */
    { 0xC6F77Fu, { NULL, NULL, NULL, Call_C6F77F_M1X1 }, 0 },  /* Call_C6F77F */
    { 0xC6F7B0u, { NULL, NULL, NULL, Call_C6F7B0_M1X1 }, 0 },  /* Call_C6F7B0 */
    { 0xC6F7D1u, { NULL, NULL, NULL, Call_C6F7D1_M1X1 }, 0 },  /* Call_C6F7D1 */
    { 0xC6F800u, { NULL, NULL, NULL, Call_C6F800_M1X1 }, 0 },  /* Call_C6F800 */
    { 0xC6F801u, { NULL, NULL, NULL, Call_C6F801_M1X1 }, 0 },  /* Call_C6F801 */
    { 0xC6F83Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C6F83A */
    { 0xC6F83Eu, { NULL, NULL, NULL, Call_C6F83E_M1X1 }, 0 },  /* Call_C6F83E */
    { 0xC703C8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C703C8 */
    { 0xC70400u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C70400 */
    { 0xC7041Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C7041F */
    { 0xC7044Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C7044A */
    { 0xC808A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C808A9 */
    { 0xC808B7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C808B7 */
    { 0xC808D9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C808D9 */
    { 0xC808F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C808F0 */
    { 0xC80922u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80922 */
    { 0xC809C3u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C809C3 */
    { 0xC809DBu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C809DB */
    { 0xC809DFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C809DF */
    { 0xC80AA5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80AA5 */
    { 0xC80AA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80AA9 */
    { 0xC80AADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80AAD */
    { 0xC80AD8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80AD8 */
    { 0xC80ADBu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80ADB */
    { 0xC80B00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80B00 */
    { 0xC80C00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80C00 */
    { 0xC80C3Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80C3C */
    { 0xC80CD8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80CD8 */
    { 0xC80CDAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80CDA */
    { 0xC80CDBu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80CDB */
    { 0xC80CDDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80CDD */
    { 0xC80D00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80D00 */
    { 0xC80DA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80DA9 */
    { 0xC80F4Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80F4D */
    { 0xC80F51u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80F51 */
    { 0xC80F62u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80F62 */
    { 0xC80F66u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80F66 */
    { 0xC80F77u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80F77 */
    { 0xC80F7Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80F7B */
    { 0xC80F8Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80F8C */
    { 0xC80F99u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80F99 */
    { 0xC80FA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80FA9 */
    { 0xC80FADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80FAD */
    { 0xC80FC9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80FC9 */
    { 0xC80FCEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80FCE */
    { 0xC80FD8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C80FD8 */
    { 0xC81000u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C81000 */
    { 0xC81001u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C81001 */
    { 0xC8139Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8139D */
    { 0xC8139Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8139F */
    { 0xC813ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C813AD */
    { 0xC814A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C814A9 */
    { 0xC814D8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C814D8 */
    { 0xC814D9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C814D9 */
    { 0xC82095u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C82095 */
    { 0xC820A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C820A5 */
    { 0xC820A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C820A9 */
    { 0xC820AEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C820AE */
    { 0xC82923u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C82923 */
    { 0xC82A2Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C82A2E */
    { 0xC82A78u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C82A78 */
    { 0xC875CFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C875CF */
    { 0xC87600u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C87600 */
    { 0xC8CF86u, { NULL, NULL, NULL, NULL }, 0 },  /* bank_C8_CF86 */
    { 0xC8F407u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F407 */
    { 0xC8F41Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F41D */
    { 0xC8F4B7u, { NULL, NULL, NULL, Call_C8F4B7_M1X1 }, 0 },  /* Call_C8F4B7 */
    { 0xC8F4D0u, { NULL, NULL, NULL, Call_C8F4D0_M1X1 }, 0 },  /* Call_C8F4D0 */
    { 0xC8F4E9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F4E9 */
    { 0xC8F500u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F500 */
    { 0xC8F51Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F51D */
    { 0xC8F563u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F563 */
    { 0xC8F5A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F5A9 */
    { 0xC8F5EFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F5EF */
    { 0xC8F622u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F622 */
    { 0xC8F800u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F800 */
    { 0xC8F801u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F801 */
    { 0xC8F820u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F820 */
    { 0xC8F89Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F89F */
    { 0xC8F8DAu, { NULL, NULL, NULL, Call_C8F8DA_M1X1 }, 0 },  /* Call_C8F8DA */
    { 0xC8F8EBu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F8EB */
    { 0xC8F94Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F94C */
    { 0xC8F966u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8F966 */
    { 0xC8FA00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8FA00 */
    { 0xC8FA0Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8FA0B */
    { 0xC8FA7Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_C8FA7A */
    { 0xC9916Du, { NULL, NULL, NULL, NULL }, 0 },  /* bank_C9_916D */
    { 0xC9E4DCu, { NULL, NULL, NULL, LayoutTableIndexA_M1X1 }, 0 },  /* LayoutTableIndexA */
    { 0xC9E57Bu, { NULL, NULL, NULL, LayoutTableIndexB_M1X1 }, 0 },  /* LayoutTableIndexB */
    { 0xCA0B5Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0B5F */
    { 0xCA0B8Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0B8F */
    { 0xCA0BA2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0BA2 */
    { 0xCA0BA7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0BA7 */
    { 0xCA0BA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0BA9 */
    { 0xCA0BB9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0BB9 */
    { 0xCA0BBFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0BBF */
    { 0xCA0BF0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0BF0 */
    { 0xCA0BFFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0BFF */
    { 0xCA0C00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0C00 */
    { 0xCA0C07u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0C07 */
    { 0xCA0C20u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0C20 */
    { 0xCA0C44u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0C44 */
    { 0xCA0C80u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0C80 */
    { 0xCA0C84u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA0C84 */
    { 0xCA19F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA19F0 */
    { 0xCA1AA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA1AA9 */
    { 0xCA1AADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA1AAD */
    { 0xCA1AB9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA1AB9 */
    { 0xCA1ABFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA1ABF */
    { 0xCA1AF0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA1AF0 */
    { 0xCA2420u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2420 */
    { 0xCA2424u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2424 */
    { 0xCA2464u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2464 */
    { 0xCA2466u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2466 */
    { 0xCA2485u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2485 */
    { 0xCA248Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA248A */
    { 0xCA248Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA248D */
    { 0xCA2497u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2497 */
    { 0xCA24A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA24A5 */
    { 0xCA24A6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA24A6 */
    { 0xCA24ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA24AD */
    { 0xCA24EEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA24EE */
    { 0xCA24F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA24F0 */
    { 0xCA2564u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2564 */
    { 0xCA25BFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA25BF */
    { 0xCA25F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA25F0 */
    { 0xCA2618u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2618 */
    { 0xCA2620u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2620 */
    { 0xCA262Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA262D */
    { 0xCA264Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA264A */
    { 0xCA2657u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2657 */
    { 0xCA2A55u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2A55 */
    { 0xCA2A70u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2A70 */
    { 0xCA2A77u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2A77 */
    { 0xCA2A85u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2A85 */
    { 0xCA2A96u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2A96 */
    { 0xCA2AA5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2AA5 */
    { 0xCA2AA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2AA9 */
    { 0xCA2AAFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA2AAF */
    { 0xCA4800u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4800 */
    { 0xCA4810u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4810 */
    { 0xCA481Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA481A */
    { 0xCA4834u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4834 */
    { 0xCA487Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA487B */
    { 0xCA488Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA488B */
    { 0xCA48A2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA48A2 */
    { 0xCA48A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA48A9 */
    { 0xCA48ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA48AD */
    { 0xCA4A18u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4A18 */
    { 0xCA4A1Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4A1A */
    { 0xCA4A2Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4A2B */
    { 0xCA4A37u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4A37 */
    { 0xCA4A43u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4A43 */
    { 0xCA4A4Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4A4A */
    { 0xCA4A63u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4A63 */
    { 0xCA4A75u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4A75 */
    { 0xCA4A8Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4A8F */
    { 0xCA4AABu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4AAB */
    { 0xCA4AE6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4AE6 */
    { 0xCA4AF0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4AF0 */
    { 0xCA4B20u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4B20 */
    { 0xCA4B24u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4B24 */
    { 0xCA4B79u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4B79 */
    { 0xCA4B85u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4B85 */
    { 0xCA4B8Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4B8B */
    { 0xCA4BC1u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4BC1 */
    { 0xCA4BDCu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4BDC */
    { 0xCA4BF7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4BF7 */
    { 0xCA4BFDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4BFD */
    { 0xCA4C03u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4C03 */
    { 0xCA4C12u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4C12 */
    { 0xCA4C17u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4C17 */
    { 0xCA4C1Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4C1C */
    { 0xCA4C21u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4C21 */
    { 0xCA4C26u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4C26 */
    { 0xCA4C2Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4C2B */
    { 0xCA4C40u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4C40 */
    { 0xCA4C4Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4C4E */
    { 0xCA4C77u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4C77 */
    { 0xCA4C78u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4C78 */
    { 0xCA4CA7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4CA7 */
    { 0xCA4CADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4CAD */
    { 0xCA4CB0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4CB0 */
    { 0xCA4CCAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4CCA */
    { 0xCA4D32u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4D32 */
    { 0xCA4D3Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4D3A */
    { 0xCA4D5Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4D5D */
    { 0xCA4D67u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4D67 */
    { 0xCA4DBFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4DBF */
    { 0xCA4DDCu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4DDC */
    { 0xCA4E6Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4E6D */
    { 0xCA4E7Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4E7D */
    { 0xCA4EA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4EA9 */
    { 0xCA4EBDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4EBD */
    { 0xCA4EBFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4EBF */
    { 0xCA4EF0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4EF0 */
    { 0xCA4EF7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4EF7 */
    { 0xCA4F2Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4F2C */
    { 0xCA4FD0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4FD0 */
    { 0xCA4FD6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4FD6 */
    { 0xCA4FF0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4FF0 */
    { 0xCA4FFAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4FFA */
    { 0xCA4FFCu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA4FFC */
    { 0xCA5000u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5000 */
    { 0xCA5004u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5004 */
    { 0xCA5018u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5018 */
    { 0xCA5025u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5025 */
    { 0xCA5032u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5032 */
    { 0xCA503Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA503F */
    { 0xCA50A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA50A9 */
    { 0xCA50BFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA50BF */
    { 0xCA5120u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5120 */
    { 0xCA5155u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5155 */
    { 0xCA52E1u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA52E1 */
    { 0xCA52ECu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA52EC */
    { 0xCA5320u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5320 */
    { 0xCA5357u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5357 */
    { 0xCA536Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA536F */
    { 0xCA53E6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA53E6 */
    { 0xCA53F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA53F0 */
    { 0xCA541Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA541B */
    { 0xCA5420u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5420 */
    { 0xCA5456u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5456 */
    { 0xCA547Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA547A */
    { 0xCA5496u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5496 */
    { 0xCA54A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA54A9 */
    { 0xCA54BFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA54BF */
    { 0xCA550Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA550A */
    { 0xCA5520u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5520 */
    { 0xCA5523u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5523 */
    { 0xCA552Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA552D */
    { 0xCA5539u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5539 */
    { 0xCA5591u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5591 */
    { 0xCA55BFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA55BF */
    { 0xCA562Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA562E */
    { 0xCA5674u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5674 */
    { 0xCA5677u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5677 */
    { 0xCA567Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA567A */
    { 0xCA5680u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5680 */
    { 0xCA5683u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5683 */
    { 0xCA569Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA569E */
    { 0xCA56A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA56A9 */
    { 0xCA56B9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA56B9 */
    { 0xCA56BFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA56BF */
    { 0xCA56D4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA56D4 */
    { 0xCA56F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA56F0 */
    { 0xCA56F7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA56F7 */
    { 0xCA5712u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5712 */
    { 0xCA5783u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5783 */
    { 0xCA5794u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5794 */
    { 0xCA57AFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA57AF */
    { 0xCA57EEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA57EE */
    { 0xCA581Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA581D */
    { 0xCA58AEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA58AE */
    { 0xCA58B9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA58B9 */
    { 0xCA58CEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA58CE */
    { 0xCA58F2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA58F2 */
    { 0xCA590Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA590A */
    { 0xCA5920u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5920 */
    { 0xCA5943u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5943 */
    { 0xCA5955u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5955 */
    { 0xCA5978u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5978 */
    { 0xCA5983u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5983 */
    { 0xCA59C0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA59C0 */
    { 0xCA59CDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA59CD */
    { 0xCA5A18u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5A18 */
    { 0xCA5A48u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5A48 */
    { 0xCA5AC5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5AC5 */
    { 0xCA5ACFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5ACF */
    { 0xCA5ADAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5ADA */
    { 0xCA5AEFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5AEF */
    { 0xCA5B15u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5B15 */
    { 0xCA5B20u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5B20 */
    { 0xCA5B6Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5B6F */
    { 0xCA5C4Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5C4B */
    { 0xCA5C5Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5C5E */
    { 0xCA5C6Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5C6B */
    { 0xCA5C6Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5C6F */
    { 0xCA5C80u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5C80 */
    { 0xCA5C87u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5C87 */
    { 0xCA5C9Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5C9A */
    { 0xCA5CA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5CA9 */
    { 0xCA5CC6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5CC6 */
    { 0xCA5CE8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5CE8 */
    { 0xCA5CF0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5CF0 */
    { 0xCA5D20u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5D20 */
    { 0xCA5D2Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5D2E */
    { 0xCA5DB1u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5DB1 */
    { 0xCA5DCEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5DCE */
    { 0xCA5DEAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5DEA */
    { 0xCA5DFEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5DFE */
    { 0xCA5E10u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5E10 */
    { 0xCA5E20u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5E20 */
    { 0xCA5E3Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5E3E */
    { 0xCA5E46u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5E46 */
    { 0xCA5E4Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5E4F */
    { 0xCA5ED1u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5ED1 */
    { 0xCA5F2Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5F2D */
    { 0xCA5F34u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5F34 */
    { 0xCA5FA6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA5FA6 */
    { 0xCA6006u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6006 */
    { 0xCA601Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA601E */
    { 0xCA6028u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6028 */
    { 0xCA605Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA605D */
    { 0xCA6060u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6060 */
    { 0xCA60A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA60A9 */
    { 0xCA60BBu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA60BB */
    { 0xCA60C0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA60C0 */
    { 0xCA60DAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA60DA */
    { 0xCA60F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA60F0 */
    { 0xCA60F9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA60F9 */
    { 0xCA60FAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA60FA */
    { 0xCA6120u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6120 */
    { 0xCA6167u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6167 */
    { 0xCA6172u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6172 */
    { 0xCA6183u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6183 */
    { 0xCA619Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA619C */
    { 0xCA61ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA61AD */
    { 0xCA61C0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA61C0 */
    { 0xCA61D1u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA61D1 */
    { 0xCA61E2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA61E2 */
    { 0xCA61F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA61F0 */
    { 0xCA6328u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6328 */
    { 0xCA638Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA638E */
    { 0xCA63AEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA63AE */
    { 0xCA6400u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6400 */
    { 0xCA6420u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6420 */
    { 0xCA64A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA64A9 */
    { 0xCA64BEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA64BE */
    { 0xCA650Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA650A */
    { 0xCA6518u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6518 */
    { 0xCA65ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA65AD */
    { 0xCA6720u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6720 */
    { 0xCA679Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA679C */
    { 0xCA67A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA67A9 */
    { 0xCA67ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA67AD */
    { 0xCA688Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA688B */
    { 0xCA68A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA68A9 */
    { 0xCA68ABu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA68AB */
    { 0xCA68EDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA68ED */
    { 0xCA6918u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6918 */
    { 0xCA6920u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6920 */
    { 0xCA6BC9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6BC9 */
    { 0xCA6BCDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6BCD */
    { 0xCA6BF0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6BF0 */
    { 0xCA6C8Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6C8E */
    { 0xCA6CA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6CA9 */
    { 0xCA6CADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6CAD */
    { 0xCA6CBFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6CBF */
    { 0xCA6CFBu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6CFB */
    { 0xCA6D0Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6D0F */
    { 0xCA6D18u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6D18 */
    { 0xCA6D5Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6D5F */
    { 0xCA6DA7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6DA7 */
    { 0xCA6DACu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6DAC */
    { 0xCA6DBAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6DBA */
    { 0xCA6DBFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA6DBF */
    { 0xCA8898u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA8898 */
    { 0xCA88A9u, { NULL, NULL, NULL, Call_CA88A9_M1X1 }, 0 },  /* Call_CA88A9 */
    { 0xCA88E8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA88E8 */
    { 0xCA8916u, { NULL, NULL, NULL, Call_CA8916_M1X1 }, 0 },  /* Call_CA8916 */
    { 0xCA8E37u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA8E37 */
    { 0xCA8E60u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA8E60 */
    { 0xCA8E7Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA8E7F */
    { 0xCA8E8Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA8E8D */
    { 0xCA8EADu, { NULL, NULL, NULL, Call_CA8EAD_M1X1 }, 0 },  /* Call_CA8EAD */
    { 0xCA8EB3u, { NULL, NULL, NULL, Call_CA8EB3_M1X1 }, 0 },  /* Call_CA8EB3 */
    { 0xCA8EF3u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CA8EF3 */
    { 0xCAA588u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA588 */
    { 0xCAA59Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA59C */
    { 0xCAA5C3u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA5C3 */
    { 0xCAA5DAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA5DA */
    { 0xCAA5E3u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA5E3 */
    { 0xCAA5E4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA5E4 */
    { 0xCAA60Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA60A */
    { 0xCAA613u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA613 */
    { 0xCAA61Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA61C */
    { 0xCAA941u, { NULL, NULL, NULL, Call_CAA941_M1X1 }, 0 },  /* Call_CAA941 */
    { 0xCAA943u, { NULL, NULL, NULL, Call_CAA943_M1X1 }, 0 },  /* Call_CAA943 */
    { 0xCAA959u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA959 */
    { 0xCAA960u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA960 */
    { 0xCAA969u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA969 */
    { 0xCAA983u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA983 */
    { 0xCAA98Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA98B */
    { 0xCAA9EBu, { NULL, NULL, NULL, Call_CAA9EB_M1X1 }, 0 },  /* Call_CAA9EB */
    { 0xCAA9FFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAA9FF */
    { 0xCAAA00u, { NULL, NULL, NULL, Call_CAAA00_M1X1 }, 0 },  /* Call_CAAA00 */
    { 0xCAAA30u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAAA30 */
    { 0xCAAD23u, { NULL, NULL, NULL, Call_CAAD23_M1X1 }, 0 },  /* Call_CAAD23 */
    { 0xCAAD2Au, { NULL, NULL, NULL, Call_CAAD2A_M1X1 }, 0 },  /* Call_CAAD2A */
    { 0xCAAD31u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAAD31 */
    { 0xCAAD48u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAAD48 */
    { 0xCAB3D6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB3D6 */
    { 0xCAB3DAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB3DA */
    { 0xCAB3FBu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB3FB */
    { 0xCAB40Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB40D */
    { 0xCAB420u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB420 */
    { 0xCAB439u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB439 */
    { 0xCAB48Du, { NULL, NULL, NULL, Call_CAB48D_M1X1 }, 0 },  /* Call_CAB48D */
    { 0xCAB49Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB49F */
    { 0xCAB520u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB520 */
    { 0xCAB534u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB534 */
    { 0xCAB555u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB555 */
    { 0xCAB6A7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB6A7 */
    { 0xCAB6BFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB6BF */
    { 0xCAB6E5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB6E5 */
    { 0xCAB6F2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB6F2 */
    { 0xCAB913u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB913 */
    { 0xCAB921u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAB921 */
    { 0xCAB9A1u, { NULL, NULL, NULL, Call_CAB9A1_M1X1 }, 0 },  /* Call_CAB9A1 */
    { 0xCABA16u, { NULL, NULL, NULL, Call_CABA16_M1X1 }, 0 },  /* Call_CABA16 */
    { 0xCABA1Bu, { NULL, NULL, NULL, Call_CABA1B_M1X1 }, 0 },  /* Call_CABA1B */
    { 0xCABA20u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABA20 */
    { 0xCABA64u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABA64 */
    { 0xCABA85u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABA85 */
    { 0xCABAFDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABAFD */
    { 0xCABB02u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABB02 */
    { 0xCABB07u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABB07 */
    { 0xCABB14u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABB14 */
    { 0xCABB19u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABB19 */
    { 0xCABB7Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABB7A */
    { 0xCABB9Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABB9E */
    { 0xCABBCFu, { NULL, NULL, NULL, Call_CABBCF_M1X1 }, 0 },  /* Call_CABBCF */
    { 0xCABBDBu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABBDB */
    { 0xCABC2Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABC2E */
    { 0xCABC3Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABC3A */
    { 0xCABC7Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABC7A */
    { 0xCABC8Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABC8D */
    { 0xCABCA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABCA9 */
    { 0xCABCADu, { NULL, NULL, NULL, Call_CABCAD_M1X1 }, 0 },  /* Call_CABCAD */
    { 0xCABD20u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABD20 */
    { 0xCABD37u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CABD37 */
    { 0xCAC020u, { NULL, NULL, NULL, NULL }, 0 },  /* bank_CA_C020 */
    { 0xCAC0C3u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC0C3 */
    { 0xCAC0CAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC0CA */
    { 0xCAC0F1u, { NULL, NULL, NULL, Call_CAC0F1_M1X1 }, 0 },  /* Call_CAC0F1 */
    { 0xCAC120u, { NULL, NULL, NULL, Call_CAC120_M1X1 }, 0 },  /* Call_CAC120 */
    { 0xCAC13Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC13C */
    { 0xCAC355u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC355 */
    { 0xCAC38Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC38A */
    { 0xCAC5E2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC5E2 */
    { 0xCAC5EAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC5EA */
    { 0xCAC620u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC620 */
    { 0xCAC640u, { NULL, NULL, NULL, Call_CAC640_M1X1 }, 0 },  /* Call_CAC640 */
    { 0xCAC65Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC65E */
    { 0xCAC686u, { NULL, NULL, NULL, Call_CAC686_M1X1 }, 0 },  /* Call_CAC686 */
    { 0xCAC6A8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC6A8 */
    { 0xCAC6A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC6A9 */
    { 0xCAC6C0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC6C0 */
    { 0xCAC6F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC6F0 */
    { 0xCAC720u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAC720 */
    { 0xCAD369u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAD369 */
    { 0xCAD382u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAD382 */
    { 0xCAD38Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAD38D */
    { 0xCAD3ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAD3AD */
    { 0xCAD3B7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAD3B7 */
    { 0xCAD3BBu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAD3BB */
    { 0xCAD3CCu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAD3CC */
    { 0xCAD3D0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAD3D0 */
    { 0xCAD3ECu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAD3EC */
    { 0xCAD3F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAD3F0 */
    { 0xCAD40Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAD40C */
    { 0xCAD410u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CAD410 */
    { 0xCB058Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB058A */
    { 0xCB058Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB058E */
    { 0xCB05A2u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB05A2 */
    { 0xCB05A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB05A5 */
    { 0xCB05A6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB05A6 */
    { 0xCB05E4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB05E4 */
    { 0xCB05E8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB05E8 */
    { 0xCB0600u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB0600 */
    { 0xCB0648u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB0648 */
    { 0xCB07D3u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB07D3 */
    { 0xCB07D7u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB07D7 */
    { 0xCB07D8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB07D8 */
    { 0xCB07DAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB07DA */
    { 0xCB0800u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB0800 */
    { 0xCB0801u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB0801 */
    { 0xCB0804u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB0804 */
    { 0xCB0818u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB0818 */
    { 0xCB081Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB081C */
    { 0xCB089Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB089C */
    { 0xCB08D9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB08D9 */
    { 0xCB0900u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB0900 */
    { 0xCB0923u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB0923 */
    { 0xCB0947u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB0947 */
    { 0xCB0977u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB0977 */
    { 0xCB097Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB097B */
    { 0xCB09A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CB09A9 */
    { 0xCBFDFDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CBFDFD */
    { 0xCBFE00u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CBFE00 */
    { 0xCC02A4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC02A4 */
    { 0xCC02A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC02A5 */
    { 0xCC02A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC02A9 */
    { 0xCC02B9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC02B9 */
    { 0xCC02BDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC02BD */
    { 0xCC02C6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC02C6 */
    { 0xCC0330u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0330 */
    { 0xCC0388u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0388 */
    { 0xCC0389u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0389 */
    { 0xCC038Au, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC038A */
    { 0xCC038Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC038B */
    { 0xCC039Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC039C */
    { 0xCC03A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC03A9 */
    { 0xCC03AEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC03AE */
    { 0xCC03BFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC03BF */
    { 0xCC03C9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC03C9 */
    { 0xCC03DEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC03DE */
    { 0xCC040Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC040C */
    { 0xCC0530u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0530 */
    { 0xCC0546u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0546 */
    { 0xCC0570u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0570 */
    { 0xCC0581u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0581 */
    { 0xCC059Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC059C */
    { 0xCC05A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC05A9 */
    { 0xCC05ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC05AD */
    { 0xCC05BFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC05BF */
    { 0xCC05D0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC05D0 */
    { 0xCC05DEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC05DE */
    { 0xCC0622u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0622 */
    { 0xCC06A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC06A5 */
    { 0xCC06A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC06A9 */
    { 0xCC06DEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC06DE */
    { 0xCC06F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC06F0 */
    { 0xCC06FEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC06FE */
    { 0xCC07A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC07A9 */
    { 0xCC07BDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC07BD */
    { 0xCC07D0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC07D0 */
    { 0xCC07F4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC07F4 */
    { 0xCC0800u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0800 */
    { 0xCC0860u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0860 */
    { 0xCC086Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC086B */
    { 0xCC08A5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC08A5 */
    { 0xCC08A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC08A9 */
    { 0xCC08ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC08AD */
    { 0xCC08B9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC08B9 */
    { 0xCC0924u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0924 */
    { 0xCC09A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC09A9 */
    { 0xCC09BDu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC09BD */
    { 0xCC0B9Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0B9C */
    { 0xCC0BA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0BA9 */
    { 0xCC0BAAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0BAA */
    { 0xCC0BADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0BAD */
    { 0xCC0C53u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0C53 */
    { 0xCC0C64u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0C64 */
    { 0xCC0C69u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0C69 */
    { 0xCC0C9Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0C9C */
    { 0xCC0CA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0CA9 */
    { 0xCC0D2Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0D2F */
    { 0xCC0DA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0DA9 */
    { 0xCC0E28u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0E28 */
    { 0xCC0E64u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0E64 */
    { 0xCC0EA4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0EA4 */
    { 0xCC0EA5u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0EA5 */
    { 0xCC0EA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0EA9 */
    { 0xCC0F21u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0F21 */
    { 0xCC0F4Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0F4E */
    { 0xCC0F80u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0F80 */
    { 0xCC0FA0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0FA0 */
    { 0xCC0FA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0FA9 */
    { 0xCC0FB4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC0FB4 */
    { 0xCC1083u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC1083 */
    { 0xCC10A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC10A9 */
    { 0xCC10D4u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC10D4 */
    { 0xCC11A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC11A9 */
    { 0xCC11B0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC11B0 */
    { 0xCC129Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC129E */
    { 0xCC12A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC12A9 */
    { 0xCC1330u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC1330 */
    { 0xCC1380u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC1380 */
    { 0xCC139Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC139F */
    { 0xCC13A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC13A9 */
    { 0xCC13ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC13AD */
    { 0xCC13EEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC13EE */
    { 0xCC144Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC144D */
    { 0xCC14A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC14A9 */
    { 0xCC14AFu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC14AF */
    { 0xCC152Bu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC152B */
    { 0xCC152Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC152C */
    { 0xCC1579u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC1579 */
    { 0xCC1580u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC1580 */
    { 0xCC15A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC15A9 */
    { 0xCC162Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC162C */
    { 0xCC168Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC168E */
    { 0xCC16A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC16A9 */
    { 0xCC16ADu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC16AD */
    { 0xCC16F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC16F0 */
    { 0xCC1715u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC1715 */
    { 0xCC238Fu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC238F */
    { 0xCC239Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC239C */
    { 0xCC23A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC23A9 */
    { 0xCC23BAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC23BA */
    { 0xCC24A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC24A9 */
    { 0xCC25A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC25A9 */
    { 0xCC269Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC269C */
    { 0xCC26A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC26A9 */
    { 0xCC26F0u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC26F0 */
    { 0xCC26F3u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC26F3 */
    { 0xCC279Cu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC279C */
    { 0xCC27A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC27A9 */
    { 0xCC2800u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC2800 */
    { 0xCC2878u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC2878 */
    { 0xCC2885u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC2885 */
    { 0xCC28A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC28A9 */
    { 0xCC28DCu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC28DC */
    { 0xCC28FAu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC28FA */
    { 0xCC2900u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC2900 */
    { 0xCC291Du, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC291D */
    { 0xCC2922u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC2922 */
    { 0xCC2943u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC2943 */
    { 0xCC299Eu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC299E */
    { 0xCC29A9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC29A9 */
    { 0xCC29C8u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC29C8 */
    { 0xCC29CCu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC29CC */
    { 0xCC29F3u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC29F3 */
    { 0xCC2AA9u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC2AA9 */
    { 0xCC2AAEu, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CC2AAE */
    { 0xCC805Du, { NULL, NULL, NULL, NULL }, 0 },  /* bank_CC_805D */
    { 0xCCB7EDu, { NULL, NULL, NULL, bank_CC_B7ED_M1X1 }, 0 },  /* bank_CC_B7ED */
    { 0xCCE580u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CCE580 */
    { 0xCCE584u, { NULL, NULL, NULL, Call_CCE584_M1X1 }, 0 },  /* Call_CCE584 */
    { 0xCCE595u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CCE595 */
    { 0xCCE5F6u, { NULL, NULL, NULL, NULL }, 0 },  /* Call_CCE5F6 */
    { 0xCEA9D8u, { NULL, NULL, NULL, bank_CE_A9D8_M1X1 }, 0 },  /* bank_CE_A9D8 */
};

const unsigned g_dispatch_table_count =
    (unsigned)(sizeof(g_dispatch_table) / sizeof(g_dispatch_table[0]));

const RamRoutineGuard g_ram_routine_guards[] = {
    { 0xFFFFFFFFu, 0u, 0u },
};

const unsigned g_ram_routine_guard_count =
    (unsigned)(sizeof(g_ram_routine_guards) / sizeof(g_ram_routine_guards[0]));
