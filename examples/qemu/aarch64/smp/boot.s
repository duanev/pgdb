// ARM a53 baremetal boot (qemu)
//
//        as guide: https://sourceware.org/binutils/docs-2.28/as/index.html
// pl011 datasheet: http://infocenter.arm.com/help/topic/com.arm.doc.ddi0183f/DDI0183.pdf
//
//  -machine virtualization=on    # if you want to enable EL2
//  -machine secure=on            # supposedly enables EL3

.section .text

    .global boot_entry
boot_entry:
    ldr     x0, =exc_table          // setup the el1 exception vectors (exc.s)
    msr     vbar_el1, x0

    // ---- clear bss

    mov     x0, #0
    ldr     x1, =_bss_start
    ldr     x2, =_bss_end
1:
    str     x0, [x1], #8
    cmp     x1, x2
    blt     1b

    // ---- initialize stack0

    ldr     x0, =_stack0_start
    mov     sp, x0
    adrp    x0, _tls0
    msr     tpidr_el0, x0

    bl      con_init
    bl      main

    ldr     x0, =msg_eop
    bl      con_puts

    // ---- if main returns

reboot:
    ldr     x0, =1000000000         // qemu: about 3 seconds
1:
    sub     x0, x0, #1
    cbnz    x0, 1b                  // delay so con_puts can be seen
    ldr     x0, =msg_reboot
    bl      con_puts

    ldr     x0, =0x84000009         // system reset
    hvc     0                       // hypervisor call

    .global smp_entry
smp_entry:
    ldr     x3, =exc_table          // setup the el1 exception vectors (exc.s)
    msr     vbar_el1, x3

    ldr     x3, [x0]
    mov     sp, x3
    .extern smp_newcpu              // provided by smp.c
    b       smp_newcpu


// ---- pl011 uart -------------------------

UART_DR  = 0x00
UART_ECR = 0x04
UART_FR  = 0x18
UART_IB  = 0x24
UART_FB  = 0x28
UART_CR  = 0x30

FR_TXFF = (1 << 5)
FR_RXFE = (1 << 4)
FR_BUSY = (1 << 3)

ASCII_NL = 10
ASCII_CR = 13

    .macro wait_for_tx_ready
    1:
        ldr     w3, [x1, UART_FR]
        mov     w4, #(FR_TXFF | FR_BUSY)
        and     w3, w3, w4
        cbnz    w3, 1b
    .endm

    .global con_init
con_init:
    ldr  x0, uart_addr
    str  wzr, [x0, UART_CR]
    str  wzr, [x0, UART_ECR]
    str  wzr, [x0, UART_DR]
    mov  w1,  0x2               // 115200 baud
    str  w1,  [x0, UART_IB]
    mov  w1,  0xb               // 115200 baud
    str  w1,  [x0, UART_FB]
    mov  w1,  0x301
    str  w1,  [x0, UART_CR]
    ret

    .global con_puts
con_puts:
    ldr  x1, uart_addr
loop:
    wait_for_tx_ready
    ldrb w2, [x0]
    cmp  x2, #0
    b.eq done
    cmp  w2, ASCII_NL
    b.ne 2f
    mov  w3, ASCII_CR
    str  x3, [x1]
    wait_for_tx_ready
2:
    str  x2, [x1]
    add  x0, x0, #1
    b    loop
done:
    ret

    .global con_getc
con_getc:
    ldr  x1, uart_addr
1:
    ldr  w2, [x1, UART_FR]
    and  w2, w2, #FR_RXFE
    cbnz w2, 1b
    ldr  w0, [x1, UART_DR]
    ret

    .global con_peek
con_peek:
    mov  x0, #0
    ldr  x1, uart_addr
    ldr  w2, [x1, UART_FR]
    and  w2, w2, #FR_RXFE
    cbnz w2, 1f
    add  x0, x1, #1
1:
    ret


    .align 4
uart_addr:
    .word  0x9000000        // qemu aarch64


.section .data

msg_eop:
    .ascii "-- program done --\r\n"
    .byte  0

msg_reboot:
    .ascii "-- rebooting --\r\n"
    .byte  0

    .global boot_end
boot_end:

