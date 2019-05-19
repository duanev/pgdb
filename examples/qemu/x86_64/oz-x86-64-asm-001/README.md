
To run pgdb with qemu, install qemu-system-x86_64 (v3.1.0 used here), then:
```
$ cd <gitdir>/pgdb/examples/qemu/x86_64/oz-x86-64-asm-001
$ qemu-system-x86_64 -boot a -fda oz_fd -monitor stdio -s -S
```
(and in another terminal)
```
$ cd <gitdir>pgdb
$ python pgdb.py -nasmlst examples/qemu/x86_64/oz-x86-64-asm-001/oz_fd.lst
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
    '/lgdt<enter>'   will search for the lgdt instruction in the code window
    home    will recenter the code window to the left margin
    'j'     jump to the lgdt instruction
    's' x2  step twice to get into protected mode
    'm' followed by 'gdt@gdt,7<enter>' to open a new window that displays 7 gdt entries
    'c'     to free run
#### to regain debug control:
    goto the qemu monitor (the (qemu) prompt) and type 'stop', pgdb will reactivate

You can quit without killing qemu with 'q', then restart pgdb and
it will reload the current cpu state where you left off,
or 'Q' to exit both and start over.


## Rebuild
```
$ make clean
$ make
```
