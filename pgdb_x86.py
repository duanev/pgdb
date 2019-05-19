#
# PGDB x86 32bit architecture module
#
# implementation notes:
#   - don't create class objects in this module that are not quickly
#       released by pgdb.py.  the x86 modules get switched out dynamically
#       when qemu switches in and out of 64bit mode!
#   - syntax errors in this module can be found by running  $ python pgdb_x86.py
#
# contributors:
#   djv - Duane Voth
#
# history:
#   2015/10/12 - v0.01 - djv - released
#   2015/12/27 - v0.02 - djv - add cpu modes

version = "PGDB x86 v0.02 2015/12/27"

name = 'x86'

Log = None
DSfns = None


# PGDB can perform an alter ego switch mid-stream (thanks to module re-load).
# If this architecture knows about an alter ego with a different register
# dump length, return the name of that alter ego and PGDB will switch.
# x86's multiple cpu modes can however run in different cores simultaneously
# so this module supports all of them.

def alter_ego(n):
    return None


# The 'g' command for gdb's remote debug protocol (rdp)
# returns a long string of hex digits, which are the cpu
# registers all packed together - we have to parse this.
# The following Gspec arrays determine register display
# order, as well as the position (start and end) of
# specific register data from the gdb cmd response string.

gspec16 = [
    # 16 bit mode is a total guess ... it has not been debugged
    ['ax',      0,   4], ['bx',     12,  16], ['cx',      4,   8], ['dx',      8,  12],
    ['di',     28,  32], ['si',     24,  28], ['bp',     20,  24], ['flags',  36,  40],
    ['cs',     40,  44], ['ip',     32,  36], ['ss',     44,  48], ['esp',    16,  20]
]

gspec32 = [
    ['eax',     0,   8], ['ebx',    24,  32], ['ecx',     8,  16], ['edx',    16,  24],
    ['edi',    56,  64], ['esi',    48,  56], ['ebp',    40,  48], ['flags',  72,  80],
    ['cs',     80,  88], ['eip',    64,  72], ['ss',     88,  96], ['esp',    32,  40],
    ['ds',     96, 104], ['es',    104, 112], ['fs',    112, 120], ['gs',    120, 128],
    ['st0',   128, 148], ['st1',   148, 168], ['st2',   168, 188], ['st3',   188, 208],
    ['st4',   208, 228], ['st5',   228, 248], ['st6',   248, 268], ['st7',   268, 288],
    ['fctrl', 288, 296], ['fstat', 296, 304], ['ftag',  304, 312], ['fiseg', 312, 320],
    ['fioff', 320, 328], ['foseg', 328, 336], ['fooff', 336, 344], ['fop',   344, 352],
    ['xmm0',  352, 384], ['xmm1',  384, 416], ['xmm2',  416, 448], ['xmm3',  448, 480],
    ['xmm4',  480, 512], ['xmm5',  512, 544], ['xmm6',  544, 576], ['xmm7',  576, 608],
    ['mxcsr', 608, 616]
]

gspec64 = [
    ['rax',     0,  16], ['rbx',    16,  32], ['rcx',    32,  48], ['rdx',    48,  64],
    ['rsi',    64,  80], ['rdi',    80,  96], ['rbp',    96, 112], ['rsp',   112, 128],
    ['r8',    128, 144], ['r9',    144, 160], ['r10',   160, 176], ['r11',   176, 192],
    ['r12',   192, 208], ['r13',   208, 224], ['r14',   224, 240], ['r15',   240, 256],
    ['rip',   256, 272], ['flags', 272, 280], ['cs',    280, 288], ['ss',    288, 296],
    ['ds',    296, 304], ['es',    304, 312], ['fs',    312, 320], ['gs',    320, 328],
# ok I know I botched the floating point offsets ... and what is 328-392 ?
    ['st0',   392, 402], ['st1',   402, 412], ['st2',   412, 422], ['st3',   422, 432],
    ['st4',   432, 442], ['st5',   442, 452], ['st6',   452, 462], ['st7',   462, 472],
    ['st8',   472, 482], ['st9',   482, 492], ['st10',  492, 502], ['st11',  502, 512],
    ['st12',  512, 522], ['st13',  522, 532], ['st14',  532, 542], ['st15',  542, 552],

    ['xmm0',  552, 584], ['xmm1',  584, 616], ['xmm2',  616, 648], ['xmm3',  648, 680],
    ['xmm4',  680, 712], ['xmm5',  712, 744], ['xmm6',  744, 776], ['xmm7',  776, 808],
    ['xmm8',  808, 840], ['xmm9',  840, 872], ['xmm10', 872, 904], ['xmm11', 904, 936],
    ['xmm12', 936, 968], ['xmm13', 968,1000], ['xmm14',1000,1032], ['xmm15',1032,1064],
    ['mxcsr',1064,1072]
]

