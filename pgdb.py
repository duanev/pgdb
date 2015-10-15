#!/usr/bin/env python
# vi: set tabstop=8 expandtab softtabstop=4 shiftwidth=4

"""
Copyright (c) 2015, Duane Voth
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

#
# Python GDB RDP client (replaces gdb for QEMU tcp debug)
#
# why:
#   - gdb won't ever understand non-gas assemblers (like NASM)
#   - gdb still doesn't deal with multiple cores (nicely? at all?)
#   - gdb is cumbersome, its time to raise the bar.
#
# resources:
#   https://sourceware.org/gdb/onlinedocs/gdb/Remote-Protocol.html
#
# usage:
#   $ qemu-system-i386 -s -S ....     (opens a window (or not) and stops)
#   (then from a separate terminal)
#   $ python pgdb_x86.py -nasmlst myasmcode.lst -objdump myccode.lst ...
#
# implementation notes:
#   - PGDB is a purely event driven app.  Keyboard events and gdb-rdp-tcp
#       receive events drive ALL actions.
#   - update_status('...', CPdbg) is a possible one-line debug mechanism,
#       or use the Log.write('...\n', CPdbg)
#   - gdb rdp (remote debug protocol) thinks in 'threads' (based from 1)
#       but pgdb thinks in 'cpus' (based from 0).
#   - the words 'panel' and 'window' seem to be used interchangeably,
#       but no, windows are 'seen' by the user, panels are the software
#       objects that often result in windows ... yeah, it's fuzzy,
#   - specific architectures have different names for the instruction
#       pointer - pgdb simply labels them all as 'ip'.
#   - when using a lot of cpu cores, it can take a while to refetch all
#       the regs after a single-step or emulator stop, some display events
#       don't fire until all the data has been retrieved (be patient).
#   - python exceptions go to the log window once the main loop runs.
#       you can scroll back and forward with ctrl-pgup and ctrl-pgdown.
#   - my approach to tracking program flow (by doing text searches through
#       .lst and .map files) is *not* deterministic and will undoubtedly
#       give incorrect results in certain complex situations with overlapping
#       logical address spaces.  and there is some squirrely code to support
#       this of which I'm not entirely proud.  but this approach allows us
#       to more easily trace rom-able code where we may only have a binary
#       image, a lst file, and maybe a map file.  I will argue against trying
#       to make pgdb handle elf executables and object files if it means
#       breaking the text based current approach. (but a "different" version
#       of pgdb would be fine as a complete gdb replacement)
#   - "pinning" the source window is one workaround for overlapping address
#       spaces.  Pressing a number key twice pins a source window; pressing
#       any other number key unpins the source window, as does a clearly
#       better choice that causes an automatic switch.
#   - when generating .lst files using gcc and objdump, be sure to use:
#           $ gcc -O0 ...
#           $ objdump -S ...
#   - symbol support (from a map file) was added for gcc/objdump
#       nasm so far doesn't need it.
#   - segment support is questionable, but for non-segmented architectures,
#       defining a segment to be like an overlay works fine, where each
#       overlay gets a unique number.
#   - qemu-system-arm -kernel for some reason reports the pc values to be
#       *relative* to the start address at 0x10000.  this messes everything up.
#       for now, a *negative* segment offset brings the symbols into line,
#       but yeah it's a hack ...
#   - nasm happily allows you to put data in your .text segment.
#       pgdb however keeps symbols found in the .text segment separate from
#       symbols found in the .data segment.  text symbols work for breakpoint
#       addresses, data symbols work for memory and watchpoint addresses.
#       if to a mem address prompt you type gdt@mygdt and pgdb says 'error
#       in [mygdt] at mygdt' then maybe you are missing a .data section.
#   - bro, I just wanna read your code, why isn't this shit all in some README?
#       because my young padawan, the less your crap is spread out, the
#       easier it is to clean up.
#
# todo:
#   - handle multiple breakpoints, let some remain active across continues.
#   - better support for multiple memory windows: auto update, highlight in
#       yellow which bytes have changed - should be able to embed the fancy
#       \a \t control characters and use ccs() to make it a small bit simpler.
#   - better expressions for memory addresses (allow more math and segment
#       regs and do selector lookups for protected mode)
#   - add an 'x' command to modify memory ...
#   - add an 'r' command to modify registers ...
#   - properly fetch multiple memory regions with chained rdp fetches.
#       this is being done currently but it is an accident that it sometimes
#       works correctly -- what breaks is if you put up two mem windows with
#       the same starting address (or try to display flat memory AND a data
#       structure over the same region at the same time).  multiple requests
#       for memory region dumps cannot be distinguished, so funneling them
#       all through the rdp interface causes downstream display events to
#       get confused or lost.  what is needed is a memory 'cache'.  all
#       memory windows should pool their requests and share their answers
#       so overlapping regions don't cause multiple rdp fetches and one
#       answer can update all interested memory windows.  but it will be a
#       significant project ...
#   - fetch complex data structures via rdp (ie. gdt/ldt/idt with multiple
#       chained lookups).  once the above is fixed, it would be nice to
#       pull segment the selectors for each segment register in use by a cpu.
#   - if terminal resize shrinks display and cuts off windows - they can
#       no longer be moved.  resize enlarge however won't unfreeze moves!
#       (probably a curses bug - can we watch for resize events and relocate
#       windows so they don't get cut off?)  for now, don't shrink the
#       terminal window while pgdb is running.
#   - support for other architectures: mips, ppc, s390, etc.  arm has
#       been started - remember, pgdb is primarily a gdb rdp front end ...
#   - finish abstracting out all the x86_32 specific code placing it in
#       pgdb_x86_32.py  (there is no need for classes here, python modules
#       create a perfectly functional name space boundary which is all we need)
#   - other architectures: x86_64, arm32, arm64, mips32, mips64, s390x, etc.
#       names should match qemu build names (i386 and 64 need to be combined
#       if qemu-x86_64 can switch midstream to 64bit - but I don't know yet
#       when this happens - gdb has a 'set architecture i386:x86-64' command
#       but it doesn't do cause any rdp traffic)
#   - add a general purpose disassembler per architecture so source files
#       don't need to be loaded
#   - add a -structs command line flag to load data structures that are not
#       tied to a specific architecture.  aka:
#           $ pgdb -arch x86_64 -structs linux4.0.7,mydriver,yourapp
#
# future:
#   - properly define source contexts and what they mean.  as I've added
#       features such as proper symbol support, the temporary work arounds
#       I used to support multiple source contexts have become strained.
#       restricting symbol lookups to the source context in which they were
#       defined is good in some cases, bad in others.
#       ex: if there are no overlapping address spaces for all the code we
#       are working on, then we of course want to be able to say 'show me
#       mem addr X' or 'break at Y' and pgdb does the right thing regardless
#       of which source file is being displayed.  but if there are
#       overlapping spaces, then which X or Y in what space do you mean?
#       for multiple spaces, clearly, we have to remain source context
#       sensitive.  but then users have to select the correct source window
#       before mem windows or breaks or watches can be set ...
#       or maybe pgdb can prompt the user to change contexts when a symbol
#       not defined in the current context exists in another?
#       and shouldn't some memory windows be bound to the source contexts?
#       if we are tracing through a kernel there are kernel data structures
#       and there are user mode data structures - they shouldn't all be on
#       the screen at once.
#   - what is being said here for the objdump and the gcc tool chain?
#       or for listing files in general?  perhaps there is a use for an
#       integrated listing/map file (and I don't mean that the symbols are
#       simply listed at the end) - that is built from both the object files
#       and a map file - maybe a *single* text file detailing all post-link
#       addresses, machine opcodes, and interlaced source code is a way to
#       improve debugging productivity - as opposed to tools that try to
#       integrate multiple files ...
#
# gdb remote debug protocol changes that are BADLY needed:
#   - the response string must include the command to which it is replying
#       (solves race conditions for event driven designs that queue cmds)
#   - return the control regs (gdt,ldt,cr3,etc!) c'mon!?  why just a subset?!
#       could also easily return the complete gdt/ldt descriptors for the
#       segment regs in protected mode too (would make our lives way easier)
#
# contributors:
#   djv - Duane Voth
#
# history:
#   2015/10/12 - v0.05 - djv - released

Version = "PGDB v0.05 2015/10/12"

# We're fresh out of lines for the main help window - too many keys
# to document.  (Note, we have to fit in 24 lines)  I can't seem to
# get rid of the last blank line either.

Help_text_main = \
"""      h - toggles visibility of context sensitive help
       l - toggles visibility of the log window
     tab - rotates the active window
       r - reorder windows (useful after resize)
 <enter> - refresh window, if cpu make it active
   1-9,0 - select source window to display (twice to pin)
       / - text search source window (prompts for text)
       n - next text search
     b/w - set a breakpoint/watchpoint (prompt for addr)
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
 arrows,pageup,pagedn,home - scroll source window"""

Help_text_breakpoints = \
"""
 QEMU breakpoints are logical hex addresses (CS is not involved).
 ESC aborts set breakpoint.  A suggested breakpoint value is taken
 from the address in the source window highlighted in white.
 The white address is the next valid instruction pointer location
 following the *focus point* on the source window (fixed at 3/4
 the way down the screen).  The address highlighted in yellow is
 the current cpu's current IP."""

Help_text_mem_address = \
"""
 Memory addresses can be simple expressions
 with hex (only) constants, register names,
 and * + or -  (no parentheses are allowed):

 ex:    40ac0
        ebx + edi*2+3c

 or of the form: <struct>@<addr>,<count> where
 struct names are defined in the arch modules.
 (count is again in hex)
"""

import os
import re
import sys
import string
import curses
import curses.panel
import socket
import asyncore
import traceback
import importlib

Arch = None
Arch_name = 'i386'          # qemu-i386 doesn't offer any .xml files
                            # oh oh, qemu-alpha doesn't either, nor do the
                            # sparcs -- gees, put your fav default here!

Host_port = ('0.0.0.0', 1234)

# ----------------------------------------------------------------------------
# early command line processing

if '-h' in sys.argv or '--help' in sys.argv:
    print('usage: python pgdb.py [-remote tcp::1234] [-nasmlst <file1>] [-objdump <file2>] ...')
    print()
    print(Help_text_main)
    print()
    print(Help_text_breakpoints)
    print()
    print(Help_text_mem_address)
    sys.exit(0)

if '-remote' in sys.argv:
    idx = sys.argv.index('-remote')
    sys.argv.pop(idx)
    remote = ''
    try:
        remote = sys.argv.pop(idx)
        medium, host, port = remote.split(':')
        if medium != 'tcp': raise Exception('only tcp supported so far')
        if len(host) == 0: host = '0.0.0.0'
        port = int(port)
        Host_port = (host, port)
    except:
        print('bad -remote arg [%s]: %s' % (remote, sys.exc_info()[1]))
        sys.exit(0)

