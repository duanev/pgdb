
## To run with qemu, install qemu-system-aarch64 (v4.0.50 used here), then:
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
    'j'     jump to highlighted location in the code window (eg. run till marked instruction)
#### then:
    's'     single step
    up/down arrow (move source window line at a time), page up/down (half page at a time)
            to move the highlighted location
    'j'     jump to new highlighted location, repeat jump to skip over ints and calls

Use 'J' (capital J) when ready to unleash the slave cpus (or else
they just sit at the start vector), and use 'S' to single step all
of them (qemu will break on a random cpu - 'J' is better, qemu runs
until your instruction is executed by any cpu), and 'C' to let all
cpus free run.

You can quit without killing qemu with 'q', then restart pgdb and
it will reload the current cpu state where you left off (good for
debugging pgdb), or 'Q' to exit both and start over.



## Rebuild smp
install aarch64-linux-gnu-gcc
```
$ make clean
$ make
```
So far only verified with gcc -g -O1 (non)optimizations.


## SMP notes

ARMv8_PrgGuide_1189507856.pdf  pg 204  chapter 14  Multi-core processors



## Get qemu to debug some errors

```
$ qemu-system-aarch64 -machine virt -cpu cortex-a53 -m 256 -monitor stdio -kernel smp.bin -d guest_errors,unimp,in_asm -s -S
```

press a key in the qemu virtual terminal to exit and reboot the
simulated machine ... but memory is not cleared and the bss is
not re-initialized!

