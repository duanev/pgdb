; OZ - A more utopian OS
; ex: set expandtab softtabstop=4 shiftwidth=4 nowrap :
;
;
;       x86-32 startup 
;
;
; usage:
;	$ qemu-system-i386 -boot a -fda oz_fd.img
;
; requires: nasm-2.07  or later from: http://www.nasm.us
;
; contributors:
;        djv - Duane Voth
;
; history:
; 2007/03/03 - 0.00.01 - djv - begin with various web examples
;                      http://linuxgazette.net/issue82/misc/raghu/code.asm.txt
;                      http://www.osdever.net/tutorials/brunmar/simple_asm.txt
; 2007/03/04 - 0.00.02 - djv - add timer interrupt support with stray int dbg
; 2007/03/05 - 0.00.03 - djv - remove stray int dbg, add mbr data struc back
; 2007/03/11 - 0.00.04 - djv - debug USB boot problem

%ifdef USB
[map symbols oz_usb.map]
%else
[map symbols oz_fd.map]
%endif

; -------- stage 1 ---------------------------------------------------------
; A classic x86 Master Boot Record

section .text start=0x7c00  ; PC BIOS boot loader entry point
codestart :

bios_entry :
    cli
    jmp short load_stage2   ; jump to stage2 loader, skip mbr data struct

times 6-($-$$)  db 0
oemid db "oz"

times 11-($-$$)  db 0

; compute the size of the kernel image in 512 byte sectors
nsectors equ codesize/512