if '-arch' in sys.argv:
    idx = sys.argv.index('-arch')
    sys.argv.pop(idx)
    Arch_name = sys.argv.pop(idx)

def load_arch_module():
    global Arch
    if Arch:
        return

    fn = 'pgdb_' + Arch_name
    try:
        Arch = importlib.import_module(fn)
        Log.write('Cpu architecture is ' + Arch.name + '\n', attr=CPok)
        Arch.Log = Log
    except:
        Arch = FakeArch()
        Log.write('unable to load %s\n' % fn, CPerr)
        Log.write('try:  python %s  alone to check for errors\n' % fn, CPerr)

class FakeArch(object):
    name = 'ERSATZ'
    gspec = []
    gspec_len = 0
    cpu_maxy = cpu_maxx = 4

    def generate_gspec(self, tree): pass
    def get_seg_register(self, x): return None
    def get_ip_register(self, x): return None
    def cpu_reg_update(self, x, y): return []

# ----------------------------------------------------------------------------
# gdb client support

Gdbc = None
Breakpoints = {}        # a list of active 'Z0,xxxx,1' breakpoint commands
Watchpoints = {}        # a list of active 'Z2,xxxx,n' watchpoint commands


def lsn2msn(s):
    # gdb 'g' register strings are sent least-significant-nibble first
    rval = ''
    for i in range(len(s), 0, -2):
        rval += s[i-2:i]
    return rval

def dumpmem(s, addr, wth=16):
    # addr is an integer
    rval = []

    def prntabl(c):
        return chr(c) if c >= 32 and c < 127 else '.'

    def bytegen(s, n):
        # yield 'n' formatted hex bytes and 'n' characters per iteration
        for i in range(0, len(s), wth*2):           # break into lines
            seg = s[i:i+wth*2]
            bytes = []
            chrs  = ''
            for j in range(0, len(seg), 2):         # break into bytes
                bytes.append(seg[j:j+2])
                chrs  += prntabl(int(bytes[-1], 16))
            yield i/2, bytes, chrs

    for n, hexline, chrline in bytegen(s, wth):
        rval.append('0x%08x  %-*s %s' % (addr+n, wth*3, ' '.join(hexline),
                                         chrline))
    return rval

def parse_xml(data):
    # because ElementTree is insane overkill.
    # and yes this version is incomplete.  some things missing:
    #   - text following sub tags
    #   - probably doesn't handle <!DOCTYPE ...> correctly
    # generates lists of tuples with 5 elements per tupple:
    #   (tag, attrs, pre-text, subtree, post-text)

    tags = [t.rstrip().rstrip('>') for t in data.split('<')[1:]]
    root = []

    def parse_tags(tree, tags):
        in_comment = False
        while len(tags) > 0:
            tag = tags[0] #.strip()  if strip helps, xml is malformed
            if tag[0] == '/':
                # unwind recurrsion until matching tag is found
                if  len(tree) > 0 \
                and tag[1:].lower().startswith(tree[-1][0].lower()):
                    tags.pop(0)
                    continue
                return
            elif tag.startswith('!--'):
                in_comment = True;

            tags.pop(0)
            subtree = []
            text = ''
            if tag.find('>') > 0:
                # tag contains text
                tag, text = tag.split('>', 1)

            if tag[-1] == '/':
                tag = tag[:-1]          # standalone tag
            elif in_comment and tag[-2:] == '--':
                tag = tag[:-2]          # standalone comment
                in_comment = False
            else:
                # not a self-ending tag, recurse another level
                parse_tags(subtree, tags)

            # tag contains only attributes
            parts = tag.split()
            tree.append((parts[0], parts[1:], text, subtree, ''))

    try:
        parse_tags(root, tags)
    except:
        Log.write('error parsing xml: %s\n' % traceback.format_exc(), CPerr)

    return root


class GdbClient(asyncore.dispatcher):

    def __init__(self):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect(Host_port)
        self.cmds = []
        self.sbuf = ''
        self.rbuf = ''
        self.rchksm = ''
        self.lastcmd = None
        self.state = None
        self.nthreads = 0
        self._threads = []
        self.current_thread = None      # 1 based
        self.stopped_thread = None      # None = emulator running
        # eventually support all this?
        #self.queue_cmd('qSupported:multiprocess+;xmlRegisters=i386;qRelocInsn+')
        # initiate the startup sequence
        self.queue_cmd('qSupported')

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    def handle_error(self):
        if str(sys.exc_info()[1]).find('[Errno 111]') >= 0:
            Log.write('cannot connect to %s (Connection refused)' %
                        str(Host_port) + ' is qemu running with -s ?\n', CPerr)
        else:
            Log.write('GdbClient exception: %s\n' % traceback.format_exc(), CPerr)

    def writable(self):
        if len(self.sbuf) > 0:
            return True
        if self.state == None and self.lastcmd == None and len(self.cmds) > 0:
            return True
        return False

    def handle_write(self):
        if len(self.cmds) <= 0:
            return
        cmd = self.cmds.pop(0)
        self.lastcmd = cmd
        s = '$' + cmd + '#' + "%02x" % (sum([ord(c) for c in cmd]) & 0xff)
        self.sbuf = s.encode('ascii')
        Log.write('w-- ' + str(self.sbuf) + '\n')
        sent = self.send(self.sbuf)
        self.sbuf = self.sbuf[sent:]

    def queue_cmd(self, cmd):
        self.cmds.append(cmd)

    def handle_read(self):
        data = self.recv(8192).decode('ascii')
        Log.write('r-- ' + data + '\n')
        self.process_read(data)

    def process_read(self, data):
        # two nested state machines here,
        # the 'outside' sm parses $...#..
        # the 'inside' sm collects rbuf and rchksm strings
        # lastcmd remembers the cmd that triggered the current response
        for c in data:
            if self.state == None:
                # state is inactive - we are outside of a msg packet
                if c == '$':
                    self.state = '$'
                    self.rbuf = ''
                    self.rchksm = ''
                    continue
                elif c == '+':
                    #print('msg ok')
                    continue
                elif c == '-':
                    # if over a serial line retransmit might be in order
                    update_status('**** transmission failure ****', CPerr)
                    continue

            # else state is active - we are inside a msg packet

            if self.state == '$':
                if c == '#':
                    self.state = 'chksm0'
                else:
                    # collect characters until checksum
                    self.rbuf += c
                continue

            if self.state == 'chksm0':
                # first checksum character
                self.rchksm += c
                self.state = 'chksm1'
                continue

            if self.state == 'chksm1':
                # second checksum character
                self.rchksm += c
                self.state = None
                # checksum complete, validate
                s = "%02x" % (sum([ord(d) for d in self.rbuf]) & 0xff)
                if s != self.rchksm:
                    update_status('**** warning: recv checksum mismatch **** [%s,%s]' %
                                        (s, self.rchksm), CPerr)
                self.rchksm = ''
                #Log.write('++ state ' + str(self.state) + ' [%s|%s|%s]' % (
                #                       c, self.rbuf, self.rchksm))

                # process rbuf
                if not self.lastcmd or len(self.lastcmd) == 0:
                    update_status('++ rbuf[%s]' % self.rbuf, CPdbg)
                    pass
                elif self.lastcmd == 'qSupported':
                    self.process_supported()
                elif self.lastcmd.startswith('qXfer:features:read:'):
                    self.process_feature_read()
                elif self.lastcmd[:5] in ['?', 's', 'c', 'vCont']:
                    self.process_stop()
                elif self.lastcmd == 'g':
                    self.process_regs()
                elif self.lastcmd[0] == 'm':
                    self.process_mem()
                elif self.lastcmd == 'qC':
                    self.process_currentthread()
                elif self.lastcmd.startswith('Hg'):
                    self.process_currentthread()
                elif self.lastcmd == 'qfThreadInfo':
                    if self.process_threadinfo():
                        self.queue_cmd('qsThreadInfo')
                elif self.lastcmd == 'qsThreadInfo':
                    if self.process_threadinfo():
                        self.queue_cmd('qsThreadInfo')
                else:
                    Log.write('++ rdp response to [%s] not implemented' % (
                                                    self.lastcmd))

                self.lastcmd = None
                self.rbuf = ''
            else:
                update_status('++ stray recv char [%s]' % c, CPerr)

    def process_supported(self):
        Log.write('++ supported: ' + str(self.rbuf.split(';')) + '\n')
        features = self.rbuf.split(';')
        cmds = 0
        for feature in features:
            if feature == 'qXfer:features:read+':
                # sweet, we can actually know what arch we need,
                # ask for the xml
                self.queue_cmd('qXfer:features:read:target.xml:0,ffb')
                cmds += 1

        if cmds == 0:
            # get the machine state now
            self.queue_cmd('?')             # triggers process_stop
        # else let process_feature_read get the machine state

    def process_feature_read(self):
        global Arch_name
        reqfn = self.lastcmd.split(':')[3]
        if reqfn == 'target.xml':
            # got names of xml files available on the target
            tree = parse_xml(self.rbuf)
            #import pprint
            #Log.write(pprint.pformat(tree) + '\n')
            #            +- xml
            #            |     +- !DOCTYPE
            #            |     |     +- target
            #            |     |     |
            files = tree[0][3][0][3][0][3]
            Log.write('target has %d files\n' % len(files))
            # queue them all up
            for tag,attrs,txta,subtree,txtb in files:
                fn = attrs[0].split('"')[1]
                Log.write('++ %s\n' % fn, CPdbg)
                Arch_name = fn.split('-')[0]
                self.queue_cmd('qXfer:features:read:%s:0,ffb' % fn)
            Log.write('\n')
            load_arch_module()
            # then get the machine state
            self.queue_cmd('?')             # triggers process_stop
            return

        # process each of the others files we get
        #with open('foo-' + reqfn, 'w') as fh:
        #    fh.write(self.rbuf + '\n')
        tree = parse_xml(self.rbuf)
        Arch.generate_gspec(tree)

    def process_stop(self):

        #   GDB_SIGNAL_0 = 0,
        #   GDB_SIGNAL_INT = 2,
        #   GDB_SIGNAL_QUIT = 3,
        #   GDB_SIGNAL_TRAP = 5,
        #   GDB_SIGNAL_ABRT = 6,
        #   GDB_SIGNAL_ALRM = 14,
        #   GDB_SIGNAL_IO = 23,
        #   GDB_SIGNAL_XCPU = 24,
        #   GDB_SIGNAL_UNKNOWN = 143

        # we're going to need the arch module now
        load_arch_module()
        self.delete_breakpoints()
        reasons = self.rbuf[3:].split(';')
        st = 'stopped:'
        for reason in reasons:
            if len(reason) > 0:
                n, r = reason.split(':')
                if n == 'thread':
                    th = int(r, 16)
                    self.stopped_thread = th
                    st += ' cpu%d' % (th-1)
                else:
                    st += '  reason=' + reason
        update_status(st, CPnrm)
        # initiate reload of all cpu regs
        self.queue_cmd('qfThreadInfo')
        # refetch all the mem windows.
        # yup, memory fetch requests interlaced with qfThreadInfo!
        # yea, the qemu gdbstub seems to have no problem with this!
        for mem in Mems:
            mem.refetch()

    def process_regs(self):
        global Arch, Arch_name
        if len(self.rbuf) != Arch.gspec_len:
            new_name = Arch.alter_ego(len(self.rbuf))
            if new_name:
                Arch = None
                Arch_name = new_name
                load_arch_module()      # presto changeo ...
                # blank all the cpu windows
                for cpu in Cpus.keys():
                    Cpus[cpu].resize(Arch.cpu_maxy, Arch.cpu_maxx)

            else:
                err = '**** expected %d hex digits for the %s cpu architecture' % (
                                Arch.gspec_len, Arch.name)
                err += ' - but received %d (wrong cpu architecture) ****' % (
                                len(self.rbuf))
                update_status(err, CPerr)
                Log.write(err.replace('-', '****\n****') + '\n', attr=CPerr)
                return

        th = self.current_thread
        i = n = 0
        newregs = {}
        for spec in Arch.gspec:
            if spec[2] <= len(self.rbuf):
                val = lsn2msn(self.rbuf[spec[1]:spec[2]])
                newregs[spec[0]] = int(val, 16)

        # during the first pass, Cpus objects may not have been created
        if not th-1 in Cpus.keys():
            Cpus[th-1] = Cpu(th-1)
        Cpus[th-1].update(newregs)
        #Log.write('++++ newregs ' + str(newregs), CPdbg)
        refresh_all()
        # humm.... would like to fetch about 8 bytes of memory at the ip,
        # but I'm not sure multiple rdp queued commands work asynchronously
        #addr = Arch.compute_ip_address()
        #self.queue_cmd('m%08x,8' % addr)

    def process_mem(self):
        parts = self.lastcmd.split(',')
        addr = int(parts[0].strip()[1:], 16)
        length = int(parts[1], 16)
        st = '++ mem data 0x%x' % addr
        for mem in Mems:
            if mem.addr == addr:        # match data with mem panel
                mem.update(self.rbuf, length)
                st += '  updated!'
        update_status(st, CPdbg)

    def process_threadinfo(self):
        global Reorder_cpus
        if self.rbuf == 'l':
            # no more threads/cpus
            if Reorder_cpus:            # first time?
                reorder_cpu_panels(self.stopped_thread, self.nthreads)
                Reorder_cpus = False
            # restore stopped thread/cpu
            # humm, self.stopped_thread can be None if user steps too fast?
            if self.stopped_thread:
                self.queue_cmd('Hg%d' % self.stopped_thread)
                # FIXME if pgdb can't pick the right source file, setting
                # active obj here will override the users source file
                # selection and piss them off ...
                set_active_object(Cpus[self.stopped_thread-1])
            if Active_src:
                Active_src.center()
            return False        # no more thread/cpu data need to be fetched

        # extract the thread number
        th = int(self.rbuf[1:], 16)
        if not th-1 in Cpus.keys():
            Cpus[th-1] = Cpu(th-1)
        if not th-1 in self._threads:
            self.nthreads += 1
            self._threads.append(th-1)
        self.queue_cmd('Hg%02x' % th)
        self.queue_cmd('g')         # re/populate regs for this cpu
        return True                 # more threads/cpus might exist

    def process_currentthread(self):
        self.current_thread = int(self.lastcmd[2:], 16)

