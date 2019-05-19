
## To run pgdb with qemu, install qemu-system-arm (v3.1.0 used here), then:
```
$ cd pgdb/examples/qemu/arm-versatilepb/hello_world
$ QEMU_AUDIO_DRV=none qemu-system-arm -M versatilepb -m 128M -nographic -kernel test.bin -s -S
```
(don't use the virtual gpu terminal)
(and in another terminal)
$ cd pgdb
$ python pgdb.py -gccmap examples/qemu/arm-versatilepb/hello_world/test.map
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

