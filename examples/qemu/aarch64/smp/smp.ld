/* https://ftp.gnu.org/old-gnu/Manuals/ld-2.9.1/html_chapter/ld_3.html */

MEMORY
{
    /*
     * memory regions seem hard coded for qemu aarch64:
     *   $ qemu-system-aarch64 -machine virt -cpu cortex-a53 -m 256 -monitor stdio -kernel smp.bin
     *   (qemu) info mtree
     */
    code : org = 0x40080000, len =  64K
    bss  : org = 0x40090000, len =  32K
    data : org = 0x40098000, len =  32K
}

SECTIONS
{
    code : { boot.o(.text) exc.o(.text) *.o(.text) } > code

    bss  : {
        _bss_start = .;

        *.o(.bss) *(COMMON)

        . = ALIGN(4K);
        _tls0 = .;
        _stack0_end = .;
        . += 1;
        . = ALIGN(4K);
        _stack0_start = .;

        _bss_end = .;
    } > bss

    data : {
        *.o(.data)

        . = ALIGN(32K);
        _free_mem = .;
    } > data
}
