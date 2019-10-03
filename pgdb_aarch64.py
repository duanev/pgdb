#
# PGDB arm 64bit architecture module
#
# contributors:
#   djv - Duane Voth
#
# history:
#   2015/10/16 - v0.01 - djv - released
#   2015/12/27 - v0.02 - djv - add cpu modes
#   2019/05/12 - v0.03 - djv - update for qemu 3.1.x (proper feature support)
#                            - display all 64bits of registers (forces users
#                              to use terminal windows of at least 90x24)

version = "PGDB aarch64 v0.03 2019/05/12"

name = 'aarch64'

Log = None
DSfns = None

# The 'g' command for gdb's remote debug protocol (rdp)
# returns a long string of hex digits, which are the cpu
# registers all packed together - we have to parse this.
# The following Gspec arrays determine register display
# order, as well as parsing specific register data from
# the gdb cmd response string.

gspec = []
gspec_idx = 0

#import pprint

def generate_gspec(name, xml_tree):
    global gspec, gspec_idx
    if name == 'org.gnu.gdb.aarch64.core':
        for r in xml_tree:
            n = int(r['bitsize']) // 4    # 4 bits per nibble
            gspec.append((r['name'], gspec_idx, gspec_idx+n))
            gspec_idx += n
#    elif name == 'org.gnu.gdb.aarch64.fpu':
#        # <vector id="v2d" type="ieee_double" count="2"/>
#        # <vector id="v2u" type="uint64" count="2"/>
#        for r in xml_tree:
#            Log.write('## implement fpu reg: ' + r['name'] + ' ' + r['bitsize'] + ' later\n')
    else:
        Log.write('## deal with feature "' + name + '" later ...\n')
        #Log.write(pprint.pformat(gspec) + '\n')


# we'd really like to bring up pgdb in an 80x24 terminal minimally, but
# 32 64bit regs really don't fit in 80x24 in any sensible way ... so I'm
# now pushing the problem to the user with a warning message about using
# too small a terminal window. worst case the cpu window is cropped, and
# because of an ncurses problem, we can't move it ...

spec = {  536: { 'mode':None,  'maxy':11,  'maxx':87, 'gspec':gspec } }


# Cpu methods

