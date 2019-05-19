
## To run pgdb with qemu, install qemu-system-aarch64 (v3.1.0 used here), then:
```
$ cd pgdb/examples/qemu/arm-versatilepb/hello_world
$ qemu-system-aarch64 -machine virt -cpu cortex-a53 -m 128 -kernel test.bin -monitor stdio -s -S
```
(and in another 90x24 or larger terminal)
```
$ cd pgdb
$ python pgdb.py -gccmap examples/qemu/aarch64/hello_world/test.map
```

#### Then press:
    'h'     toggle help menu
    'l'     toggle log menu
    'j'     jump to highlighted location in the code window (eg. run till marked instruction)

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