; MS MBR  (http://support.microsoft.com/kb/140418)
%ifdef FLOPPY
    dw 512                  ; Bytes per sector
    db 1                    ; Sectors per cluster
    dw nsectors             ; Number of reserved sectors
    db 2                    ; Number of FATs
    dw 0x00e0               ; Number of dirs in root
    dw 0x0b40               ; Number of sectors in volume
    db 0xf0                 ; Media descriptor
    dw 9                    ; Number of sectors per FAT
    dw 18                   ; Number of sectors per track
    dw 2                    ; Number of heads
    dd 0                    ; Number of hidden sectors
    dd 0                    ; Large Sectors
%endif

%ifdef USB
    dw 0                    ; Bytes per sector
    db 0                    ; Sectors per cluster
    dw nsectors             ; Number of reserved sectors
    db 0                    ; Number of FATs
    dw 0                    ; Number of dirs in root
    dw 0                    ; Number of sectors in volume
    db 0                    ; Media descriptor
    dw 0                    ; Number of sectors per FAT
    dw 0                    ; Number of sectors per track
    dw 0                    ; Number of heads
    dd 0                    ; Number of hidden sectors
    dd 0                    ; Large Sectors
%endif

; -------- protected-mode support functions --------
bits 32

align 4
IRQA equ 32                 ; system timer interrupt (after remap)
int_handler_timer :
    mov  ax,videosel        ; point gs at video memory
    mov  gs,ax
    mov  bl,byte [gs:1]     ; inc the color of the first two chars
    inc  bl
    and  bl,0xf             ; just the foreground
    mov  byte [gs:1],bl
    mov  byte [gs:3],bl
    mov  al,0x20
    out  0x20,al            ; signal end of interrupt (eoi)
    iret

;F - white
;E - yellow
;D - magenta
;C - red
;B - cyan
;A - green
;9 - blue
;8 - dark grey

align 4
IRQB equ 33                 ; keyboard interrupt (after remap)
int_handler_kbd :
    cli
    mov  al,0x20
    out  0x20,al            ; signal end of interrupt (eoi)
    iret

; -------- main (enter protected mode) --------
bits 16
align 2

load_stage2 :
    push dx                 ; save BIOS drive number

    mov  ax,0x0600          ; ah=06h : scroll window up, if al = 0 clrscr
    mov  cx,0x0000          ; clear window from 0,0 
    mov  dx,0x174f          ; to 23,79
    mov  bh,0xf             ; fill with hi white
    int  0x10               ; clear screen for direct writes to video memory

    mov  si,bootmsg
    xor  bx,bx
    call puts_vga_rm
                            ; puts_vga_rm leaves gs pointing at video mem
    mov  byte [gs:1],0xE    ; turn the first two chars yellow
    mov  byte [gs:3],0xE

;   mov  ah,0x00            ; Fn 00h of int 16h: read next character
;   int  0x16               ; wait for the user to respond...

    lgdt [gdtr]             ; initialize the gdt
    mov  eax,cr0
    or   al,0x01            ; set the protected mode bit (lsb of cr0)
    mov  cr0,eax
    jmp  codesel:flush_ip1  ; flush the cpu instruction pipeline
flush_ip1: 
bits 32                     ; instructions after this point are 32bit

    mov  ax,datasel   
    mov  ds,ax              ; initialize the data segments
    mov  es,ax
    mov  ax,stacksel        ; setup a restricted stack segment
    mov  ss,ax

    ; re-program the 8259's to move the hardware vectors
    ; out of the soft int range ... what were people thinking!

    mov  al,0x11
    out  0x20,al            ; init the 1st 8259
    mov  al,0x11
    out  0xA0,al            ; init the 2nd 8259
    mov  al,0x20
    out  0x21,al            ; base the 1st 8259 at 0x20
    mov  al,0x28
    out  0xA1,al            ; base the 2nd 8259 at 0x28
    mov  al,0x04
    out  0x21,al            ; set 1st 8259 as master
    mov  al,0x02
    out  0xA1,al            ; set 2nd 8259 as slave
    mov  al,0x01
    out  0x21,al
    mov  al,0x01
    out  0xA1,al
    mov  al,0x00
    out  0x21,al
    mov  al,0x00
    out  0xA1,al

    ; ---- debug marker
    mov  ax,videosel        ; point gs at video memory
    mov  gs,ax
    mov  byte [gs:1],0xA    ; turn the first two chars green
    mov  byte [gs:3],0xA

    ; ---- setup interrupt handlers

    mov  eax,int_handler_timer
    mov  [idt+IRQA*8],ax
    mov  word [idt+IRQA*8+2],codesel
    mov  word [idt+IRQA*8+4],0x8E00
    shr  eax,16
    mov  [idt+IRQA*8+6],ax

    mov  eax,int_handler_kbd
    mov  [idt+IRQB*8],ax
    mov  word [idt+IRQB*8+2],codesel
    mov  word [idt+IRQB*8+4],0x8E00
    shr  eax,16
    mov  [idt+IRQB*8+6],ax

    lidt [idtr]                     ; install the idt
    mov  sp,stack_size              ; initialize the stack


    sti
idle :
    hlt                     ; wait for interrupts
    jmp  idle

; ----------------------------
;   puts_vga_rm - write a null delimited string to the VGA controller
;                  in real mode
;
;           esi - address of string
;           ebx - screen location (2 bytes per char, 160 bytes per line)
;           eax - destroyed
;            gs - destroyed
bits 16

puts_vga_rm :
    mov  ax,0xb800      ; point gs at video memory
    mov  gs,ax
puts_vga_rm_loop :
    lodsb
    cmp  al,0
    jz   puts_vga_rm_done
    mov  [gs:bx],al
    inc  ebx
    inc  ebx
    jmp  puts_vga_rm_loop
puts_vga_rm_done :
    ret

align 8                     ; only need 4 but 8 looks nicer when debugging
codesize equ ($-codestart)

; ---------------------------------------------------------
section .data
datastart :

; -------- descriptors --------------
; Intel SW dev manual 3a, 3.4.5, pg 103
;
; In my opinion, macros for descriptor entries
; don't make the code that much more readable.

gdt :
nullsel equ $-gdt           ; nullsel = 0h
    dd 0,0                  ; first descriptor per convention is 0

codesel equ $-gdt           ; codesel = 8h  4Gb flat over all logical mem
    dw 0xffff               ; limit 0-15
    dw 0x0000               ; base  0-15
    db 0x00                 ; base 16-23
    db 0x9a                 ; present, dpl=0, code e/r
    db 0xcf                 ; 32bit, 4k granular, limit 16-19
    db 0x00                 ; base 24-31

datasel equ $-gdt           ; datasel = 10h  4Gb flat over all logical mem
    dw 0xffff               ; limit 0-15
    dw 0x0000               ; base  0-15
    db 0x00                 ; base 16-23
    db 0x92                 ; present, dpl=0, data r/w
    db 0xcf                 ; 32bit, 4k granular, limit 16-19
    db 0x00                 ; base 24-31

stacksel equ $-gdt          ; stacksel = 18h  small limited stack
    dw stack_size           ; limit
    dw stack_loc            ; base
    db 0
    db 0x92                 ; present, dpl=0, data, r/w
    db 0                    ; 16bit, byte granular
    db 0

videosel equ $-gdt          ; videosel = 20h
    dw 3999                 ; limit 80*25*2-1
    dw 0x8000               ; base 0xb8000
    db 0x0b
    db 0x92                 ; present, dpl=0, data, r/w
    db 0x00                 ; byte granular, 16 bit
    db 0x00

gdt_end :

gdtr :
    dw gdt_end - gdt - 1    ; gdt length
    dd gdt                  ; gdt physical address

idtr :
    dw idt_end - idt - 1    ; length of the idt
    dd idt                  ; address of the idt


bootmsg     db      "OZ v0.00.04 - 2007/03/11  ",0

times 446-codesize-($-$$)  db 0 ; Fill with zeros up to the partition table

%ifdef USB
; a partition table for my 512MB USB stick
db 0x80, 0x01, 0x01, 0, 0x06, 0x10, 0xe0, 0xbe, 0x20, 0, 0, 0, 0xe0, 0x7b, 0xf, 0
db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
db 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
%else
            ; A default partition table that matches a 1.44MB floppy
            db 0x80,0x01,0x01,0x00,0x06,0x01,0x12,0x4f
            db 0x12,0x00,0x00,0x00,0x2e,0x0b,0x00,0x00
            db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
            db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
            db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
%endif

times 510-codesize-($-$$) db 0      ; fill with zeros up to MBR signature

            dw 0x0aa55      ; write aa55 in bytes 511,512 to indicate
                            ; that it is a boot sector. 

idt equ 0x6000              ; use some of the free memory below us
idt_end equ idt+48*8        ; 32 sw + 16 remapped hw vectors

stack_loc  equ 0x7000
stack_size equ 1024

datasize equ ($-datastart)

kend :