def cpu_reg_update(self, newregs, mode):
    strs = []

    def rdiff(y, x, fmt, rname, newr, oldr):
        new = newr[rname]
        old = oldr[rname] if rname in oldr else new
        attr = '' if new == old else '\a'
        strs.append((y, x, attr + fmt % new))

    # the zero row is the title row
    # register names have to match what gdb rdp returns in the xml
    rdiff(0, 10, ' %016x ',   'pc',   newregs, self.regs)
    rdiff(1,  2, ' x0 %016x', 'x0',   newregs, self.regs)
    rdiff(1, 23, ' x1 %016x', 'x1',   newregs, self.regs)
    rdiff(1, 44, ' x2 %016x', 'x2',   newregs, self.regs)
    rdiff(1, 65, ' x3 %016x', 'x3',   newregs, self.regs)
    rdiff(2,  2, ' x4 %016x', 'x4',   newregs, self.regs)
    rdiff(2, 23, ' x5 %016x', 'x5',   newregs, self.regs)
    rdiff(2, 44, ' x6 %016x', 'x6',   newregs, self.regs)
    rdiff(2, 65, ' x7 %016x', 'x7',   newregs, self.regs)
    rdiff(3,  2, ' x8 %016x', 'x8',   newregs, self.regs)
    rdiff(3, 23, ' x9 %016x', 'x9',   newregs, self.regs)
    rdiff(3, 44, 'x10 %016x', 'x10',  newregs, self.regs)
    rdiff(3, 65, 'x11 %016x', 'x11',  newregs, self.regs)
    rdiff(4,  2, 'x12 %016x', 'x12',  newregs, self.regs)
    rdiff(4, 23, 'x13 %016x', 'x13',  newregs, self.regs)
    rdiff(4, 44, 'x14 %016x', 'x14',  newregs, self.regs)
    rdiff(4, 65, 'x15 %016x', 'x15',  newregs, self.regs)
    rdiff(5,  2, 'x16 %016x', 'x16',  newregs, self.regs)
    rdiff(5, 23, 'x17 %016x', 'x17',  newregs, self.regs)
    rdiff(5, 44, 'x18 %016x', 'x18',  newregs, self.regs)
    rdiff(5, 65, 'x19 %016x', 'x19',  newregs, self.regs)
    rdiff(6,  2, 'x20 %016x', 'x20',  newregs, self.regs)
    rdiff(6, 23, 'x21 %016x', 'x21',  newregs, self.regs)
    rdiff(6, 44, 'x22 %016x', 'x22',  newregs, self.regs)
    rdiff(6, 65, 'x23 %016x', 'x23',  newregs, self.regs)
    rdiff(7,  2, 'x24 %016x', 'x24',  newregs, self.regs)
    rdiff(7, 23, 'x25 %016x', 'x25',  newregs, self.regs)
    rdiff(7, 44, 'x26 %016x', 'x26',  newregs, self.regs)
    rdiff(7, 65, 'x27 %016x', 'x27',  newregs, self.regs)
    rdiff(8,  2, 'x28 %016x', 'x28',  newregs, self.regs)
    rdiff(8, 23, ' fp %016x', 'x29',  newregs, self.regs)
    rdiff(8, 44, ' lr %016x', 'x30',  newregs, self.regs)
    rdiff(8, 72, 'spsr %08x', 'cpsr', newregs, self.regs)
    rdiff(9,  2, ' sp %016x', 'sp',   newregs, self.regs)

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

    # lol, messy, but cool
    x = newregs['cpsr']
    fla = '%02x' % (x&0xff) + '%02x' % ((x&0xff00)>>8)
    fla += '%02x' % ((x&0xff0000)>>16)
    fla += '%02x' % ((x&0xff000000)>>24)
    flstr = DSfns['ds_print_one'](fla, ds_cpsr)[0]
    strs.append((9, 41, '%44s' % flstr))

    return strs

""" exceptions
#define EXCP_UDEF            1   /* undefined instruction */
#define EXCP_SWI             2   /* software interrupt */
#define EXCP_PREFETCH_ABORT  3
#define EXCP_DATA_ABORT      4
#define EXCP_IRQ             5
#define EXCP_FIQ             6
#define EXCP_BKPT            7
#define EXCP_EXCEPTION_EXIT  8   /* Return from v7M exception.  */
#define EXCP_KERNEL_TRAP     9   /* Jumped to kernel code page.  */
#define EXCP_HVC            11   /* HyperVisor Call */
#define EXCP_HYP_TRAP       12
#define EXCP_SMC            13   /* Secure Monitor Call */
#define EXCP_VIRQ           14
#define EXCP_VFIQ           15
#define EXCP_SEMIHOST       16   /* semihosting call */
#define EXCP_NOCP           17   /* v7M NOCP UsageFault */
#define EXCP_INVSTATE       18   /* v7M INVSTATE UsageFault */
#define EXCP_STKOF          19   /* v8M STKOF UsageFault */
#define EXCP_LAZYFP         20   /* v7M fault during lazy FP stacking */
#define EXCP_LSERR          21   /* v8M LSERR SecureFault */
#define EXCP_UNALIGNED      22   /* v7M UNALIGNED UsageFault */
"""

def get_seg_register(self):
    # for architectures that don't use segments, return either a 0
    # or an overlay number.  Overlays (for our purposes here) have
    # the same definition as segments: ie. a set of address spaces
    # that may overlap.
    return 0

def get_ip_register(self):
    if 'pc' in self.regs:
        return self.regs['pc']
    return None