#   def process_selectcpu(self):
#       # 'C' command maybe ...
#       if self.rbuf == "OK":
#           self.current_thread = int(self.lastcmd[2])
#           update_status('current thread now %d' % self.current_thread, CPdbg)

    def single_step(self):
        #self.queue_cmd('s')        # old school gdb
        cmd = 'vCont'
        if Active_cpu:
            # single-step the active cpu
            # NOTE: qemu's gdbstub seems to be pretty cavalier with this
            # command - often I see lots of cpus advance ...
            cmd += ';s:%02x' % (Active_cpu.i+1)
        else:
            # single-step all cpus
            for thread in range(self.nthreads):
                cmd += ';s:%02x' % (thread+1)
        self.queue_cmd(cmd)

    def single_step_all(self):
        cmd = 'vCont'
        # single-step all cpus
        for thread in range(self.nthreads):
            cmd += ';s:%02x' % (thread+1)
        self.queue_cmd(cmd)

    def cont(self):
        cmd = 'vCont'
        if Active_cpu:
            # continue the active cpu
            cmd += ';c:%02x' % (Active_cpu.i+1)
        else:
            # continue all cpus
            for thread in range(self.nthreads):
                cmd += ';c:%02x' % (thread+1)
        self.queue_cmd(cmd)
        self.stopped_thread = None

    def cont_all(self):
        # continue all cpus
        cmd = 'vCont'
        for thread in range(self.nthreads):
            cmd += ';c:%02x' % (thread+1)
        self.queue_cmd(cmd)
        self.stopped_thread = None

    def delete_breakpoints(self):
        global Breakpoints
        for bp in Breakpoints.keys():
            bp = bp.replace('Z', 'z')
            self.queue_cmd(bp)
            update_status('++ deleted %s' % bp, CPdbg)
        Breakpoints = {}

    def delete_watchpoints(self):
        global Watchpoints
        for bp in Watchpoints.keys():
            bp = bp.replace('Z', 'z')
            self.queue_cmd(bp)
            update_status('++ deleted %s' % bp, CPdbg)
        Watchpoints = {}

# ----------------------------------------------------------------------------
# nasm specifics

# easier to blacklist non-opcode keywords than whitelist opcodes ...
# only need to list the nasm keywords that create data.
Non_opcode_keywords = ['db', 'dw', 'dd', 'dq', 'times', 'align']

# ----------------------------------------------------------------------------
# curses TUI support

Fail         = None     # a way to get an error message on the terminal
Stdscr       = None
Active_obj   = None     # the active object (one of Cpu, Mem,or None)
Active_cpu   = None     # the most relevant cpu
Active_mem   = None     # blatant hack to support a single memory window
Active_src   = None
Pin_source   = False    # True if user has pinned a source window
Nextip       = None     # updated when source window scrolls to highlighted ip
Log          = None

Reorder_cpus = True     # True = need to reorder cpu panels
                        # (will occur at end of next qThreadInfo cmd chain)

Cpus  = {}              # all cpu panels
Mems  = []              # all memory panels
Srcs  = []              # all source panels
Helps = []              # all help panels

# inputmode vars
Prompt = None
Text = None

KEY_DOWN   = b'KEY_DOWN'
KEY_LEFT   = b'KEY_LEFT'
KEY_RIGHT  = b'KEY_RIGHT'
KEY_UP     = b'KEY_UP'
KEY_RESIZE = b'KEY_RESIZE'
KEY_PPAGE  = b'KEY_PPAGE'
KEY_NPAGE  = b'KEY_NPAGE'
KEY_HOME   = b'KEY_HOME'

CTRL_DOWN  = b'kDN5'
CTRL_LEFT  = b'kLFT5'
CTRL_RIGHT = b'kRIT5'
CTRL_UP    = b'kUP5'
CTRL_PAGEU = b'kPRV5'
CTRL_PAGED = b'kNXT5'

CPnrm = None
CPhi  = None

def init_colors():
    global CPnrm, CPerr, CPok, CPinfo, CPdbg, CPhi, CPbdr, CPtitle1, CPtitle0
    global CPchg, CPsrc, CPip, CPnip, CPbp, CPtxt
    curses.start_color()
    if curses.has_colors():
        # enable transparent backgrounds and the use of -1 for a bg color
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_RED,     -1)
        curses.init_pair(2, curses.COLOR_GREEN,   -1)
        curses.init_pair(3, curses.COLOR_YELLOW,  -1)
        curses.init_pair(4, curses.COLOR_BLUE,    -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_CYAN,    -1)
        curses.init_pair(7, curses.COLOR_WHITE,   -1)
    else:
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)

    # don't like the colors?  change them here:
    CPnrm    = curses.color_pair(7)
    CPerr    = curses.color_pair(1)
    CPok     = curses.color_pair(2)
    CPinfo   = curses.color_pair(4)
    CPdbg    = curses.color_pair(5)
    CPhi     = curses.color_pair(3)
    CPbdr    = curses.color_pair(2)
    CPtitle1 = curses.color_pair(3)
    CPtitle0 = curses.color_pair(7)
    CPchg    = curses.color_pair(3)
    CPsrc    = curses.color_pair(4)
    CPip     = curses.color_pair(3)
    CPnip    = curses.color_pair(7)
    CPbp     = curses.color_pair(5)
    CPtxt    = curses.color_pair(2)

def ccs(win, y, x, ins, default_attr):
    # convert character string (yea, bad name)
    #
    # ASCII was designed almost 60 years ago for mechanical devices.
    # Our default character set really needs to support things other
    # than form-feed and ring-the-bell.  Color for example ...
    attr = default_attr
    next_attr = default_attr
    outs = ''
    for c in ins:
        if   c == '\a':  next_attr = CPhi
        elif c == '\b':  next_attr = CPinfo
        elif c == '\f':  next_attr = CPok
        elif c == '\r':  next_attr = CPerr
        elif c == '\t':  next_attr = CPnrm
        elif c == '\v':  next_attr = CPdbg
        else:
            outs += c
            continue
        win.addstr(y, x, outs, attr)
        x += len(outs)
        outs = ''
        attr = next_attr
    win.addstr(y, x, outs, attr)


#def stdscr_clear():
#    #Stdscr.erase()
#    Stdscr.move(1, 0)
#    Stdscr.clrtobot()

def ishexdigit(s):
    if len(s) == 0: return False
    return all(c in string.hexdigits for c in s)

def update_status(s=None, attr=CPnrm):
    # a blank string allows the pinned flag to be
    # changed without changing the status message
    global Last_status, Last_status_attr
    h,w = Stdscr.getmaxyx()
    if s:
        Last_status = s + ' ' + '*'*w
        Last_status_attr = attr
    Stdscr.addnstr(0, 0, ['[ ] ','[P] '][Pin_source] + Last_status + '  ',
                                                 w, Last_status_attr)

