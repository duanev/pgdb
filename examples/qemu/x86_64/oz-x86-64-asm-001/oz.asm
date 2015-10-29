; OZ - A more utopian OS
; ex: set expandtab softtabstop=4 shiftwidth=4 nowrap :
;
;
;       x86-64 startup 
;
;
; usage:
;	$ qemu-system-x86_64 -boot a -fda oz_fd -monitor stdio
;
; requires: nasm-2.07  or later from: http://www.nasm.us
;
; credits:
;       many thanks to the folks at wiki.osdev.org who archive great info.
;       http://wiki.osdev.org/Entering_Long_Mode_Directly
;
; contributors:
;        djv - Duane Voth
;
; history:
; 2015/10/12 - 0.00.64 - djv - dup oz-x86-32-asm-001, get into 64bit mode

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
    jmp 0:main              ; load cs, skip over mbr data struct

times 6-($-$$)  db 0
oemid db "oz"

times 11-($-$$)  db 0

; compute the size of the kernel image in 512 byte sectors
nsectors equ codesize/512

; -------- main (enter protected mode) --------
bits 16
align 2

main :
    mov  ax,kstack_loc
    mov  sp,ax
    xor  ax,ax
    mov  ss,ax
    mov  es,ax
    mov  ds,ax
    mov  fs,ax
    mov  gs,ax
    cld

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

    ; ---- verify this is a 64bit processor

    pushfd
    pop  eax
    mov  ebx,eax
    xor  eax,0x200000       ; flip the cpuid test flag
    push eax
    popfd
    pushfd
    pop  eax
    xor  eax,ebx            ; did anything change?
    jnz  have_cpuid

not64 :
    mov  si,no64msg
    xor  bx,bx
    call puts_vga_rm
halt :
    hlt
    jmp  halt               ; we're done

have_cpuid :
    push ebx
    popfd                   ; restore flags

    mov  eax,0x80000000
    cpuid
    cmp  eax,0x80000001     ; is extended function 0x80000001 available?
    jb   not64

    mov  eax,0x80000001
    cpuid
    test edx, 1 << 29       ; test LM bit
    jz   not64

    ; ---- setup 4KB paging tables
    ;           swdev3a s4.5 pg 4-25 fig 4-8
    ;           swdev3a s4.6 pg 4-23 fig 4-10

    mov  edi,pml4e          ; first pml4
    mov  cr3,edi            ; install it in cr3
    mov  eax,pdpte + 7
    stosd
    xor  eax,eax
    mov  ecx,0x400-1
    rep  stosd

            ; assume pdpte physically follows pml4

    mov  ax,pgdir + 7       ; next setup the pdpte
    stosd
    xor  eax,eax
    mov  cx,0x400-1
    rep  stosd

            ; assume pgdir physically follows pdpte

    mov  ax,pgtb0 + 7       ; page table 0: present, pl=3, r/w
    stosd                   ; ... pl=3 for now (simplify vga access)
    xor  eax,eax            ; invalidate the rest of the addr space
    mov  cx,0x400-1
    rep stosd

            ; assume pgtb0 physically follows pgdir
            ; pgtb0 is the page table for kernel memory

    stosd                   ; access to page 0 will always cause a fault
    stosd
    mov  ebx,eax
    mov  ax,0x1000 + 3      ; rest are direct map: present, pl=0, r/w
    mov  cx,0x200-1
pgtb0_fill :
    stosd
    xchg eax,ebx
    stosd
    xchg eax,ebx
    add  eax,0x1000
    loop pgtb0_fill

            ; enable paging and protected mode

    mov  eax,0xa0
    mov  cr4,eax            ; set the pae and pge

    mov ecx,0xc0000080      ; get the efer msr
    rdmsr    
    or  ax,0x00000100       ; set lme
    wrmsr

    mov eax,cr0
    or  eax,0x80000001      ; enable paging and protected mode together
    mov cr0,eax 

    ; ----

    lgdt [gdtr]             ; initialize the gdt
    jmp  codesel:flush_ip1  ; flush the cpu instruction pipeline
flush_ip1: 
bits 64                     ; instructions after this point are 64bit

    mov  ax,datasel         ; yes its silly to load the segments regs in 64bit
    mov  ds,ax              ; mode (only fs & gs can be used) but this helps us
    mov  es,ax              ; check to see if we are parsing the qemu register
    mov  ss,ax              ; dumps correctly
    mov  fs,ax
    mov  ax,videosel
    mov  gs,ax

    ; ---- debug marker
    mov  byte [gs:rbx+1],0xA        ; turn the first two chars green
    mov  byte [gs:rbx+3],0xA

    ;sti                     ; can't do this ...
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
    dq 0,0                  ; first descriptor per convention is 0

codesel equ $-gdt           ; codesel = 10h  4Gb flat over all logical mem
    dw 0x0000               ; limit 0-15
    dw 0x0000               ; base  0-15
    db 0x00                 ; base 16-23
    db 0x9a                 ; present, dpl=0, code e/r
    db 0x20                 ; 4k granular, 64bit/8bit, limit 16-19
    db 0x00                 ; base 24-31
    dd 0                    ; base 32-63
    dd 0

datasel equ $-gdt           ; datasel = 20h  4Gb flat over all logical mem
    dw 0x0000               ; limit 0-15
    dw 0x0000               ; base  0-15
    db 0x00                 ; base 16-23
    db 0x92                 ; present, dpl=0, data r/w
    db 0x20                 ; 4k granular, 64bit/8bit, limit 16-19
    db 0x00                 ; base 24-31
    dd 0                    ; base 32-63
    dd 0

videosel equ $-gdt          ; videosel = 30h
    dw 3999                 ; limit 80*25*2-1
    dw 0x8000               ; base 0xb8000
    db 0x0b
    db 0x92                 ; present, dpl=0, data, r/w
    db 0x20                 ; byte granular, 64bit/8bit
    db 0                    ; base 24-31
    dd 0                    ; base 32-63
    dd 0

gdt_end :

gdtr :
    dw gdt_end - gdt - 1    ; gdt length
    dq gdt                  ; gdt physical address

idtr :
    dw idt_end - idt - 1    ; length of the idt
    dq idt                  ; address of the idt

bootmsg     db      "OZ v0.00.64 - 2015/10/12",0
no64msg     db      "cpu not 64bit ",0

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

pml4e equ 0x1000            ; use some of the free memory below us
pdpte equ 0x2000            ; code above assumes this follows pml4e
pgdir equ 0x3000            ; code above assumes this follows pdpte
pgtb0 equ 0x4000            ; code above assumes this follows pgdir

idt equ 0x6000
idt_end equ idt+48*8        ; 32 sw + 16 remapped hw vectors

kstack_loc  equ 0x7000
kstack_size equ 1024

datasize equ ($-datastart)

kend :