def get_ip_bpfmt(self):
    # return the current pc formatted for the gdb 'Z0' command
    # no, you are right, its not directly useful (because who wants to
    # set a breakpoint at the current pc?  the emulator is just going
    # to stop in exactly the same place), but it does show the user how
    # to format the value correctly
    rval = '%x' % self.regs['pc']
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

_cpsr_els = (
    DSFLD(0, 0, '_',[DSBLD(0,3,0xffffffff,0)],
        # print the flags left to right
        [DSVAL(0x80000000,0x80000000,'n'),    DSVAL(0x40000000,0x40000000,' z'),
         DSVAL(0x20000000,0x20000000,' c'),   DSVAL(0x10000000,0x10000000,' v'),
         DSVAL(0x08000000,0x08000000,' q'),   DSVAL(0x01000000,0x01000000,' J'),
         DSVAL(0x00080000,0x00080000,' ge3'), DSVAL(0x00040000,0x00040000,' ge2'),
         DSVAL(0x00020000,0x00020000,' ge1'), DSVAL(0x00010000,0x00010000,' ge0'),
         DSVAL(0x00001000,0x00001000,' big'), DSVAL(0x00000800,0x00000800,' a'),
         DSVAL(0x00000400,0x00000400,' i0?'), DSVAL(0x00000200,0x00000200,' d'),
         DSVAL(0x00000100,0x00000100,' a'),   DSVAL(0x00000080,0x00000080,' i'),
         DSVAL(0x00000040,0x00000040,' f'),

         DSVAL(0x0000001f,0x0000001f,'\a sys\t'), DSVAL(0x0000001f,0x0000001e,'\r XXX\t'),
         DSVAL(0x0000001f,0x0000001d,'\r XXX\t'), DSVAL(0x0000001f,0x0000001c,'\r XXX\t'),
         DSVAL(0x0000001f,0x0000001b,'\r und\t'), DSVAL(0x0000001f,0x0000001a,'\b hyp\t'),
         DSVAL(0x0000001f,0x00000019,'\r XXX\t'), DSVAL(0x0000001f,0x00000018,'\r XXX\t'),
         DSVAL(0x0000001f,0x00000017,'\a abt\t'), DSVAL(0x0000001f,0x00000016,'\r XXX\t'),
         DSVAL(0x0000001f,0x00000015,'\r XXX\t'), DSVAL(0x0000001f,0x00000014,'\r XXX\t'),
         DSVAL(0x0000001f,0x00000013,'\a svc\t'), DSVAL(0x0000001f,0x00000012,' irq'),
         DSVAL(0x0000001f,0x00000011,' fiq',),    DSVAL(0x0000001f,0x00000010,' usr'),

         DSVAL(0x0000001f,0x0000000f,'\r xxx\t'), DSVAL(0x0000001f,0x0000000e,'\r xxx\t'),
         DSVAL(0x0000001f,0x0000000d,' el3h'),    DSVAL(0x0000001f,0x0000000c,' el3t'),
         DSVAL(0x0000001f,0x0000000b,'\r xxx\t'), DSVAL(0x0000001f,0x0000000a,'\r xxx\t'),
         DSVAL(0x0000001f,0x00000009,' el2h'),    DSVAL(0x0000001f,0x00000008,' el2t'),
         DSVAL(0x0000001f,0x00000007,'\r xxx\t'), DSVAL(0x0000001f,0x00000006,'\r xxx\t'),
         DSVAL(0x0000001f,0x00000005,' el1h'),    DSVAL(0x0000001f,0x00000004,' el1t'),
         DSVAL(0x0000001f,0x00000003,'\r xxx\t'), DSVAL(0x0000001f,0x00000002,'\r xxx'),
         DSVAL(0x0000001f,0x00000001,'\r xxx',),  DSVAL(0x0000001f,0x00000000,' el0t')]),
)

ds_cpsr = DS('cpsr', 'program status register', 4, 1, 44, None, _cpsr_els)

data_structs = [ds_cpsr]

