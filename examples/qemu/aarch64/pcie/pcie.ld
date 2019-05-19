/* https://ftp.gnu.org/old-gnu/Manuals/ld-2.9.1/html_chapter/ld_3.html */

MEMORY
{
    /*
     * memory regions seem hard coded for qemu aarch64:
     *     $ qemu-system-aarch64 -machine virt -cpu cortex-a53 -m 128 -monitor stdio -kernel hv1.bin
     */
    code : org = 0x40080000, len = 16K
    data : org = 0x40084000, len = 16K
}

SECTIONS
{
    code : { crt.o(.text) *.o(.text) } > code

    data : { *.o(.data) *.o(.bss) *(COMMON)
        . = ALIGN(2K);
        _stack_end = .;
        . = ALIGN(4K);
        _stack_start = .;
    } > data
}