spec = {  111: { 'mode':'16b', 'maxy':7,  'maxx':50, 'gspec':gspec16 },
          616: { 'mode':'32b', 'maxy':7,  'maxx':61, 'gspec':gspec32 },
         1072: { 'mode':'64b', 'maxy':11, 'maxx':63, 'gspec':gspec64 }
}


#def compute_address(seg, off):
#    # deal with protected mode vs. real mode:
#    # assume seg values below 0x80 are descriptors
#    if seg < 0x80:
#        return off      # FIXME need to lookup descriptor
#    else:
#        return seg * 16 + off



# Cpu methods

def cpu_reg_update(self, newregs, speclen):
    strs = []
    mode = spec[speclen]['mode']

    def rdiff(y, x, fmt, rname, newr, oldr):
        new = newr[rname]
        old = oldr[rname] if rname in oldr else new
        attr = '' if new == old else '\a'
        strs.append((y, x, attr + fmt % new))

    if self.mode == mode:
        strs.append((0, 10, ' %s ' % mode))
    else:
        strs.append((0, 10, ' \a%s ' % mode))

    if mode == '32b':
        # zero row is the title row
        rdiff(0, 20, ' %04x:',      'cs',    newregs, self.regs)
        rdiff(0, 26, '%08x ',       'eip',   newregs, self.regs)
        rdiff(1,  2, 'eax %08x',    'eax',   newregs, self.regs)
        rdiff(1, 17, 'ebx %08x',    'ebx',   newregs, self.regs)
        rdiff(1, 32, 'ecx %08x',    'ecx',   newregs, self.regs)
        rdiff(1, 47, 'edx %08x',    'edx',   newregs, self.regs)
        rdiff(2,  2, 'edi %08x',    'edi',   newregs, self.regs)
        rdiff(2, 17, 'esi %08x',    'esi',   newregs, self.regs)
        rdiff(2, 32, 'ebp %08x',    'ebp',   newregs, self.regs)
        rdiff(2, 47, 'esp %08x',    'esp',   newregs, self.regs)
        rdiff(3,  3, 'ds     %04x', 'ds',    newregs, self.regs)
        rdiff(3, 18, 'es     %04x', 'es',    newregs, self.regs)
        rdiff(3, 30, 'mxcsr %08x',  'mxcsr', newregs, self.regs)
        rdiff(3, 48, 'ss     %04x', 'ss',    newregs, self.regs)
        rdiff(4,  3, 'fs     %04x', 'fs',    newregs, self.regs)
        rdiff(4, 18, 'gs     %04x', 'gs',    newregs, self.regs)
        rdiff(4, 30, 'fctrl %08x',  'fctrl', newregs, self.regs)
        rdiff(4, 45, 'flags %08x',  'flags', newregs, self.regs)

    elif mode == '64b':
        # I'm not completely happy with this layout ...

        # zero row is the title row
        rdiff(0, 20, ' %04x:',      'cs',    newregs, self.regs)
        rdiff(0, 26, '%016x ',      'rip',   newregs, self.regs)
        rdiff(1,  2, 'rax %016x',   'rax',   newregs, self.regs)
        rdiff(1, 24, 'rbx %016x',   'rbx',   newregs, self.regs)
        rdiff(2,  2, 'rcx %016x',   'rcx',   newregs, self.regs)
        rdiff(2, 24, 'rdx %016x',   'rdx',   newregs, self.regs)
        rdiff(2, 54, 'ds %04x',     'ds',    newregs, self.regs)
        rdiff(3,  2, 'rdi %016x',   'rdi',   newregs, self.regs)
        rdiff(3, 24, 'rsi %016x',   'rsi',   newregs, self.regs)
        rdiff(3, 54, 'es %04x',     'es',    newregs, self.regs)
        rdiff(4,  2, 'rbp %016x',   'rbp',   newregs, self.regs)
        rdiff(4, 24, 'rsp %016x',   'rsp',   newregs, self.regs)
        rdiff(4, 54, 'ss %04x',     'ss',    newregs, self.regs)
        rdiff(5,  2, 'r08 %016x',   'r8',    newregs, self.regs)
        rdiff(5, 24, 'r09 %016x',   'r9',    newregs, self.regs)
        rdiff(5, 54, 'fs %04x',     'fs',    newregs, self.regs)
        rdiff(6,  2, 'r10 %016x',   'r10',   newregs, self.regs)
        rdiff(6, 24, 'r11 %016x',   'r11',   newregs, self.regs)
        rdiff(6, 54, 'gs %04x',     'gs',    newregs, self.regs)
        rdiff(7,  2, 'r12 %016x',   'r12',   newregs, self.regs)
        rdiff(7, 24, 'r13 %016x',   'r13',   newregs, self.regs)
        rdiff(7, 47, 'mxcsr %08x',  'mxcsr', newregs, self.regs)
        rdiff(8,  2, 'r14 %016x',   'r14',   newregs, self.regs)
        rdiff(8, 24, 'r15 %016x',   'r15',   newregs, self.regs)
        rdiff(8, 47, 'flags %08x',  'flags', newregs, self.regs)

    else:
        strs.append((1, 2, 'unknown register set (%d)' % mode))


    # lol, messy, but cool
    x = newregs['flags']
    fla = '%02x' % (x&0xff) + '%02x' % ((x&0xff00)>>8) + '%02x00' % ((x&0xff0000)>>16)
    flstr = DSfns['ds_print_one'](fla, ds_eflags)[0]
    if mode == '32b':
        # so the max possible eflags string is like 53,
        # here I hope that not all flags will be on at the same time
        strs.append((5, 14, '%45s' % flstr))
    elif mode =='64b':
        ## lol, messy, but cool
        #x = newregs['flags']
        #fla = '%02x' % (x&0xff) + '%02x' % ((x&0xff00)>>8) + '%02x00' % ((x&0xff0000)>>16)
        #flstr = DSfns['ds_print_one'](fla, ds_rflags)[0]
        strs.append((9, 16, '%45s' % flstr))
    elif mode == '16b':
        strs[rset].append((5, 14, '%45s' % flstr))


    # TODO: at one point I used this for XMM and ST regs - only displayed the
    #       non-zero regs - but it's all too much - need a slick way to deal
    #       with tons of regs - scroll the cpu windows maybe ... for now,
    #       no floating point or extended "multimedia" regs are displayed.
    # track line length in nibbles displayed
    # always print the first 16 regs, then only non-zero regs
    #    if i < 16 or int(val, 16) != 0:
    #        n += len(val)
    #        if (n > 30):
    #            eol = '\n'
    #            n = 0
    #        else:
    #            eol = ''
    #        rdata += ' %5s' % spec[0] + ' %s' % val + eol
    #    i += 1

    self.mode = mode
    return strs