def refresh_all():
    # from the bottom up
    pnl = curses.panel.bottom_panel()
    while pnl:
        pnl.window().touchwin()
        pnl = pnl.above()

    curses.panel.update_panels()
    curses.doupdate()

def set_active_object(newobj):
    global Active_obj, Active_cpu, Active_mem
    if Active_obj and newobj != Active_obj:
        Active_obj.deactivate_title()
    Active_obj = newobj
    Active_obj.activate_title()
    Active_obj.panel.top()
    if isinstance(newobj, Cpu):
        Active_cpu = newobj
        newobj.locate()
    if isinstance(newobj, Mem):
        Active_mem = newobj
        newobj.refetch()
    refresh_all()

def rotate_active_object():
    global Active_obj
    if Active_obj:
        #Stdscr.addstr(30,0, str('old ' + Active_obj.title).encode('ascii'))
        Active_obj.deactivate_title()
        pnl = Active_obj.panel.below()
        if pnl:
            Active_obj = pnl.userptr()
        else:
            Active_obj = None
    else:
        #Stdscr.addstr(30,0, b'old  none')
        Active_obj = curses.panel.top_panel().userptr()
    if Active_obj:
        Active_obj.activate_title()
        update_status(Active_obj.title, CPnrm)
        #Stdscr.addstr(31,0, str('new ' + Active_obj.title).encode('ascii'))
    else:
        update_status('no active window', CPnrm)
        #Stdscr.addstr(31,0, b'new  none')
    refresh_all()

def deactivate_all():
    global Active_obj
    if Active_obj:
        Active_obj.deactivate_title()
    Active_obj = None

def reorder_cpu_panels(stopped_thread, nthreads):
    global Active_cpu, Active_obj
    if stopped_thread == None:
        return
    # once all cpu panels have been created,
    # this function can place them nicely
    h,w = Stdscr.getmaxyx()
    cw = Cpus[0].w
    for i in range(nthreads-1, -1, -1):
        Cpus[i].rise()
        # if the screen is too narrow, vertically stack cpus.
        # try to leave 15 columns for source display
        if nthreads*2+cw > w-15:
            Cpus[i].move(nthreads+1-i, w-cw)
        else:
            Cpus[i].move(nthreads+1-i, w-cw-nthreads*2+i*2)

def set_breakpoint(text):
    text = text.lower()     # lower needed so we can match strcmp breakpoints
    cmd = 'Z0,%s,1' % text
    if cmd in Breakpoints:
        update_status('breakpoint %s already set' % text, CPhi)
    else:
        Breakpoints[cmd] = True
        update_status('++ setting %s' % cmd, CPdbg)
        Gdbc.queue_cmd(cmd)

def set_and_show_breakpoint(text):
    # TODO: for each srcwin, add a HILITETYP_BP if the breakpoint can be found
    set_breakpoint(text)

def set_watchpoint(text):
    text = text.lower()     # lower needed so we can match strcmp watchpoints
    cmd = 'Z2,%s,1' % text
    if cmd in Watchpoints:
        update_status('watchpoint %s already set' % text, CPhi)
    else:
        Watchpoints[cmd] = True
        update_status('++ setting %s' % cmd, CPdbg)
        Gdbc.queue_cmd(cmd)

def fixup_lookup(label, src):
    for name, offset, segments, fixup in src.codesyms:
        if name == label:
        # and len(set(segments).intersection(set(srcwin.segments))) > 0:
            return fixup #offset
    return None

def dictify_symbols(table):
    # I'm sure there is a really good reason symbol tables are
    # still lists and not dictionaries ...
    rval = {}
    for name, offset, segments, fixup in table:
        rval[name] = offset
    return rval

def locate_src(seg, ip):
    global Active_src, Pin_source
    # if a window is pinned, it, and only it, gets searched
    if  Pin_source \
    and Active_src.segments and seg in Active_src.segments \
    and Active_src.offset <= ip:
        Active_src.ip_search(ip)
        return

    best_offset = None
    best_src = None
    st = 'locating %x:%08x\n' % (seg, ip)
    n = 0
    # next, see if any src files have a starting offset that is below our ip
    src_candidates = []
    for src in Srcs:
        st += 'seg{%s,%d}  ' % (str(src.segments), seg)
        if src.segments and seg in src.segments:
            st += 'ip{%x,%x}  ' % (src.offset, ip)
            # choose src with the nearest offset just below our ip
            if src.offset <= ip:
                src_candidates.append(src)
                n += 1
                if not best_offset or src.offset >= best_offset:
                    best_offset = src.offset
                    best_src = src
                    st += 'yo %s' % os.path.basename(src.fname)
        st += '\n'
    # next, within the list of src candidates, look for a code address that
    # is as close to the ip as possible but still below
    for src in src_candidates:
        for name, off, segs, base in src.codesyms:
            if seg in segs and off <= ip:
                if not best_offset or off >= best_offset:
                    best_offset = off
                    best_src = src
                    st += 'best now lbl=%s in %s\n' % (name,
                                        os.path.basename(src.fname))
    st += 'found %d src files that might work\n' % n
    #Log.write(st, CPdbg)        # this one is frequently useful ...
    # assuming the offset will never be 0
    if best_offset:
        # if we only have one candidate, switch to it.
        # if we have more but the user has one pinned, don't switch.
        # else do the switch.
        if n == 1 or not Pin_source:
            if Pin_source:
                Log.write('source window unpinned\n')
                Pin_source = False
                update_status()
            Active_src = best_src
            Active_src.center()
    else:
        # no source file seems to describe where ip is,
        # how about a generic disassembly Background panel as a default?
        pass

    # finally, search for the current ip in the selected src panel
    if Active_src:
        Active_src.ip_search(ip)


def match_src_file(fname, segs):
    # prevents duplicate loads of source files
    # any segment values can match
    for src in Srcs:
        if src.fname == fname \
        and len(set(src.segments).intersection(set(segs))) > 0:
            return src
    return None

#----------------------------------------------------------
# TUI classes

class Movable_panel(object):
    def __init__(self, h,w, y,x, title):
        sh,sw = Stdscr.getmaxyx()
        if y+h > sh:
            y = sh-h-2
        if x+w > sw:
            x = sw-w-2

        self.y = y
        self.x = x
        self.h = h
        self.w = w
        self.title = title
        self.visible = True
        self.win = curses.newwin(h,w, y,x)
        self.win.erase()
        self.win.attron(CPbdr)
        self.win.box()
        self.win.attron(CPbdr)
        self.win.addstr(0, 1, self.title, CPtitle0)
        self.win.attroff(CPbdr)
        self.panel = curses.panel.new_panel(self.win)
        self.panel.set_userptr(self)

    def re_title(self, attr):
        self.win.addstr(0, 1, self.title, attr)

    def add_strs(self, strs, default_attr):
        # strs are a list of 3 value tuples: (y, x, str)
        for t in strs:
            ccs(self.win, t[0], t[1], t[2], default_attr)

    def activate_title(self):
        self.win.attron(CPtitle1)
        self.re_title(curses.A_REVERSE)
        self.win.attroff(CPtitle1)

    def deactivate_title(self):
        self.win.attron(CPtitle0)
        self.re_title(curses.A_NORMAL)
        self.win.attroff(CPtitle0)

    def rise(self):             # silly python, claims 'raise' for itself
        self.panel.top()

    def lower(self):
        self.panel.bottom()

    def show(self):
        self.panel.show()
        self.visible = True

    def hide(self):
        self.panel.hide()
        self.visible = False

    def resize(self, y, x):
        self.win.resize(y, x)
        self.win.move(1, 0)
        self.win.clrtobot()
        self.win.attron(CPbdr)
        self.win.box()
        self.win.attron(CPbdr)

    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()

    def jog(self, kname):
        y = self.y; x = self.x
        if   kname == CTRL_LEFT:  x -= 1
        elif kname == CTRL_RIGHT: x += 1
        elif kname == CTRL_UP:    y -= 1
        elif kname == CTRL_DOWN:  y += 1
        self.move(y, x)

    def move(self, y, x):
        # really wish I could move panels that are partially off screen
        # but curses just throws up (shrug) - so they appear to freeze
        try:
            self.panel.move(y, x)
            self.y = y; self.x = x
        except:
            #update_status('++ move(%d,%d) failed' % (y, x), CPdbg)
            pass

    def delete(self):
        del self.panel
        del self.win
        del self


class Cpu(Movable_panel):
    def __init__(self, i):
        global Active_cpu, Active_obj
        h,w = Stdscr.getmaxyx()
        Movable_panel.__init__(self, 7,61, i+2,i*3+4, ' cpu%d ' % i)
        self.i = i
        self.regs = {}          # register values are integers
        self.last_ip = None

    def update(self, newregs):

        if Gdbc.stopped_thread and self.i == Gdbc.stopped_thread-1:
            set_active_object(self)

        if Active_obj == self:
            title_attr = curses.A_REVERSE
        else:
            title_attr = curses.A_NORMAL

        strs = Arch.cpu_reg_update(self, newregs)
        self.add_strs(strs, CPnrm)

        # update regs
        for key, val in newregs.items():
            self.regs[key] = val

        if self == Active_cpu:
            self.locate()

        refresh_all()

    def locate(self):
        seg = Arch.get_seg_register(self)
        ip  = Arch.get_ip_register(self)
        if ip:
            locate_src(seg, ip)

    def scroll(self, kname):
        pass

class Mem(Movable_panel):
    def __init__(self, i, addr, count):
        # addr needs to be an int.
        # the gdb rdp docs claim addr can be an expresstion, but with qemu only
        # hex strings work.  and I can only get qemu to return physical memory,
        # no segmented or logical addresses ...
        global Active_mem
        self.count = count if count else 0x40
        self.h = (self.count + 15)//16
        self.w = 77
        h,w = Stdscr.getmaxyx()
        Movable_panel.__init__(self, self.h+2,self.w+2,
                               Gdbc.nthreads+8+i*3,w-self.w-2, ' mem%d ' % i)
        self.i = i
        self.addr = addr
        self._mkcmd()
        Active_mem = self
        self.refetch()

    def _mkcmd(self):
        self.cmd = 'm%x,%x' % (self.addr, self.count)
        self.lines = None

    def update(self, data, length):
        # called by Gdbc when data returns, NOT by keyboard or curses events.
        if data == "E14":
            self.win.addstr(2, 1, "  page fault: part of [%x-%x] memory is not accessible  " % (
                                    self.addr, self.addr+length), CPerr)
        else:
            i = 1
            new_lines = []
            for ln in dumpmem(data, self.addr):
                # has line changed? (sloppy, but its a first cut)
                if not self.lines \
                or len(self.lines) == 0 \
                or self.lines.pop(0) == ln:
                    self.win.addstr(i, 1, ln)
                else:
                    self.win.addstr(i, 1, ln, CPhi)
                new_lines.append(ln)
                i += 1
            self.lines = new_lines
        refresh_all()

    def refetch(self):
        # initiate mem data read
        Gdbc.queue_cmd(self.cmd)

    def scroll(self, kname):
        # don't scroll, instead move the address up/down half a window
        if   kname == CTRL_PAGEU: self.addr -= 0x20
        elif kname == CTRL_PAGED: self.addr += 0x20
        self._mkcmd()
        self.refetch()

    def kill(self):
        global Mems
        Mems.remove(self)
        self.delete()

