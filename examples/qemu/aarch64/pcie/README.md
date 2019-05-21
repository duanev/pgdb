
## To run pgdb with qemu, install qemu-system-aarch64 (v3.1.0 used here), then:
```
$ cd pgdb/examples/qemu/aarch64/pcie
$ qemu-system-aarch64 -machine virt -cpu cortex-a53 -m 128 -monitor stdio -kernel pcie.bin -s -S
```
(and in another 90x24 or larger terminal)
```
$ cd pgdb
$ python pgdb.py -gccmap examples/qemu/aarch64/pcie/pcie.map
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

You can quit without killing qemu with 'q', then restart pgdb and
it will reload the current cpu state where you left off,
or 'Q' to exit both and start over.


## Rebuild
install aarch64-linux-gnu-gcc
```
$ make clean
$ make
```

## Bugs:
* The names for the a53 psr flags are probably not right.



## Useful qemu command lines for alternate pcie configurations:

```
$ qemu-system-aarch64 -machine virt -cpu cortex-a53 -m 128 -monitor stdio -kernel pcie.bin -readconfig pcie.cfg -d guest_errors,mmu,unimp,in_asm -s -S
```

```
$ qemu-system-aarch64 -machine virt -cpu cortex-a53 -m 128 -monitor stdio -kernel pcie.bin -device nvme,serial=f0,drive=n0 -drive file=dsk0.img,if=none,format=raw,id=n0 -device pcie-root-port,id=r1,slot=0 -d guest_errors,mmu,unimp,in_asm -s -S
```
execute pcie until ```con_getc()```, then enter the below to hotplug a new nvme device:
```
(qemu) drive_add 1.1 file=dsk1.img,if=none,format=raw,id=n1
(qemu) device_add nvme,serial=f1,drive=n1,bus=r1
```
press a key in the qemu virtual terminal to exit ```con_getc()```, continue pcie to rescan.