def get_seg_register(self):
    if 'cs' in self.regs:
        return self.regs['cs']
    return None

def get_ip_register(self):
    if self.mode == '32b':
        if 'eip' in self.regs:
            return self.regs['eip']
    elif self.mode == '64b':
        if 'rip' in self.regs:
            return self.regs['rip']
    elif self.mode == '16b':
        if 'ip' in self.regs:
            return self.regs['ip']
    else:
        Log.write('*** get_ip_register: unknown mode [%s] ***\n' % self.mode)
    return None


def get_ip_bpfmt(self):
    # return the current cs:eip formatted for the gdb 'Z0' command
    # no, you are right, its not directly useful (because who wants to
    # set a breakpoint at the current eip?  the emulator is just going
    # to stop in exactly the same place), but it does show the user how
    # to format the value correctly
    rval = ''
    # not sure if gdb protocol supports segments for breakpoints, might
    # need to convert seg:off to a physical or logical memory address
    #if self.regs['cs']:
    #    rval += '%x' % self.regs['cs']
    if self.mode == 616:
        rval += '%x' % self.regs['eip']
    elif self.mode == 1072:
        rval += '%x' % self.regs['rip']
    return rval.lower()






# ---------------------------------------------------------------------------
# Format Arbitrary Data Structures
#
# sure, this could be an external module i.e. 'import fads', and someone
# will (in some project of theirs) likely break it out, but I won't (see
# my rant in pgdb.py about 'fads').

