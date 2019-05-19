MEMORY
{
    rom  : ORIGIN = 0x40080000, LENGTH = 1K
}

SECTIONS
{
   .text : { *(.text*) } > rom
}
