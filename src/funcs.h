/* Function declarations for Star Ocean recompiled code.
 * This file provides forward declarations for functions in the generated code.
 */

#ifndef FUNCS_H
#define FUNCS_H

#include "cpu_state.h"

/* Bank 00 function declarations */
RecompReturn I_IRQ_M0X0(CpuState *cpu);
RecompReturn I_IRQ_M0X1(CpuState *cpu);
RecompReturn I_IRQ_M1X0(CpuState *cpu);
RecompReturn I_IRQ_M1X1(CpuState *cpu);
RecompReturn I_NMI_M0X0(CpuState *cpu);
RecompReturn I_NMI_M0X1(CpuState *cpu);
RecompReturn I_NMI_M1X0(CpuState *cpu);
RecompReturn I_NMI_M1X1(CpuState *cpu);
RecompReturn I_RESET_M1X1(CpuState *cpu);

/* Add more function declarations as needed by the generated code */

#endif /* FUNCS_H */