class DS(object):
    # defines a data structure
    def __init__(self, name, lname, dlen, height, width, hdr, elements):
        self.name = name
        self.lname = lname
        self.dlen = dlen            # ds data length in bytes
        self.height = height        # height of one ds
        self.width = width          # strings will be truncated to this
        self.header = hdr           # hdr %fmt or None
        self.elements = elements    # list of DSFLD objects

class DSFLD(object):
    # defines a data structure field
    # field objects must be sorted for the display, in row then column order
    def __init__(self, y, x, name, build, vals):
        self.y = y                  # display row number
        self.x = x                  # display minimum column number
        self.name = name
        self.build = build          # list of DSBLD objects
        self.vals = vals            # list of DSVAL objects

class DSBLD(object):
    # defines how to build a data structure field from data
    # a list of DSBLD objects are ORed together to build a field
    def __init__(self, firstb, lastb, mask, lshift):
        self.firstb = firstb        # index of first byte
        self.lastb = lastb          # index of last byte
        self.mask = mask            # int
        self.lshift = lshift        # bits to left shift mask/bytes

class DSVAL(object):
    # defines text that identifies a specific field value
    def __init__(self, mask, val, txt):
        self.mask = mask            # field mask
        self.val = val              # value, or -1 for != 0 test
        self.txt = txt              # string to print if match

# ------------------------------------------------
# define the data structures specific to i386

# gdt: intel swdev3a s3.4.5 pg 3-13 fig 3-8
#      code and data:  intel swdev3a s3.4.5.1 pg 3-17
#      tss descriptor: intel swdev3a s7.2.2   pg 7-7
_gdt_els = (
    DSFLD(0, 0,'',[DSBLD(2,3,0xffff,0),DSBLD(4,4,0xff,16),DSBLD(7,7,0xff,24)], []),
    DSFLD(0,10,'',[DSBLD(0,1,0xffff,0),DSBLD(6,6,0x0f,16)], []),
    DSFLD(0,17,'',[DSBLD(5,5,0xff,0)],
                    [DSVAL(0x1f,0x00,' \rres\t'), DSVAL(0x1f,0x08,' \rres\t'),
                     DSVAL(0x1f,0x0a,' \rres\t'), DSVAL(0x1f,0x0d,' \rres\t'),
                     DSVAL(0x80,0x00,' \a!pres\t'),
                     # system types
                     #DSVAL(0x1d,0x01,' tss16'),  DSVAL(0x1f,0x02,' ldt'),
                     #DSVAL(0x1f,0x04,' call16'), DSVAL(0x1f,0x05,' taskg'),
                     #DSVAL(0x1f,0x06,' intr16'), DSVAL(0x1f,0x07,' trap16'),
                     #DSVAL(0x1d,0x09,' tss'),    DSVAL(0x1f,0x0c,' call'),
                     #DSVAL(0x1f,0x0e,' intr'),   DSVAL(0x1f,0x0f,' trap'),

                     DSVAL(0x1f,0x01,' tss16'),    DSVAL(0x1f,0x02,' ldt'),
                     DSVAL(0x1f,0x03,' tss16(b)'), DSVAL(0x1f,0x04,' call16'),
                     DSVAL(0x1f,0x05,' taskg'),    DSVAL(0x1f,0x06,' intr16'),
                     DSVAL(0x1f,0x07,' trap16'),   DSVAL(0x1f,0x09,' tss'),
                     DSVAL(0x1f,0x0b,' tss(b)'),   DSVAL(0x1f,0x0c,' call'),
                     DSVAL(0x1f,0x0e,' intr'),     DSVAL(0x1f,0x0f,' trap'),

                     # non system types
                     DSVAL(0x18,0x10,' data'), DSVAL(0x18,0x18,' code'),
                     DSVAL(0x1a,0x10,' r/o'),  DSVAL(0x1a,0x12,' r/w'),
                     DSVAL(0x1a,0x18,' e/o'),  DSVAL(0x1a,0x1a,' e/r'),
                     DSVAL(0x11,0x11,' accessed')]),
    DSFLD(0,21,'',[DSBLD(6,6,0xff,0)],
                    [DSVAL(0x60,0x00,' 16bit'),DSVAL(0x60,0x20,' 64bit'),
                     DSVAL(0x60,0x60,' \rerr\r')])
)

