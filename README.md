# pgdb
Python GDB RDP client (replaces gdb for QEMU tcp debug)

See READMEs in the example directories for quick start guides.

PGDB provides source level debugging for assembly code such as NASM
built ROMS and kernels.  Some support is also available for the GCC
tool chain.

You only need pgdb.py and pgdb_<arch>.py for the architecture you
want to debug in your current directory or path.  Python 2.7 and 3
supported.

PGDB video demo/tutorial on youtube:

<a href="http://www.youtube.com/watch?feature=player_embedded&v=TuvjGCcVXMc" target="_blank"><img src="http://img.youtube.com/vi/TuvjGCcVXMc/0.jpg" 
alt="IMAGE ALT TEXT HERE" width="240" height="180" border="10" /></a>


usage: python pgdb.py [-remote tcp::1234] [-nasmlst <file1>] [-objdump <file2>] ...

           h - toggles visibility of context sensitive help
           l - toggles visibility of the log window
         tab - rotates the active window
        back - makes no window active, start rotation at top
           r - reorder windows (useful after resize)
     <enter> - refresh window, if cpu make it active
       1-9,0 - select source window to display (twice to pin)
           / - text search source window (prompts for text)
           n - next text search
         b/w - set a breakpoint/watchpoint (prompts for addr)
           v - clear all breakpoints and watchpoints
           m - new memory window (prompts for address)
           M - destroy active memory window
           a - lookup a hex address in current source window
         s/S - single step active cpu / all cpus
         j/J - jump active cpu / all cpus to highlight addr
         c/C - continue active cpu / all cpus
         q/Q - quit pgdb / and kill qemu also
        ctrl+arrows - move active window around screen
         ctrl+space - raise active window to the top
     ctrl+pageup/dn - scroll active window (ex: log,mem)
     arrows,pageup,pagedn,home - scroll source window

breakpoint command help:
    QEMU breakpoints are logical hex addresses (CS is not involved).
    ESC aborts set breakpoint.  A suggested breakpoint value is taken
    from the address in the source window highlighted in white.
    The white address is the next valid instruction pointer location
    following the *focus point* on the source window (fixed at 3/4
    the way down the screen).  The address highlighted in yellow is
    the current cpu's current IP.

memory window address help:
    Memory addresses can be simple expressions
    with hex (only) constants, register names,
    and * + or -  (no parentheses are allowed):

    ex:    40ac0
           ebx + edi*2+3c

    or of the form: <struct>@<addr>,<count> where
    struct names are defined in the arch modules.
    (count is again in hex)

    ex:    gdt@mygdt,c



![ScreenShot](http://imgur.com/sq0o6tf)
<img src="http://imgur.com/sq0o6tf" title="ScreenShot">



Donations gladly accepted and will certainly attract more of my attention :)

    email: duanev at gmail
    bitcoin: 16yQJg1fXCvVUETQVpSoxLAwNPKXKRYvXN

