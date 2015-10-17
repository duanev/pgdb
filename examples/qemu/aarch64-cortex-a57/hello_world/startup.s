.global _Reset

.section .text
_Reset:
    ldr x0, uart_addr
    ldr x1, =banner
loop:
    ldrb w2, [x1]
    cmp  x2, #0
    b.eq done
    str  x2, [x0]
    add  x1, x1, #1
    b    loop
done:
    b .

    .align 4
uart_addr:
    .word 0x9000000

.section .data
banner:
    .ascii "Hello world!"
    .byte  0