#           name,  lname,                  dlen, height, width, hdr, elements
ds_gdt = DS('gdt', '32 bit global descriptor table', 8, 1, 58, '%03x ', _gdt_els)

# tss: intel swdev3a s7.2.1 pg 7-5
_tss_els = (
    DSFLD( 0, 2,   'ss0 ',[DSBLD(  8,  9,    0xffff,0)],[]),
    DSFLD( 0, 0,   '_res',[DSBLD( 10, 11,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rss0 reserved!')]),
    DSFLD( 0,12,  'esp0 ',[DSBLD(  4,  7,0xffffffff,0)],[]),
    DSFLD( 1, 2,   'ss1 ',[DSBLD( 16, 17,    0xffff,0)],[]),
    DSFLD( 1, 0,   '_res',[DSBLD( 18, 19,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rss1 reserved!')]),
    DSFLD( 1,12,  'esp1 ',[DSBLD( 12, 15,0xffffffff,0)],[]),
    DSFLD( 2, 2,   'ss2 ',[DSBLD( 24, 25,    0xffff,0)],[]),
    DSFLD( 2, 0,   '_res',[DSBLD( 26, 27,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rss1 reserved!')]),
    DSFLD( 2,12,  'esp2 ',[DSBLD( 20, 23,0xffffffff,0)],[]),
    DSFLD( 3, 2,   'cr3 ',[DSBLD( 28, 31,0xffffffff,0)],[]),
    DSFLD( 3,16,   'flg ',[DSBLD( 36, 39,0xffffffff,0)],[]),
    DSFLD( 4, 2,   'eax ',[DSBLD( 40, 43,0xffffffff,0)],[]),
    DSFLD( 4,16,   'ecx ',[DSBLD( 44, 47,0xffffffff,0)],[]),
    DSFLD( 5, 2,   'edx ',[DSBLD( 48, 51,0xffffffff,0)],[]),
    DSFLD( 5,16,   'ebx ',[DSBLD( 52, 55,0xffffffff,0)],[]),
    DSFLD( 6, 3,    'cs ',[DSBLD( 76, 77,    0xffff,0)],[]),
    DSFLD( 6, 0,   '_res',[DSBLD( 78, 79,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rcs reserved!')]),
    DSFLD( 6,12,   'eip ',[DSBLD( 32, 35,0xffffffff,0)],[]),
    DSFLD( 7, 3,    'ss ',[DSBLD( 80, 81,    0xffff,0)],[]),
    DSFLD( 7, 0,   '_res',[DSBLD( 82, 83,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rss reserved!')]),
    DSFLD( 7,12,   'esp ',[DSBLD( 56, 59,0xffffffff,0)],[]),
    DSFLD( 8,12,   'ebp ',[DSBLD( 60, 63,0xffffffff,0)],[]),
    DSFLD( 9, 3,    'es ',[DSBLD( 72, 73,    0xffff,0)],[]),
    DSFLD( 9, 0,   '_res',[DSBLD( 74, 75,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \res reserved!')]),
    DSFLD( 9,12,   'esi ',[DSBLD( 64, 67,0xffffffff,0)],[]),
    DSFLD(10, 3,    'ds ',[DSBLD( 84, 85,    0xffff,0)],[]),
    DSFLD(10, 0,   '_res',[DSBLD( 86, 87,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rds reserved!')]),
    DSFLD(10,12,   'edi ',[DSBLD( 68, 71,0xffffffff,0)],[]),
    DSFLD(11, 3,    'fs ',[DSBLD( 88, 89,    0xffff,0)],[]),
    DSFLD(11, 0,   '_res',[DSBLD( 90, 91,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rfs reserved!')]),
    DSFLD(11,20,   'ldt ',[DSBLD( 96, 97,    0xffff,0)],[]),
    DSFLD(11, 0,   '_res',[DSBLD( 98, 99,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rldt reserved!')]),
    DSFLD(12, 3,    'gs ',[DSBLD( 92, 93,    0xffff,0)],[]),
    DSFLD(12, 0,   '_res',[DSBLD( 94, 95,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rgs reserved!')]),
    DSFLD(12,19,  'link ',[DSBLD(  0,  1,    0xffff,0)],[]),
    DSFLD(12, 0,   '_res',[DSBLD(  2,  3,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rlink reserved!')]),
    DSFLD(13, 0, 'iomap ',[DSBLD(102,103,    0xffff,0)],[]),
    DSFLD(13, 0,      '_',[DSBLD(100,100,       0x1,0)],
                                [DSVAL(0x1,0x1,' \vdbg trap')]),
    DSFLD(13, 0,      '_',[DSBLD(100,100,    0xfffe,0)],
                                [DSVAL(0xfffe,-1,' \rt reserved!')])
)

ds_tss = DS('tss', 'task state', 104, 15, 30, '\b---- tss @ 0x%x', _tss_els)


# eflags: intel swdev1 s3.4.3  pg 3-21 fig 3-8
_eflags_els = (
    DSFLD(0, 0, '_',[DSBLD(0,2,0xffffff,0)],
        # print the flags left to right
        [DSVAL(0x200000,0x200000,'id'),
         DSVAL(0x100000,0x100000,' vp'),  DSVAL(0x080000,0x080000,' vi'),
         DSVAL(0x040000,0x040000,' ac'),  DSVAL(0x020000,0x020000,' v8'),
         DSVAL(0x010000,0x010000,' r'),   DSVAL(0x004000,0x004000,' nt'),
         DSVAL(0x003000,0x001000,' io1'),
         DSVAL(0x003000,0x002000,' io2'), DSVAL(0x003000,0x003000,' io3'),

         DSVAL(0x000800,0x000800,' o'),
         DSVAL(0x000400,0x000400,' d'), DSVAL(0x000200,0x000200,' i'),
         DSVAL(0x000100,0x000100,' t'), DSVAL(0x000080,0x000080,' s'),
         DSVAL(0x000040,0x000040,' z'), DSVAL(0x000010,0x000010,' a'),
         DSVAL(0x000004,0x000004,' p'), DSVAL(0x000001,0x000001,' c')]),
)

ds_eflags = DS('flags', '32 bit cpu flags', 4, 1, 53, None, _eflags_els)


# ------------------------------------------------
# define the data structures specific to x86_64

# gdt: intel swdev3a s3.4.5 pg 3-13 fig 3-8
#      code and data:  intel swdev3a s3.4.5.1 pg 3-17
#      tss descriptor: intel swdev3a s7.2.2   pg 7-7
_gdt64_els = (
    DSFLD(0, 0,'',[DSBLD(2,3,0xffff,0),DSBLD(4,4,0xff,16),
                   DSBLD(7,7,0xff,24), DSBLD(8,16,0xffffffff,32)], []),
    DSFLD(0,18,'',[DSBLD(0,1,0xffff,0),DSBLD(6,6,0x0f,16)], []),
    DSFLD(0,25,'',[DSBLD(5,5,0xff,0)],
                    [DSVAL(0x1f,0x00,' \rres\t'), DSVAL(0x1f,0x08,' \rres\t'),
                     DSVAL(0x1f,0x0a,' \rres\t'), DSVAL(0x1f,0x0d,' \rres\t'),
                     DSVAL(0x80,0x00,' \a!pres\t'),
                     # system types
                     DSVAL(0x1d,0x01,' tss16'),  DSVAL(0x1f,0x02,' ldt'),
                     DSVAL(0x1f,0x04,' call16'), DSVAL(0x1f,0x05,' taskg'),
                     DSVAL(0x1f,0x06,' intr16'), DSVAL(0x1f,0x07,' trap16'),
                     DSVAL(0x1d,0x09,' tss'),    DSVAL(0x1f,0x0c,' call'),
                     DSVAL(0x1f,0x0e,' intr'),   DSVAL(0x1f,0x0f,' trap'),
                     # non system types
                     DSVAL(0x18,0x10,' data'), DSVAL(0x18,0x18,' code'),
                     DSVAL(0x1a,0x10,' r/o'),  DSVAL(0x1a,0x12,' r/w'),
                     DSVAL(0x1a,0x18,' e/o'),  DSVAL(0x1a,0x1a,' e/r'),
                     DSVAL(0x11,0x11,' accessed')]),
    DSFLD(0,29,'',[DSBLD(6,6,0xff,0)],
                    [DSVAL(0x60,0x00,' 16bit'),DSVAL(0x60,0x20,' 64bit')])
)

ds_gdt64 = DS('gdt64', '64 bit global descriptor table', 16, 1, 62, '%03x ', _gdt64_els)

# tss: intel swdev3a s7.2.1 pg 7-5
_tss_els = (
    DSFLD( 0, 2,   'ss0 ',[DSBLD(  8,  9,    0xffff,0)],[]),
    DSFLD( 0, 0,   '_res',[DSBLD( 10, 11,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rss0 reserved!')]),
    DSFLD( 0,12,  'esp0 ',[DSBLD(  4,  7,0xffffffff,0)],[]),
    DSFLD( 1, 2,   'ss1 ',[DSBLD( 16, 17,    0xffff,0)],[]),
    DSFLD( 1, 0,   '_res',[DSBLD( 18, 19,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rss1 reserved!')]),
    DSFLD( 1,12,  'esp1 ',[DSBLD( 12, 15,0xffffffff,0)],[]),
    DSFLD( 2, 2,   'ss2 ',[DSBLD( 24, 25,    0xffff,0)],[]),
    DSFLD( 2, 0,   '_res',[DSBLD( 26, 27,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rss1 reserved!')]),
    DSFLD( 2,12,  'esp2 ',[DSBLD( 20, 23,0xffffffff,0)],[]),
    DSFLD( 3, 2,   'cr3 ',[DSBLD( 28, 31,0xffffffff,0)],[]),
    DSFLD( 3,16,   'flg ',[DSBLD( 36, 39,0xffffffff,0)],[]),
    DSFLD( 4, 2,   'eax ',[DSBLD( 40, 43,0xffffffff,0)],[]),
    DSFLD( 4,16,   'ecx ',[DSBLD( 44, 47,0xffffffff,0)],[]),
    DSFLD( 5, 2,   'edx ',[DSBLD( 48, 51,0xffffffff,0)],[]),
    DSFLD( 5,16,   'ebx ',[DSBLD( 52, 55,0xffffffff,0)],[]),
    DSFLD( 6, 3,    'cs ',[DSBLD( 76, 77,    0xffff,0)],[]),
    DSFLD( 6, 0,   '_res',[DSBLD( 78, 79,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rcs reserved!')]),
    DSFLD( 6,12,   'eip ',[DSBLD( 32, 35,0xffffffff,0)],[]),
    DSFLD( 7, 3,    'ss ',[DSBLD( 80, 81,    0xffff,0)],[]),
    DSFLD( 7, 0,   '_res',[DSBLD( 82, 83,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rss reserved!')]),
    DSFLD( 7,12,   'esp ',[DSBLD( 56, 59,0xffffffff,0)],[]),
    DSFLD( 8,12,   'ebp ',[DSBLD( 60, 63,0xffffffff,0)],[]),
    DSFLD( 9, 3,    'es ',[DSBLD( 72, 73,    0xffff,0)],[]),
    DSFLD( 9, 0,   '_res',[DSBLD( 74, 75,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \res reserved!')]),
    DSFLD( 9,12,   'esi ',[DSBLD( 64, 67,0xffffffff,0)],[]),
    DSFLD(10, 3,    'ds ',[DSBLD( 84, 85,    0xffff,0)],[]),
    DSFLD(10, 0,   '_res',[DSBLD( 86, 87,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rds reserved!')]),
    DSFLD(10,12,   'edi ',[DSBLD( 68, 71,0xffffffff,0)],[]),
    DSFLD(11, 3,    'fs ',[DSBLD( 88, 89,    0xffff,0)],[]),
    DSFLD(11, 0,   '_res',[DSBLD( 90, 91,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rfs reserved!')]),
    DSFLD(11,20,   'ldt ',[DSBLD( 96, 97,    0xffff,0)],[]),
    DSFLD(11, 0,   '_res',[DSBLD( 98, 99,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rldt reserved!')]),
    DSFLD(12, 3,    'gs ',[DSBLD( 92, 93,    0xffff,0)],[]),
    DSFLD(12, 0,   '_res',[DSBLD( 94, 95,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rgs reserved!')]),
    DSFLD(12,19,  'link ',[DSBLD(  0,  1,    0xffff,0)],[]),
    DSFLD(12, 0,   '_res',[DSBLD(  2,  3,    0xffff,0)],
                                [DSVAL(0xffff,-1,' \rlink reserved!')]),
    DSFLD(13, 0, 'iomap ',[DSBLD(102,103,    0xffff,0)],[]),
    DSFLD(13, 0,      '_',[DSBLD(100,100,       0x1,0)],
                                [DSVAL(0x1,0x1,' \vdbg trap')]),
    DSFLD(13, 0,      '_',[DSBLD(100,100,    0xfffe,0)],
                                [DSVAL(0xfffe,-1,' \rt reserved!')])
)

ds_tss = DS('tss', '32 bit task state', 104, 15, 30, '\b---- tss @ 0x%x', _tss_els)


# rflags: intel swdev1 s3.4.3  pg 3-21 fig 3-8
_rflags_els = (
    DSFLD(0, 0, '_',[DSBLD(0,2,0xffffff,0)],
        # print the flags left to right
        [DSVAL(0x200000,0x200000,'id'),
         DSVAL(0x100000,0x100000,' vp'),  DSVAL(0x080000,0x080000,' vi'),
         DSVAL(0x040000,0x040000,' ac'),  DSVAL(0x020000,0x020000,' v8'),
         DSVAL(0x010000,0x010000,' r'),   DSVAL(0x004000,0x004000,' nt'),
         DSVAL(0x003000,0x001000,' io1'),
         DSVAL(0x003000,0x002000,' io2'), DSVAL(0x003000,0x003000,' io3'),

         DSVAL(0x000800,0x000800,' o'),
         DSVAL(0x000400,0x000400,' d'), DSVAL(0x000200,0x000200,' i'),
         DSVAL(0x000100,0x000100,' t'), DSVAL(0x000080,0x000080,' s'),
         DSVAL(0x000040,0x000040,' z'), DSVAL(0x000010,0x000010,' a'),
         DSVAL(0x000004,0x000004,' p'), DSVAL(0x000001,0x000001,' c')]),
)

ds_rflags = DS('flags64', '64 bit cpu flags', 4, 1, 45, None, _rflags_els)


# sample_gdt = "0000000000000000ffff0000009acf00ffff00000093cf00ff1f0010009300009f0f00800b930000ffff0000009a0f00ffff000000920f006800808d00890000"

# sample_tss = "00000000e01f0000100000000000000000000000000000000000000000300000d8004000000000000000000000000000000000000000000000204000000000000000000000000000170000000f000000170000011700000000000000000000004b00010000000000000000000000000000000000000000000000000000000000"

# if __name__ == "__main__":
#     # example: multiple gdt entries
#     loop_offset = 0     # in bytes
#     while loop_offset*2 < len(sample_gdt):
#         # break data into descriptor size chunks
#         data = sample_gdt[loop_offset*2:(loop_offset+ds_gdt.dlen)*2]
#         for ln in ds_print_one(data, ds_gdt):
#             print(ln)
#         loop_offset += ds_gdt.dlen
# 
#     # example: one tss
#     for ln in ds_print_one(sample_tss, ds_tss):
#         print(ln)

data_structs = [ds_gdt, ds_gdt64, ds_tss, ds_eflags, ds_rflags]

