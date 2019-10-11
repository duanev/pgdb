## smp

The 'smp' version of this arm64 nano-kernel brings all the cores online.

## To run with qemu, install qemu-system-aarch64 (v4.1.0 used here), then:
```
$ qemu-system-aarch64 -machine virt -cpu cortex-a53 -m 256 -monitor stdio -kernel smp.bin -smp 8
```

## To run with pgdb and qemu:
```
$ cd pgdb/examples/qemu/aarch64/smp
$ qemu-system-aarch64 -machine virt -cpu cortex-a53 -m 256 -monitor stdio -kernel smp.bin -smp 4 -s -S
```
(and in another 90x24 or larger terminal)
```
$ cd pgdb
$ python pgdb.py -gccmap examples/qemu/aarch64/smp/smp.map
```

#### Then press:
    'h'     toggle help menu
    'l'     toggle log menu
    'j'     jump to highlighted location in the code window (eg. break at instruction marked in white - the current pc is yellow)
#### then:
    's'     single step
    up/down arrow (move source window line at a time), page up/down (half page at a time)
            to move the highlighted location
    'j'     jump to new highlighted location, repeat jump to skip over ints and calls

Use 'J' (capital J) when ready to unleash the slave cpus (or else
they just sit at the start vector), and use cap 'S' to single step
all of them (qemu will break on a random cpu - so 'J' is better,
qemu run until your breakpoint is hit by any cpu).  Use cap 'C' to
let all cpus free run.

You can quit pgdb without killing qemu with 'q', then restart pgdb
and it will reload the current cpu state where you left off (good for
debugging pgdb), or cap 'Q' to exit both.



## Rebuild smp
install aarch64-linux-gnu-gcc
```
$ make clean
$ make
```
So far only verified with gcc -g -O1 (non)optimizations.


## SMP notes

ARMv8_PrgGuide_1189507856.pdf  pg 204  chapter 14  Multi-core processors



## Get qemu to debug some errors, trace some events

```
$ qemu-system-aarch64 -machine virt -cpu cortex-a53 -m 256 -monitor stdio -kernel smp.bin -d guest_errors,unimp,in_asm -s -S
```

Press any key in the qemu virtual terminal to reboot the simulated machine.
(smp thread 0, the boot thread, is polling on the uart rx status)  MAX_CPUS
is fixed at 8 (thats all that qemu-system-aarch64 currently supports).
