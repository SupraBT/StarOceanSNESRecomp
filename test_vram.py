import struct

class SNES_PPU_Simulator:
    def __init__(self):
        self.vram = bytearray(0x10000)
        self.vmain = 0x00
        self.vmadd = 0x0000
        self.event_log = []

    def write_register(self, reg, value):
        if reg == 0x2115:
            self.vmain = value
            self.event_log.append(f"[REG WRITE] $2115 (VMAIN) = 0x{value:02X} (Increment Mode: {value & 0x03})")
        elif reg == 0x2116:
            self.vmadd = (self.vmadd & 0xFF00) | value
            self.event_log.append(f"[REG WRITE] $2116 (VMADD LSB) -> VMADD = 0x{self.vmadd:04X} Word Addr")
        elif reg == 0x2117:
            self.vmadd = (self.vmadd & 0x00FF) | (value << 8)
            self.event_log.append(f"[REG WRITE] $2117 (VMADD MSB) -> VMADD = 0x{self.vmadd:04X} Word Addr (Byte Addr: 0x{self.vmadd*2:04X})")

    def execute_sdd1_dma(self, decompressed_data, bAdr=0x18):
        self.event_log.append(f"\n--- INICIANDO TRANSFERENCIA DMA (Tamaño: {len(decompressed_data)} bytes, Target: $bAdr={bAdr:02X}) ---")
        if bAdr != 0x18:
            self.event_log.append(f"[ERROR DMA] El destino $bAdr={bAdr:02X} no es VRAM ($18). Transferencia cancelada.")
            return

        inc_mode = self.vmain & 0x03
        increment_step = 1 if inc_mode == 0 else (32 if inc_mode == 1 else 128)

        bytes_written = 0
        for i in range(0, len(decompressed_data), 2):
            if bytes_written >= len(decompressed_data):
                break
            byte_low = decompressed_data[i]
            byte_high = decompressed_data[i+1] if (i+1) < len(decompressed_data) else 0x00
            vram_byte_offset = (self.vmadd * 2) & 0xFFFF
            
            self.vram[vram_byte_offset] = byte_low
            self.vram[vram_byte_offset + 1] = byte_high
            
            if i == 0 or i == len(decompressed_data) - 2:
                self.event_log.append(
                    f"[DMA WRITE] VRAM Word $2118/$2119 @ WordAddr 0x{self.vmadd:04X} (ByteOffset 0x{vram_byte_offset:04X}) "
                    f"<- Val: 0x{byte_high:02X}{byte_low:02X}"
                )

            self.vmadd = (self.vmadd + increment_step) & 0x7FFF
            bytes_written += 2

        self.event_log.append(f"[DMA COMPLETO] Final VMADD = 0x{self.vmadd:04X}\n")

    def inspect_vram_region(self, word_start, word_length):
        byte_start = word_start * 2
        byte_end = byte_start + (word_length * 2)
        slice_data = self.vram[byte_start:byte_end]
        non_zero = sum(1 for b in slice_data if b != 0)
        return f"Rango VRAM Word 0x{word_start:04X}-0x{word_start+word_length:04X} -> Total Bytes: {len(slice_data)}, Bytes No-Cero: {non_zero}"

if __name__ == "__main__":
    ppu = SNES_PPU_Simulator()
    mock_sdd1_tiles = bytearray([0xFF, 0x00, 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC] * 128)

    print("=== ESCENARIO A: LO QUE ESTÁ HACIENDO TU ENGINE ACTUALMENTE (FALLO) ===")
    ppu.execute_sdd1_dma(mock_sdd1_tiles, bAdr=0x18)
    print(ppu.inspect_vram_region(0x2000, 0x1000))

    print("\n=== ESCENARIO B: LA SECUENCIA CORRECTA EN SNES (CÓMO DEBE FUNCIONAR) ===")
    ppu_ok = SNES_PPU_Simulator()
    ppu_ok.write_register(0x2115, 0x00)
    ppu_ok.write_register(0x2116, 0x00)
    ppu_ok.write_register(0x2117, 0x20)
    ppu_ok.execute_sdd1_dma(mock_sdd1_tiles, bAdr=0x18)
    print(ppu_ok.inspect_vram_region(0x2000, 0x1000))

    print("\n--- DETALLE DE LOGS DE LA EJECUCIÓN CORRECTA ---")
    for log in ppu_ok.event_log:
        print(log)
