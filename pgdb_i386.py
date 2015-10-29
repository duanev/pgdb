#
# PGDB x86 32bit architecture module
#
# implementation notes:
#   - don't create class objects in this module that are not quickly
#       released by pgdb.py.  the x86 modules get switched out dynamically
#       when qemu switches in and out of 64bit mode!
#
# contributors:
#   djv - Duane Voth
#
# history:
#   2015/10/12 - v0.05 - djv - released

version = "PGDB x86_32 v0.01 2015/10/12"

name = 'i386'

DSfns = None


# The length of the rdp 'g' register dump which is likely not
# the best way to tell which architecture qemu is emulating
gspec_len = 616

# PGDB can switch personalities mid-stream (thanks to module re-load).
# If this architecture knows about an alter ego with a different register
# dump length, return the name of that alter ego and PGDB will switch.

def alter_ego(n):
    if n == 1072:
        return 'x86_64'
    return None


# The 'g' command for gdb's remote debug protocol (rdp)
# returns a long string of hex digits, which are the cpu
# registers all packed together - we have to parse this.
# The following Gspec arrays determine register display
# order, as well as parsing specific register data from
# the gdb cmd response string.

gspec = [
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


#def compute_address(seg, off):
#    # deal with protected mode vs. real mode:
#    # assume seg values below 0x80 are descriptors
#    if seg < 0x80:
#        return off      # FIXME need to lookup descriptor
#    else:
#        return seg * 16 + off

cpu_maxy = 7
cpu_maxx = 61


# Cpu methods

def cpu_reg_update(self, newregs):
    strs = []

    def rdiff(y, x, fmt, rname, newr, oldr):
        new = newr[rname]
        old = oldr[rname] if rname in oldr else new
        attr = '' if new == old else '\a'
        strs.append((y, x, attr + fmt % new))

    # zero row is the title row
    rdiff(0, 10, ' %04x:',      'cs',    newregs, self.regs)
    rdiff(0, 16, '%08x ',       'eip',   newregs, self.regs)
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

    # lol, messy, but cool
    x = newregs['flags']
    fla = '%02x' % (x&0xff) + '%02x' % ((x&0xff00)>>8) + '%02x00' % ((x&0xff0000)>>16)
    flstr = DSfns['ds_print_one'](fla, ds_eflags)[0]
    # so the max possible eflags string is like 53,
    # here I hope that not all flags will be on at the same time
    strs.append((5, 14, '%45s' % flstr))

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

    return strs

def get_seg_register(self):
    if 'cs' in self.regs:
        return self.regs['cs']
    return None

def get_ip_register(self):
    if 'eip' in self.regs:
        return self.regs['eip']
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
    rval += '%x' % self.regs['eip']
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
        self.elements = elements    # list of DSFLD objects
        self.header = hdr           # hdr %fmt or None

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
    DSFLD(0,21,'',[DSBLD(6,6,0xff,0)],
                    [DSVAL(0x60,0x00,' 16bit'),DSVAL(0x60,0x20,' 64bit'),
                     DSVAL(0x60,0x60,' \rerr\r')])
)

#           name,  lname,                  dlen, height, width, hdr, elements
ds_gdt = DS('gdt', 'global descriptor table', 8, 1, 58, '%03x ', _gdt_els)

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

ds_eflags = DS('flags', 'cpu 32bit flags', 4, 1, 53, None, _eflags_els)


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

data_structs = [ds_gdt, ds_tss, ds_eflags]

