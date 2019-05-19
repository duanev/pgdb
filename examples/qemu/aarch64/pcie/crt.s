// ARM a53 baremetal C runtime (crt)
//
//      with UART character I/O
//
//        as guide: https://sourceware.org/binutils/docs-2.28/as/index.html
// pl011 datasheet: http://infocenter.arm.com/help/topic/com.arm.doc.ddi0183f/DDI0183.pdf

.section .text

    .global crt
crt:
    adrp    x0, _stack_start
    mov     sp, x0
    //bl      con_init            // not needed for qemu
    bl      main
    ldr     x0, =eop_msg
    bl      con_puts
    b       .                   // hang


// ---- uart -------------------------------

// regs
UART_DR  = 0x00
UART_ECR = 0x04
UART_FR  = 0x18
UART_IB  = 0x24
UART_FB  = 0x28
UART_CR  = 0x30

// bits
FR_TXFF = (1 << 5)
FR_RXFE = (1 << 4)
FR_BUSY = (1 << 3)

// baud
// divisor (int) | divisor (frac) | desired bps | generated bps | percent error
//       0x1             0x5          230400        231911          0.656
//       0x2             0xB          115200        115101          0.086
//       0x3            0x10           76800         76923          0.160
//       0x6            0x21           38400         38369          0.081
//      0x11            0x17           14400         14401          0.007
//      0x68             0xB            2400          2400             ~0
//     0x8E0            0x2F             110           110             ~0

BAUD_I = 0x2
BAUD_F = 0xb

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
    mov  w1,  BAUD_I
    str  w1,  [x0, UART_IB]
    mov  w1,  BAUD_F
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

    .align 4
uart_addr:
    .word  0x9000000        // qemu aarch64
//  .word 0x84000000


.section .data
eop_msg:
    .ascii "-- program done --"
    .byte  0

