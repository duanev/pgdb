# pgdb
Python GDB RDP client (replaces gdb for QEMU tcp debug)

See READMEs in the example directories for quick start guides.

No, seriously, to try out PGDB, pick an example directory and
follow the README - that is the fastest way.

PGDB provides source level debugging for assembly code such as NASM
built ROMS and kernels.  I've added a lot of support for the GCC
tool chain, but its complex and is likely missing features.

Python 2.7 and 3.x should both work.

You only need pgdb.py and pgdb_*arch*.py for the architecture you
want to debug in your current directory or path.

PGDB has been updated for QEMU 3.1.0 (as of 2019).  3.1.0 has GDB RDP
(remote debug protocol) support for AARCH64 floating point and system
registers, and uses the new xml format to describe x86 architectures
(unfortunatly the x86 system registers are still missing).  Regardless,
this is a far better environment than the previous QEMU 2.x situation,
and so QEMU 2.x is no longer supported.

PGDB video demo/tutorial on youtube (not updated for the 2019 release,
so the i386 to x86_64 transition at 16:45 is different - qemu now simply
starts in 64bit mode even though the cpu is in 32bit mode :< and doesn't
tell us about any transitions ... hopefully this will be addressed when
the system registers are implemented so the alter-ego feature of pgdb
can again be used):

<a href="http://www.youtube.com/watch?feature=player_embedded&v=TuvjGCcVXMc" target="_blank"><img src="http://img.youtube.com/vi/TuvjGCcVXMc/0.jpg" 
alt="IMAGE ALT TEXT HERE" width="240" height="180" border="10" /></a>


usage: python pgdb.py [-remote tcp::1234] [-nasmlst <file1>] [-objdump <file2>] ...

           h - toggles visibility of context sensitive help
           l - toggles visibility of the log window
         tab - rotates the active window
        back - makes no window active, start rotation at top
           r - reorder windows (useful after resize)
     <enter> - refresh window, if cpu make it active
    <number> - select source window (twice to pin)(sh+N 11-20)
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

### breakpoint command help:
    QEMU breakpoints are _logical_ hex addresses (CS is not involved).
    ESC aborts set breakpoint.  A suggested breakpoint value is taken
    from the address in the source window highlighted in white.
    The white address is the next valid instruction pointer location
    following the *focus point* on the source window (fixed at 3/4
    the way down the screen).  The address highlighted in yellow is
    the current cpu's current IP.

### memory window address help:
    Memory addresses can be simple expressions
    with hex (only) constants, register names,
    and * + or -  (no parentheses are allowed):

    ex:    40ac0
           ebx + edi*2+3c

    or of the form: <struct>@<addr>,<count> where
    struct names are defined in the arch modules.
    (count is again in hex)

    ex:    gdt@mygdt,8



![ScreenShot](http://imgur.com/sq0o6tf)
<img src="https://user-images.githubusercontent.com/153577/57986990-648dfa80-7a41-11e9-82c8-c46da3d33490.png" title="ScreenShot">



Donations gladly accepted and will certainly attract more of my attention :)

    email: duanev at gmail
    btc: 3PkNXvGkzeLR2J1xgPHkFDEM7xFbEHCZQB
    eth: 0xddf2A3501333a88f1e0210D1F704aEC3496B1b51
    ltc: MCz4GnddyXLXvVa1wvb7WnzTT5JVLMgA2j

