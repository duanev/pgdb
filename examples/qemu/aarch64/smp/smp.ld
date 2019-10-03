/* https://ftp.gnu.org/old-gnu/Manuals/ld-2.9.1/html_chapter/ld_3.html */

MEMORY
{
    /*
     * memory regions seem hard coded for qemu aarch64:
     *   $ qemu-system-aarch64 -machine virt -cpu cortex-a53 -m 128 -monitor stdio -kernel smp.bin
     *   (qemu) info mtree
     */
    code : org = 0x40080000, len =  64K
    data : org = 0x40090000, len = 128K
}

SECTIONS
{
    code : { boot.o(.text) exc.o(.text) *.o(.text) } > code

    data : { *.o(.data) *.o(.bss) *(COMMON)
        _data_start = .;

        . = ALIGN(96K);

        _tls0 = .;
        _stack0_end = .;
        . += 1;
        . = ALIGN(4K);
        _stack0_start = .;

        _tls1 = .;
        _stack1_end = .;
        . += 1;
        . = ALIGN(4K);
        _stack1_start = .;

        _tls2 = .;
        _stack2_end = .;
        . += 1;
        . = ALIGN(4K);
        _stack2_start = .;

        _tls3 = .;
        _stack3_end = .;
        . += 1;
        . = ALIGN(4K);
        _stack3_start = .;

        _tls4 = .;
        _stack4_end = .;
        . += 1;
        . = ALIGN(4K);
        _stack4_start = .;

        _tls5 = .;
        _stack5_end = .;
        . += 1;
        . = ALIGN(4K);
        _stack5_start = .;

        _tls6 = .;
        _stack6_end = .;
        . += 1;
        . = ALIGN(4K);
        _stack6_start = .;

        _tls7 = .;
        _stack7_end = .;
        . += 1;
        . = ALIGN(4K);
        _stack7_start = .;

        _data_end = .;
    } > data
}