class Mem_ds(Movable_panel):
    def __init__(self, i, addr, ds_spec, count):
        # addr needs to be an int.
        global Active_mem
        self.count = count if count else 1
        self.ds_spec = ds_spec
        self.w = ds_spec.width
        self.h = ds_spec.height * self.count
        h,w = Stdscr.getmaxyx()
        if self.h > h-5:
            # too many to fit on the screen
            self.count = (h-5)//ds_spec.height
            self.h = ds_spec.height * self.count
        Movable_panel.__init__(self, self.h+2,self.w+2,
                               Gdbc.nthreads+8+i*3,w-self.w-2,
                               ' mem%d %s ' % (i, ds_spec.name))
        self.i = i
        self.addr = addr
        self._mkcmd()
        Active_mem = self
        self.refetch()

    def _mkcmd(self):
        self.cmd = 'm%x,%x' % (self.addr, self.count * self.ds_spec.dlen)
        self.lines = None

    def update(self, data, length):
        # called by Gdbc when data returns, NOT by keyboard or curses events.
        if data == "E14":
            self.win.addstr(2, 1, "  page fault: part of [%x-%x] " % (
                                    self.addr, self.addr+length), CPerr)
            self.win.addstr(2, 2, "  memory is not accessible  ", CPerr)
        else:
            i = 1
            new_lines = []
            addr = self.addr
            # display gdt,ldt,idt entries relative to 0, not the mem addr
            if self.ds_spec.name in ['gdt', 'ldt', 'idt']:
                addr = 0
            for ln in Arch.ds_print(data, self.ds_spec, addr):
                # has line changed?
                if not self.lines \
                or len(self.lines) == 0 \
                or self.lines.pop(0) == ln:
                    self.add_strs([(i, 1, ln)], CPnrm)
                else:
                    self.add_strs([(i, 1, ln)], CPhi)
                new_lines.append(ln)
                i += 1
            self.lines = new_lines
        refresh_all()

    def refetch(self):
        # initiate mem data read
        Gdbc.queue_cmd(self.cmd)

    def scroll(self, kname):
        pass

    def kill(self):
        global Mems
        Mems.remove(self)
        self.delete()

class Logging(Movable_panel):
    def __init__(self):
        self.h = 16
        self.w = 77
        sh,sw = Stdscr.getmaxyx()
        y = 17
        if y+self.h > sh-2:  y = sh - 2 - self.h
        Movable_panel.__init__(self, self.h+2,self.w+2, y,sw-self.w-2, ' log ')
        # bah, can't find anything on prefresh, subpad, or subwin
        self.pad = curses.newpad(1000, self.w-2)
        self.pad.scrollok(True)
        self.scrollback = 0
        self.refresh()

    def refresh(self):
        ph,pw = self.pad.getmaxyx()     # pad height
        wh,ww = self.win.getmaxyx()     # window height
        ch,cw = self.pad.getyx()        # current cursor
        if self.scrollback > ch - wh + 2:
            self.scrollback = ch - wh + 2
        if self.scrollback < 0:
            self.scrollback = 0
        y = ch - wh + 2 - self.scrollback
        if y < 0: y = 0
        self.pad.overwrite(self.win, y,0, 1,1, wh-2,ww-2)

    def write(self, st, attr=CPnrm):
        if attr: self.pad.attron(attr)
        self.pad.addstr(st)
        if attr: self.pad.attroff(attr)
        self.refresh()

    def scroll(self, kname):
        if   kname == CTRL_PAGEU: self.scrollback += (self.h-2)//2
        elif kname == CTRL_PAGED: self.scrollback -= (self.h-2)//2
        self.refresh()

class Help(Movable_panel):
    def __init__(self, text):
        w = 0
        h = 1
        text = text.rstrip()
        for ln in text.split('\n'):
            if len(ln) > w:  w = len(ln)
            h += 1
        w += 1
        self.h = h
        self.w = w
        self.text = text
        sh,sw = Stdscr.getmaxyx()
        y = 0
        if y+h > sh-2:  y = sh - 2 - h
        #Movable_panel.__init__(self, h+2,w+2, y,sw-w-2, ' help ')
        Movable_panel.__init__(self, h+2,w+2, y,0, ' help ')
        self.subwin = self.win.derwin(h,w, 0,1)
        self.subwin.addstr(1, 1, self.text, CPnrm)


class Background_panel(object):
    # Background panels:
    # - completely overlay stdscr (except for one line at the top)
    # - cannot be moved (the panel origin is fixed, but the overlay
    #                   start point is changed to mimic scrolling)
    # - there is only ever one background panel visible at one time
    # - background panels are always at the bottom of the panel stack
    #
    # There are two coordinate systems in effect:
    #   1) the focus point y,x (relative to stdscr 1,0)
    #   2) the pad display origin (point in the pad that maps to stdscr 1,0)
    # The focus point will move only if stdscr is resized.
    # The pad display point moves when the user scrolls a background_panel
    # based object.

    def __init__(self):
        self.pad = None
        self.pady = 0           # pad display origin
        self.padx = 0
        self.maxy = 0
        self.maxx = 0           # don't scroll to the right of this column
        # why 200,300?  well, worst case, a user will start with an 80x 24
        # terminal, run pgdb, and then resize the term window possibly much
        # larger - 200 lines and 300+file_longest_line columns anticipates,
        # (hopefully) the largest screen a user will use within the next
        # 10-20 years.
        self.extra_yx = (200, 300)

    def focus_point(self):
        # return the line number and line offset for the location where
        # search centering and ip reads are done, and return the stdscr
        # h and w while we're at it ...
        sh,sw = Stdscr.getmaxyx()
        return sh, sw, sh // 4 * 3, sw // 4

    def make_pad(self, lines, cols):
        self.maxy = len(lines)
        self.maxx = cols
        # win.overlay(destscr, sy, sx, dy, dx, dh, dw) and win.overwrite()
        # don't handle negative sy,sx values, nor do they handle sy,sx values
        # that extend beyond the pad (libncursesw.so.5.9 tends to dump core).
        # So, add blank lines and columns to the top, bottom, and right
        # sides of pad so the focus point can center on a line at the top or
        # bottom of the source file.
        ey,ex = self.extra_yx
        self.pad = curses.newpad(self.maxy + ey*2 +1, cols + ex +1)
        self.pad.attron(CPsrc)
        fmt = '%-*s' + ' '*ex + '\n'
        for i in range(ey):
            self.pad.addstr(fmt % (cols, ' '))
        for ln in lines:
            self.pad.addstr(fmt % (cols, ln))

    def show(self):
        pass

    def hide(self):
        pass

    def center(self, y=None, x=None):
        # center these pad y,x coords at the focus point
        sh,sw, fy,fx = self.focus_point()
        ey,ex = self.extra_yx

        # translate y,x to pad display origin
        # if y,x are 0 then we don't scroll, just re-overwrite at same place
        if y == None: y = self.pady
        if x == None: x = self.padx

        # clamp the pad display origin so the first and last lines
        # cannot go past the focus point

        if y > ey+self.maxy-fy:
            y = ey+self.maxy-fy

        if y < ey-fy+1:
            y = ey-fy+1

        # keep at least focus-point-width columns visible
        # (however abnormally long lines will distort this)
        if x > self.maxx-fx:  x = self.maxx-fx
        if x < 0:         x = 0;

        self.pady = y
        self.padx = x

        # proper y and x to where we are scrolling have been found,
        # apply additional highlighting before we do the overwrite
        if hasattr(self, 'read_nextip_at_or_after_focus_point'):
            self.read_nextip_at_or_after_focus_point()

        # completely rewrite the pad over stdscr.
        # 1,0 protects the prompt line at the top of stdscr
        self.pad.overwrite(Stdscr, y,x, 1,0, sh-1,sw-1)

    def scroll(self, kname):
        h,w = Stdscr.getmaxyx()
        y = self.pady; x = self.padx
        if   kname == KEY_RIGHT: x += 1
        elif kname == KEY_LEFT:  x -= 1
        elif kname == KEY_DOWN:  y += 1
        elif kname == KEY_UP:    y -= 1
        elif kname == KEY_NPAGE: y += h//2
        elif kname == KEY_PPAGE: y -= h//2
        elif kname == KEY_HOME:  x  = 0
        self.center(y, x)

# Prioritized hilite types (lowest to highest)
# TODO: there will be multiple breakpoints
# the hilite list needs to grow dynamically ...
HILITETYP_BP  = 0       # 4th: breakpoints
HILITETYP_TXT = 1       # 3rd: text search
HILITETYP_NIP = 2       # 2nd: nextip address
HILITETYP_IP  = 3       # 1st: current instruction pointer

