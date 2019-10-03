
    .macro vector vecno label
    .align 7
    \label:
    mov x0,  \vecno
    mrs x1,  esr_el1        // exception syndrome reg
    mrs x2,  elr_el1        // exception link reg
    mrs x3,  far_el1        // fault address reg
    bl  exc_handler
    b   .
    .endm

    .align 9
    .global exc_table
exc_table:

    vector  0 sp0_sync
    vector  1 sp0_irq
    vector  2 sp0_fiq
    vector  3 sp0_serror
    vector  4 spx_sync
    vector  5 spx_irq
    vector  6 spx_fiq
    vector  7 spx_serror
    vector  8 el64_sync
    vector  9 el64_irq
    vector 10 el64_fiq
    vector 11 el64_serror
    vector 12 el32_sync
    vector 13 el32_irq
    vector 14 el32_fiq
    vector 15 el32_serror

