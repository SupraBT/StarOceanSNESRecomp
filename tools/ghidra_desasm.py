#!/usr/bin/env python3
"""Desensambla un rango de la ROM con PyGhidra (lectura de un bucle concreto).

Por que existe: hay direcciones que el interprete ejecuta muchisimo y que **no
estan en ningun nodo** del manifiesto AOT -- el bucle del paron, `$C62D95`
(102.830 pasos en 6000 frames, ENCICLOPEDIA 31 y 35.3). Para saber que *es* ese
codigo (y no cuanto cuesta) hay que leerlo, y esto es lo que Ghidra hace bien:
desensamblar instrucciones reales en vez de adivinar.

Se le pasa un rango y extrae esa rebanada a un fichero crudo, la importa con el
lenguaje 65816 y la desensambla linealmente. Mapeo de bancos $C0-$CF: pagina 0
del MMC = `ROM[0:0x100000]`, o sea `banco-0xC0` por 0x10000 mas el PC de 16 bits
(ver `sdd1_mmc_linear`).

Uso:
    python tools/ghidra_desasm.py --rom "Star Ocean (Japan).sfc" \
        --desde C62D45 --hasta C62DCE
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


def rom_offset(pc24: int) -> int:
    """bancos $C0-$CF -> pagina 0 del MMC; $00-$7F -> LoROM lineal."""
    banco = (pc24 >> 16) & 0xFF
    if 0xC0 <= banco <= 0xFF:
        return ((pc24 >> 20) & 3) * 0  # pagina 0 por defecto
        # (el llamante decide la pagina; por defecto 0)
    return pc24


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", required=True)
    ap.add_argument("--desde", required=True, help="pc24 hex, p.ej. C62D45")
    ap.add_argument("--hasta", required=True, help="pc24 hex exclusivo")
    ap.add_argument("--page", type=lambda v: int(v, 0), default=0,
                    help="pagina del MMC para bancos $C0-$CF (por defecto 0)")
    ap.add_argument("--project", default=str(ROOT / "out" / "ghidra_proj"))
    args = ap.parse_args()

    desde, hasta = int(args.desde, 16), int(args.hasta, 16)
    banco = (desde >> 16) & 0xFF
    base = desde & 0xFFFF
    if 0xC0 <= banco <= 0xFF:
        ventana = (desde >> 20) & 3
        pagina = args.page if ventana == 0 else args.page + ventana
        off = (pagina << 20) | (desde & 0xFFFFF)
    else:
        off = desde
    n = (hasta - desde)
    rom = pathlib.Path(ROOT / args.rom).read_bytes() if not pathlib.Path(args.rom).is_absolute() \
        else pathlib.Path(args.rom).read_bytes()
    if off + n > len(rom):
        print("ERROR: rango fuera de la ROM (%d+%d > %d)" % (off, n, len(rom)))
        return 1

    import pyghidra  # noqa: E402
    pyghidra.start()

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="so_desasm_")) / "slice.bin"
    tmp.write_bytes(rom[off:off + n])
    proj = pathlib.Path(args.project)
    proj.mkdir(parents=True, exist_ok=True)

    with pyghidra.open_program(str(tmp), project_location=str(proj),
                               project_name="desasm", analyze=False,
                               language="65816:LE:16:default") as flat_api:
        prog = flat_api.getCurrentProgram()
        listing = prog.getListing()
        addr = prog.getAddressFactory().getDefaultAddressSpace().getAddress(base)
        print("ROM 0x%06X-%06X -> base de Ghidra 0x%04X (banco $%02X, pagina %d)"
              % (off, off + n, base, banco, args.page))
        print("--- desensamblado lineal; direcciones en la nomenclatura del invitado ---")
        pc = base
        fin = base + n
        while pc < fin:
            flat_api.disassemble(prog.getAddressFactory().getDefaultAddressSpace().getAddress(pc))
            ins = listing.getInstructionAt(
                prog.getAddressFactory().getDefaultAddressSpace().getAddress(pc))
            if ins is None:
                print("  $%06X  <sin instruccion: datos?>" % ((banco << 16) | pc))
                pc += 1
                continue
            print("  $%06X  %-22s %s" % ((banco << 16) | pc, ins.getMnemonicString(),
                                        ins.getDefaultOperandRepresentation(0) if ins.getNumOperands() else ""))
            pc += ins.getLength()
    return 0


if __name__ == "__main__":
    sys.exit(main())