class Src(Background_panel):
    # search location parameters
    SP_TXT = 0      # the text for this hilite (may be None)
    SP_LNO = 1      # index into self.lines[]
    SP_STX = 2      # starting x position
    SP_LEN = 3      # length of hilight
    SP_CLR = 3      # hightlight color

    def __init__(self, fname, ftype, segments=None, offset=None):
        # verify fname existence and source file uniqueness before calling
        global Srcs, Active_src
        Background_panel.__init__(self)
        self.fname = fname
        self.ftype = ftype          # file type (nasmlst, objdump, etc.)
        self.lines = []
        self.hilites = self._init_hilites()   # list of highlighted locations
        self.codesyms = []          # [(name, offset, segment_lst, fixup)]
        self.datasyms = []          # [(name, offset, segment_lst, fixup)]
        # ints are used for segment and offset to simplify comparisons
        self.segments = segments    # text segment selectors or frame addresses
        self.offset = offset        # text segment offset address (int)

        Srcs.append(self)

        if file_exists(fname, self.lines):
            # determine needed source panel height and width,
            # and store the source
            cols = 0
            with open(self.fname) as fh:
                for ln in fh.readlines():
                    ln = ln.rstrip()    # remove newline and whitespace
                    # ncurses can't deal with tabs
                    ln = ln.replace('\t', ' ')
                    l = len(ln)
                    if l > cols: cols = l
                    self.lines.append(ln)
                    # do per-line parsing - may find the text segment base
                    # address for this file, or may find text symbols,
                    # these override seg:off values passed in.
                    self.line_parse(ln)

                # remove blanks lines at the end of the file
                #while len(self.lines[-1]) == 0:
                if len(self.lines[-1]) == 0:
                    self.lines[-1] = '-blank-'
        else:
            cols = len(self.lines[0])

        self.make_pad(self.lines, cols)

        # make the first source file visible
        if len(Srcs) == 1 and not Active_src:
            Active_src = self
            self.center()

        off = '%08x' % self.offset if self.offset else 'unset'
        Log.write('loaded  %-20s %-8s %8s:%s\n' % (os.path.basename(fname),
                            self.ftype, str(self.segments), off))

    def line_parse(self, ln):
        if self.ftype == 'nasmlst':
            # if its a nasm .lst file, look for 'section .text start='
            mobj = re.search('section\s*.text\s*start=0x[0-9A-Fa-f]+', ln)
            if mobj:
                if not self.segments:
                    self.segments = [0]
                if not self.offset:
                    self.offset = int(mobj.group().split('=')[-1].strip(), 16)
        #elif self.ftype == 'objdump':
            # for the gcc toolchain, the map file has the .text section origin
            #pass
        elif self.ftype == None:
            # don't know the file type yet, look for clues line by line
            re_objdump = re.search('file format elf', ln)
            if re_objdump:
                self.ftype = 'objdump'
                return
            re_nasmlst = re.search('global *[\w]', ln)
            if re_nasmlst:
                self.ftype = 'nasmlst'
                return

    def _init_hilites(self):
        # create the list of prioritized hilite locations
        rval = []
        rval.append([None, None, 0, 0, CPbp])
        rval.append([None, None, 0, 0, CPtxt])
        rval.append([None, None, 0, 0, CPnip])
        rval.append([None, None, 0, 0, CPip])
        return rval

    def _unhilite(self):
        ey,ex = self.extra_yx
        for txt, lno, startx, xlen, cp in self.hilites:
            if lno:
                self.pad.chgat(ey+lno, startx, xlen, CPsrc)

    def rehilite(self, typ=None, newparms=None):
        # first, do we have something to update?
        if typ and newparms:
            self.hilites[typ] = newparms
        ey,ex = self.extra_yx
        for txt, lno, startx, xlen, cp in self.hilites:
            #Log.write('++ txt(%s) lno(%s) stx(%d) l(%d)\n' % (
            #                       txt, str(lno), startx, xlen), CPdbg)
            if lno:
                self.pad.chgat(ey+lno, startx, xlen, cp)

    def search(self, typ, text=None, eol=None, restart=True, quiet=False):
        # typ - is an index into self.hilites (the thing we are searching for)
        # text - if present, replaces typ's search string
        # eol - delimits the search (don't search past x position in eol)
        # restart - true = search for new thing, false = next thing
        # quiet - true means shut up about not finding text
        #
        # note: HILITETYP_NIP and HILITETYP_BP don't come through here, they
        # are managed by read_nextip_at_or_after_focus_point() and by
        # set_and_show_breakpoint() respectively.

        Log.write('++ src.search [%s] restart=%s\n' % (text, restart))
        # we will center the display of found text at the focus point
        sh,sw, fy,fx = self.focus_point()
        ey,ex = self.extra_yx

        parms = self.hilites[typ]
        if not restart and not parms[Src.SP_TXT]:
            update_status('no previous search term for this window', CPerr)
            return

        # reset previously highlighted text
        self._unhilite()

        # where to start the search
        if parms[Src.SP_LNO]:
            # y,x are source line and position coordinates
            y = parms[Src.SP_LNO]
            x = parms[Src.SP_STX] + 1   # resume search one chr beyond last
        else:
            y = x = 0                   # else start at the top

        # if restart, reset previous search
        if restart:
            parms[Src.SP_LNO] = None
            y = x = 0

        # if new search text, reset search
        if text:
            parms[Src.SP_TXT] = text
            parms[Src.SP_LEN] = len(text)

        for i in [0,1]:             # iterate over lines[] at most twice
            while y < len(self.lines):
                #if eol:
                #    Log.write('++ [%s] %d %s\n' % (parms[Src.SP_TXT], x, str(eol)))
                x = self.lines[y].find(parms[Src.SP_TXT], x, eol)
                if x >= 0:
                    # set highlighted text in the pad
                    # overlay will transfer it to stdscr
                    parms[Src.SP_LNO] = y       # update before center()
                    parms[Src.SP_STX] = x
                    self.rehilite(typ, parms)
                    self.center(ey+y - fy, x - fx)
                    return
                y += 1
                x = 0

            # nothing more found - start over from the top
            parms[Src.SP_LNO] = None
            y = x = 0

        if not quiet:
            update_status(' [%s] not found' % parms[Src.SP_TXT], CPhi)

        self.rehilite(typ, parms)

    def ip_search(self, ip, real_ip=True):
        # customized searches for ip values within each src file type
        hilitetyp = HILITETYP_IP if real_ip else HILITETYP_TXT

        if self.ftype == 'nasmlst':         # 8 digits, uppercase hex
            if ip >= self.offset:
                xx = ' %08X ' % (ip - self.offset)
                Log.write('ip=%08x  xx=%s\n' % (ip, xx))
                self.search(hilitetyp, xx, 16)
                return
        elif self.ftype == 'objdump':
            # find a code symbol, in the current source, below or at our ip
            best = None
            base = 0
            label = None
            for name, offset, segments, fixup in self.codesyms:
                if offset <= ip:
                #and len(set(segments).intersection(set(self.segments))) > 0:
                    #Log.write('++ ip_search cand %s %s:%08x\n' % (name, str(segments), offset))
                    if not best or offset >= best:
                        best = offset
                        base = fixup
                        label = name
            #Log.write('++ best %08x %s\n' % (best, self.fname))
            if best != None:
                # We change tabs to spaces when the source file is loaded
                # so the trailing space in the search below is dependable.
                # But I'm not sure about the leading space, suppose a single
                # C function is longer than 4k bytes of code?  0x1000
                # is the space still there?
                #
                # base is used here instead of best because of the way objdump
                # displays instructions within functions - instruction addreses
                # are displayed relative to the segment base address instead of
                # the the function address.
                xx = ' %x: ' % (ip - base)
                Log.write('ip_search: %s %s\n' % (label, xx))
                # lookup label first, then offset
                self.search(hilitetyp, label, len(label)+12)
                self.search(hilitetyp, xx, 8, restart=False, quiet=True)
                return

    def read_nextip_at_or_after_focus_point(self):
        global Nextip
        sh,sw, fy,fx = self.focus_point()
        ey,ex = self.extra_yx

        self._unhilite()
        parms = None

        # find where the ip is highlighted
        cipy = None
        if self.hilites[HILITETYP_IP][Src.SP_LNO]:
            cipy = self.hilites[HILITETYP_IP][Src.SP_LNO]

        # find the next ip on or below the focus point
        # (convert pad location to source line number)
        start_line = self.pady-ey + fy
        if start_line >= len(self.lines): start_line = len(self.lines)-1
        ip = None
        ipl = 0
        xs = xl = 0
        if self.ftype == 'nasmlst':
            for l in range(start_line, len(self.lines)):
                if cipy and l == cipy:      # avoid the current ip location
                    continue
                # only look at lines that generate addresses
                if len(self.lines[l]) < 40:
                    continue
                ip = self.lines[l][7:15]
                if ishexdigit(ip) == False:
                    ip = None
                    continue
                # check first 3 assembler keywords for non-opcodes
                keywords = self.lines[l][40:].split()[:3]
                if len(keywords) == 0 \
                or len(set(keywords).intersection(set(Non_opcode_keywords))) > 0:
                    ip = None
                    continue
                # found the next valid ip!
                Nextip = '%x' % (self.offset + int(ip , 16))
                ipl = l
                xs = 7
                xl = 8
                break

        elif self.ftype == 'objdump':
            # rewind to find the most recent .text label
            lbln = lbll = None
            for l in range(start_line, 0, -1):
                mobj = re.search('[0-9a-f]* <([\w_]*)>:', self.lines[l])
                if mobj:
                    #print('mobj: %s' % str(mobj.group(1)), file=sys.stderr)
                    lbln = mobj.group(1)
                    lbll = l
                    break

            # or the proper label may be ahead of us ...
            # while there are no code lines, keep looking for a label
            ip = None
            ipl = 0
            for l in range(start_line, len(self.lines)):
                if cipy and l == cipy:      # avoid the current ip location
                    continue
                ln = self.lines[l]
                if len(ln) < 5:
                    continue
                if self.lines[l][4] == ':':
                    ip = self.lines[l][0:4].strip()
                    ipl = l
                    xs = 0
                    xl = 4
                    break
                mobj = re.search('[0-9a-f]* <([\w_]*)>:', self.lines[l])
                if mobj:
                    lbln = mobj.group(1)
                    lbll = l

            # ipl now should point to the first line of code below the focus
            # point and lbll,lbln document the .text label for that line of
            # code, compute the ip for the line of code
            if lbln and ip != None:
                fixup = fixup_lookup(lbln, self)
                if fixup:
                    Nextip = '%x' % (fixup + int(ip, 16))
                    #Log.write('++ nextip=' + Nextip + '\n', CPdbg)

        else:
            update_status('unsupported file type [%s]' % self.ftype, CPhi)

        if ip:
            # FIXME this status msg is nice but fname is often long
            # and the important part (file name) can get cut off
            #update_status('next ip [%s] in %s ' % (Nextip, self.fname), CPdbg)
            parms = self.hilites[HILITETYP_NIP]
            parms[Src.SP_LNO] = ipl
            parms[Src.SP_STX] = xs
            parms[Src.SP_LEN] = xl
        else:
            #update_status('next ip not found', CPdbg)
            pass

        self.rehilite(HILITETYP_NIP, parms)


# ----------------------------------------------------------------------------
# main support

def file_exists(fname, errlst, warning=False):
    if os.path.exists(fname):
        return True
    err = 'cannot find ' + fname
    attr = CPhi if warning else CPerr
    Log.write(err + '\n', attr)
    if errlst != None:
        errlst.append(err)

def dump_symbols(src):
    if len(src.datasyms) > 0:
        Log.write('    data symbols for %s:\n' % os.path.basename(src.fname))
        for sym in src.datasyms:
            Log.write('%12s:%08x %08x %s\n' % (str(sym[2]), sym[1], sym[3], sym[0]))
    else:
        Log.write('    no data symbols for %s\n' % os.path.basename(src.fname))

    if len(src.codesyms) > 0:
        Log.write('    code symbols for %s:\n' % os.path.basename(src.fname))
        for sym in src.codesyms:
            Log.write('%12s:%08x %08x %s\n' % (str(sym[2]), sym[1], sym[3], sym[0]))
    else:
        Log.write('    no code symbols for %s\n' % os.path.basename(src.fname))

# Ok, what is sec_base?
#
# Addresses in .lst files generated by both nasm and objdump start back at
# zero for each new section (.data, .text.startup, etc.).  this makes is
# hard for us to match cpu register values with the source code.  So far
# however, a fixup value can be computed for each symbol while loading .map
# files, and so we store this value along with the symbol for later use.

def load_nasmmap_file(fname, segs, src):
    with open(fname) as fh:
        state = None
        for ln in fh.readlines():
            if ln.find('Section .text') > 0:
                state = 'code-ln1'
                continue
            if ln.find('Section .data') > 0:
                state = 'data-ln1'
                continue

            tokens = ln.split()
            ntokens = len(tokens)
            if ntokens == 3:
                t1, t2, t3 = ln.split()
                if t1 == 'Real':        # special case this one line ...
                    continue
            else:
                continue

            if state and state.endswith('-ln1'):
                # the first symbol gives us the section base address
                sec_base = int(t1, 16)
                state = state[:-4]

            if state == 'code':
                # need to do away with adding src.offset here
                src.codesyms.append((t3, int(t1, 16), segs, sec_base))
            elif state == 'data':
                src.datasyms.append((t3, int(t1, 16), segs, sec_base))

                #Symbols_data.append((t3, int(t1, 16), segs, srcobj, srcobj.offset))
                #Log.write('++ %s %s\n' % (t3, t1))

def load_gccmap_file(fname, segs, file_base):
    if not file_exists(fname, None):
        Src(fname, None, segs, 0)
        return
    # file_base may not be useful - gcc maps use absolute logical addresses
    if file_base == None:  file_base = 0

    srcobj = None
    path = os.path.dirname(fname)
    with open(fname) as fh:
        state = None
        for ln in fh.readlines():
            if len(ln) == 0:
                state = None; srcobj = None
                continue

            tokens = ln.split()
            ntokens = len(tokens)
            if ntokens == 2:
                t1, t2 = ln.split()
                t3 = t4 = ''
            elif ntokens == 4:
                t1, t2, t3, t4 = ln.split()
            else:
                continue

            # a section marker must be processed before a symbol can be added
            if ntokens == 2:
                if state == 'data':
                    #print('data [%s] [%s]\n' % (t2, t1), file=sys.stderr)
                    srcobj.datasyms.append((t2, int(t1, 16), segs, sec_base))
                elif state == 'code':
                    #print('code [%s] [%s]\n' % (t2, t1), file=sys.stderr)
                    srcobj.codesyms.append((t2, int(t1, 16), segs, sec_base))
                continue

            # look for the indented .data and .text section markers
            if ln.startswith(' .data '):
                state = 'data';
                sec_base = 0
            elif ln.startswith(' .text ') or ln.startswith(' .text.startup '):
                lstfname = os.path.join(path, t4.split('.')[0] + '.lst')
                sec_base = int(t2, 16)
                file_offset = int(t2, 16)
                srcobj = match_src_file (lstfname, segs)
                if not srcobj:
                    # we don't know the ftype, let Src() figure it out
                    srcobj = Src(lstfname, None, segs, file_base + file_offset)
                state = 'code'
            elif not ln.startswith('   '):
                # skip other .<section>
                if srcobj: dump_symbols(srcobj)
                state = None; srcobj = None
                sec_base = 0
    if srcobj: dump_symbols(srcobj)


def parse_fname_spec(fname_spec):
    # parse user supplied segments and offset, return fname.
    # each fname can have a list of segments and one (possibly negative) offset
    # -nasmlst fname.lst=0,8:7c00
    offset = None
    if fname_spec.find('=') > 0:
        parts = fname_spec.split('=')
        fname = parts[0]
        segoff = parts[1]
        if segoff.find(':') > 0:
            parts = segoff.split(':')
            segs = parts[0]
            offset = int(parts[1], 16)
        else:
            segs = segoff

        segments = []
        if segs.find(',') > 0:
            for seg in segs.split(','):
                segments.append(int(seg, 16))
        else:
            segments.append(int(segs, 16))
    else:
        # for non-segmented architectures, assume one segment at 0
        segments = [0]
        fname = fname_spec

    return fname, segments, offset

def load_src_file(fname_spec, ftype):
    fname, segments, offset = parse_fname_spec(fname_spec)

    # lst files are directly loaded into src windows
    if ftype in ["nasmlst", "objdump"]:
        srcobj = Src(fname, ftype, segments, offset)

        # look for a nasmmap file that might accompany the lst file
        if ftype == "nasmlst":
            fname = fname.split('.')[0] + '.map'
            if file_exists(fname, None, warning=True):
                load_nasmmap_file(fname, segments, srcobj)
            dump_symbols(srcobj)

    # gcc map files can name multiple lst files
    elif ftype in ["gccmap"]:
        load_gccmap_file(fname, segments, offset)

#---------------------------------------------------------
# inputmode_xxxx functions are passed the current key sym
# and return the next inputmode function to be called.
# this lets us transition between the various input modes
# while using a single keyboard polling loop.

def inputmode_normal(c):
    global Prompt, Text, Pin_source
    global Active_src, Active_cpu, Active_mem, Active_obj

    kn = curses.keyname(c) if c >= 0 else ''
    ch = chr(c) if 31 < c < 128 else 0

    # check for general errors
    if ch and ch in 'nNa' and not Active_src:
        update_status('no active source window', CPhi)
        return inputmode_normal

    if ch and ch in 'q':
        return None
    elif ch and ch in 'Q':
        Gdbc.queue_cmd('k')
        return None
    elif c == 0:                    # ctrl-spacebar
        if Active_obj:
            Active_obj.panel.top()
            #if isinstance(Active_obj, Cpu):
            #    Active_cpu = Active_obj
    elif c == 0x9:                  # tab
        rotate_active_object()
    elif c == 0xa:                  # enter
        if Active_obj:
            set_active_object(Active_obj)       # refetch/relocate etc.
    elif c == 0x1b:                 # esc
        deactivate_all()
        Active_cpu = None
        Active_mem = None
        Active_obj = None
    elif ch and ch in '1234567890':
        if ch == '0': ch = '10'
        if int(ch)-1 < len(Srcs):
            if Active_src == Srcs[int(ch)-1]:
                # Pin source window the second time a number key is pressed
                if not Pin_source:
                    Pin_source = True
                    Log.write('pinned %s\n' % Active_src.fname)
            else:
                if Pin_source:
                    Log.write('source window unpinned\n')
                    Pin_source = False
            #update_status()            -- display fname below handles this

            Active_src = Srcs[int(ch)-1]
            Active_src.center()
            #off = ('%x' % Active_src.offset) if Active_src.offset else 'none'
            #update_status('segments=%s  offset=%s' % (str(Active_src.segments), off), CPdbg)
            update_status(Active_src.fname, CPnrm)
    elif ch and ch in 'aA':
        Text = ''
        Prompt = 'show address: '
        update_status(Prompt + Text, CPnrm)
        return inputmode_address
    elif ch and ch in 'bB':
        Text = ''
        # get a sample bp value from the active source window
        if Nextip:
            Text = Nextip.lstrip('0')
        Prompt = 'set breakpoint: '
        update_status(Prompt + Text, CPnrm)
        return inputmode_breakpoint
    elif ch and ch in 'c':
        Gdbc.cont()
    elif ch and ch in 'C':
        Gdbc.cont_all()
    elif ch and ch in 'hH':
        Helps[0].toggle()
    elif ch and ch in 'jJ':
        if Nextip:
            Text = Nextip.lstrip('0')
            if hexchk(Text):
                set_breakpoint(hexval(Text))
            if ch == 'J':
                Gdbc.cont_all()
            else:
                Gdbc.cont()
        else:
            update_status('next ip is not valid', CPhi)
    elif ch and ch in 'lL':
        Log.toggle()
    elif ch and ch in 'm':
        Text = ''
        Prompt = 'memory address: '
        update_status(Prompt + Text, CPnrm)
        return inputmode_memory
    elif ch and ch in 'M':
        if hasattr(Active_obj, 'kill'):
            mobj = Active_obj
            rotate_active_object()
            mobj.kill()
    elif ch and ch in 'nN':
        Active_src.search(HILITETYP_TXT, restart=False)
    elif ch and ch in 'rR':
        reorder_cpu_panels(Gdbc.stopped_thread, Gdbc.nthreads)
        refresh_all()
    elif ch and ch in 's':
        Gdbc.single_step()
    elif ch and ch in 'S':
        Gdbc.single_step_all()
    elif ch and ch in 'v':
        Gdbc.delete_breakpoints()
        Gdbc.delete_watchpoints()
    elif ch and ch in 'w':
        Text = ''
        Prompt = 'set watchpoint: '
        update_status(Prompt + Text, CPnrm)
        return inputmode_watchpoint
    elif ch and ch in 'x':
        Text = ''
        Prompt = 'modify memory <addr>,<byte><byte>... : '
        update_status(Prompt + Text, CPnrm)
        return inputmode_memwrite
    elif ch and ch in '?/':
        Text = ''
        Prompt = 'text search: '
        update_status(Prompt + Text, CPnrm)
        return inputmode_search
    elif kn in [KEY_DOWN, KEY_UP, KEY_LEFT, KEY_RIGHT,
                KEY_RESIZE, KEY_PPAGE, KEY_NPAGE, KEY_HOME]:
        if Active_src: Active_src.scroll(kn)
    elif kn in [CTRL_DOWN, CTRL_UP, CTRL_LEFT, CTRL_RIGHT]:
        if Active_obj: Active_obj.jog(kn)
    elif kn in [CTRL_PAGEU, CTRL_PAGED]:
        if Active_obj: Active_obj.scroll(kn)
    else:
        update_status('unmapped key [' + str(kn) + '] ' + hex(c), CPdbg)

    return inputmode_normal

def hexchk(v):
    try: int(v, 16); return True
    except: return False

def hexval(v):
    if v.lower().startswith('0x'): v = v[2:]
    return v

def simple_eval(ex, vals):
    # parse a simple aritmetic expression with named variables
    # vals should be a dict of names (data symbols, register names, etc.)
    lst1 = re.split('(\+|-|\*)', ex)
    # rebuild lst validating tokens and replacing with values
    lst2 = []
    for tok in lst1:
        tok = tok.strip()
        if tok in ['+','-','*']:
            lst2.append(tok)
        elif tok in vals:
            lst2.append(vals[tok])
        elif hexchk(tok):
            lst2.append(int(hexval(tok), 16))
        else:
            l = len(lst2)
            er = lst1[l] if len(lst1[l].strip()) > 0 else lst1[l-1:l+2]
            return None, 'error in [%s] at %s' % (ex, er)

    # apply operators in order of precedence
    for op in ['*', '+', '-']:
        while True:
            idx = lst2.index(op) if op in lst2 else None
            if idx:
                if   op == '*':
                    lst2[idx] = lst2[idx-1] * lst2[idx+1]
                elif op == '+':
                    lst2[idx] = lst2[idx-1] + lst2[idx+1]
                elif op == '-':
                    lst2[idx] = lst2[idx-1] - lst2[idx+1]
                lst2.pop(idx+1)
                lst2.pop(idx-1)
            else:
                break

    return lst2[0], None

def inputmode_breakpoint(c):
    global Text

    kn = curses.keyname(c) if c >= 0 else ''
    ch = chr(c) if 31 < c < 128 else 0
    note = '   **** (note: ESC to abort input)'
    if 0 < c < 128:
        #cp = CPnrm if hexchk(Text) else CPerr (was cool)
        if c == 0xa:
            vals = dictify_symbols(Active_src.codesyms)
            addr, st = simple_eval(Text, vals)
            if st:
                update_status(st, CPerr)
            else:
                update_status(' ', CPnrm)
                set_and_show_breakpoint('%x' % addr)
            return inputmode_normal
        elif c == 0x7f:         # back
            Text = Text[:-1]
            update_status(Prompt + Text + note, CPnrm)
        elif c == 0x1b:         # esc
            Helps[1].hide()
            Text = ''
            update_status(' ', CPnrm)
            return inputmode_normal
        elif ch and ch in 'hH':
            Helps[1].toggle()
        elif ch:
            Text += ch
            update_status(Prompt + Text + note, CPnrm)
    elif kn in [KEY_DOWN, KEY_UP, KEY_LEFT, KEY_RIGHT,
                KEY_RESIZE, KEY_PPAGE, KEY_NPAGE, KEY_HOME]:
        if Active_src: Active_src.scroll(kn)
    return inputmode_breakpoint

def inputmode_watchpoint(c):
    global Text

    kn = curses.keyname(c) if c >= 0 else ''
    ch = chr(c) if 31 < c < 128 else 0
    note = '   **** (note: ESC to abort input)'
    if 0 < c < 128:
        #cp = CPnrm if hexchk(Text) else CPerr (was cool)
        if c == 0xa:
            vals = dictify_symbols(Active_src.datasyms)
            addr, st = simple_eval(Text, vals)
            if st:
                update_status(st, CPerr)
            else:
                update_status(' ', CPnrm)
                set_watchpoint('%x' % addr)
            return inputmode_normal
        elif c == 0x7f:         # back
            Text = Text[:-1]
            update_status(Prompt + Text + note, CPnrm)
        elif c == 0x1b:         # esc
            Helps[1].hide()
            Text = ''
            update_status(' ', CPnrm)
            return inputmode_normal
        elif ch and ch in 'hH':
            Helps[1].toggle()
        elif ch:
            Text += ch
            update_status(Prompt + Text + note, CPnrm)
    elif kn in [KEY_DOWN, KEY_UP, KEY_LEFT, KEY_RIGHT,
                KEY_RESIZE, KEY_PPAGE, KEY_NPAGE, KEY_HOME]:
        if Active_src: Active_src.scroll(kn)
    return inputmode_watchpoint

def inputmode_memory(c):
    global Text

    kn = curses.keyname(c) if c >= 0 else ''
    ch = chr(c) if 31 < c < 128 else 0
    note = '   **** (note: ESC to abort input)'
    if not Active_cpu:
        note = '    **** (note: no cpu is active -- ESC to abort input)'
    if 0 < c < 128:
        if c == 0xa:
            if len(Text) == 0:
                update_status(' ', CPnrm)
                return inputmode_normal

            vals = dictify_symbols(Active_src.datasyms)
            if Active_cpu:
                vals.update(Active_cpu.regs)    # merge dicts
            ds_spec = None
            count = None
            if Text.find('@') > 0:
                ds, Text = Text.split('@', 1)
                ds = ds.strip()
                specs = ''
                for spec in Arch.data_structs:
                    if spec.name == ds:
                        ds_spec = spec
                    specs += ' ' + spec.name
                if ds_spec == None:
                    update_status('unknown data structure [%s], pick one of: %s' % (
                                ds, specs), CPerr)
                    return inputmode_normal

            if Text.find(',') > 0:
                Text, count = Text.split(',', 1)
                count = count.strip()
                try:
                    count = int(count, 16)
                except:
                    update_status('invalid count [%s]', CPerr)
                    return inputmode_normal

            addr, st = simple_eval(Text, vals)

            if st:
                update_status(st, CPerr)
                return inputmode_normal
            elif ds_spec:
                mem = Mem_ds(len(Mems), addr, ds_spec, count)
            else:
                mem = Mem(len(Mems), addr, count)
            set_active_object(mem)
            Mems.append(mem)
            return inputmode_normal
        elif ch and ch in 'hH':
            Helps[2].toggle()
        elif c == 0x7f:         # back
            Text = Text[:-1]
            update_status(Prompt + Text + note, CPnrm)
        elif c == 0x1b:         # esc
            Helps[2].hide()
            Text = ''
            update_status(' ', CPnrm)
            return inputmode_normal
        elif ch:
            Text += ch
            update_status(Prompt + Text + note, CPnrm)
    elif kn in [KEY_DOWN, KEY_UP, KEY_LEFT, KEY_RIGHT,
                KEY_RESIZE, KEY_PPAGE, KEY_NPAGE, KEY_HOME]:
        if Active_src: Active_src.scroll(kn)
    return inputmode_memory

def inputmode_search(c):
    global Text

    ch = chr(c) if 31 < c < 128 else 0
    note = '   **** (note: ESC to abort input)'
    if 0 < c < 128:
        if c == 0xa:
            update_status(' ', CPnrm)
            if len(Text) > 0 and Active_src:
                Active_src.search(HILITETYP_TXT, Text)
            return inputmode_normal
        elif c == 0x7f:         # back
            Text = Text[:-1]
            update_status(Prompt + Text + note, CPnrm)
        elif c == 0x1b:         # esc
            Search_str = None
            update_status(' ', CPnrm)
            return inputmode_normal
        elif ch:
            Text += ch
            update_status(Prompt + Text + note, CPnrm)
    return inputmode_search

def inputmode_address(c):
    # a feature with perhaps marginal use.  IFF your .lst file happens to
    # be a monolithic collection of all your source then there is a chance
    # the code addresses will be monotonically increasing and a search for
    # a specific address may work.  ip_search() was designed specifically
    # for instruction pointers but maybe user queries can work too ...
    # hence the 'a' command.
    global Text

    ch = chr(c) if 31 < c < 128 else 0
    note = '   **** (note: ESC to abort input) '
    if 0 < c < 128:
        if c == 0xa:
            # symbols are deliberately not supported here
            # use the text search feature '/'
            addr, st = simple_eval(Text, [])
            if st:
                update_status(st, CPerr)
            else:
                update_status(' ', CPnrm)
                Active_src.ip_search(addr, False)
            return inputmode_normal
        elif c == 0x7f:         # back
            Text = Text[:-1]
            update_status(Prompt + Text + note, CPnrm)
        elif c == 0x1b:         # esc
            Search_str = None
            update_status(' ', CPnrm)
            return inputmode_normal
        elif ch:
            Text += ch
            update_status(Prompt + Text + note, CPnrm)
    return inputmode_address

def inputmode_memwrite(c):
    # hacked in cause I needed it quickly ... no error checking,
    # use the log window to see if you got it right.
    global Text

    ch = chr(c) if 31 < c < 128 else 0
    note = '   **** (note: ESC to abort input) '
    if 0 < c < 128:
        if c == 0xa:
            addr, byts = Text.split(',', 1)
            length = len(byts)//2
            cmd = 'M%s,%x:%s' % (addr, length, byts)
            Gdbc.queue_cmd(cmd)
            return inputmode_normal
        elif c == 0x7f:         # back
            Text = Text[:-1]
            update_status(Prompt + Text + note, CPnrm)
        elif c == 0x1b:         # esc
            Search_str = None
            update_status(' ', CPnrm)
            return inputmode_normal
        elif ch:
            Text += ch
            update_status(Prompt + Text + note, CPnrm)
    return inputmode_memwrite

# ----------------------------------------------------------------------------
# main

def main(stdscr):
    global Stdscr, Log, Helps, Gdbc, Fail
    Stdscr = stdscr

    init_colors()
    update_status(Version, CPnrm)

    try:
        Log = Logging()
    except curses.error:
        Fail = 'terminal window too small: 80x24 minimum'
        return
    Log.write(Version + '\n')

    Helps.append(Help(Help_text_main))
    Helps.append(Help(Help_text_breakpoints))
    Helps.append(Help(Help_text_mem_address))
    #Helps[0].toggle()   # leave Helps[0] up for initiates
    Helps[1].toggle()
    Helps[2].toggle()

    Gdbc = GdbClient()

    # load src files
    for argc in range(1, len(sys.argv)):
        if sys.argv[argc] in ["-nasmlst", "-objdump", "-gccmap"]:
            fname = sys.argv[argc+1]
            load_src_file(fname, sys.argv[argc][1:])

    stdscr.nodelay(1)               # make getch() non-blocking
    stdscr.timeout(100)             # (ms) reduce cpu usage while still
                                    # responding immediately to key strokes
    inputmode = inputmode_normal
    n = 0
    while (inputmode):
        c = stdscr.getch()          # ESC delay is internal (waiting for FN keys)
        if c > -1:
            inputmode = inputmode(c)
        refresh_all()
        asyncore.loop(timeout=0.01, count=4)
        #update_status('++ n = %d' % n, CPdbg)
        n += 1
    stdscr.nodelay(0)               # restore blocking

    h,w = stdscr.getmaxyx()         # attempt to position cursor
    stdscr.move(h-1, 0)             # correctly in previous terminal screen


curses.wrapper(main)

if Fail:
    print(Fail)

