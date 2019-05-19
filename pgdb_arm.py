#
# PGDB arm 32bit little-endian architecture module
#
# contributors:
#   djv - Duane Voth
#
# history:
#   2015/10/12 - v0.01 - djv - released
#   2015/10/16 - v0.02 - djv - display cpsr flags
#   2015/12/27 - v0.03 - djv - add cpu modes
#   2019/05/12 - v0.04 - djv - update for qemu 3.1.x (proper feature support)

version = "PGDB arm v0.04 2019/05/12"

name = 'arm'

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
    if name == 'org.gnu.gdb.arm.core':
        for r in xml_tree:
            n = int(r['bitsize']) // 4    # 4 bits per nibble
            gspec.append((r['name'], gspec_idx, gspec_idx+n))
            gspec_idx += n
    else:
        Log.write('## deal with feature "' + name + '" later ...\n')
        #Log.write(pprint.pformat(gspec) + '\n')


spec = {  136: { 'mode':None,  'maxy':7,  'maxx':58, 'gspec':gspec } }


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
    rdiff(0, 10, ' %08x ',    'pc',   newregs, self.regs)
    rdiff(1,  2, ' r0 %08x',  'r0',   newregs, self.regs)
    rdiff(1, 16, ' r1 %08x',  'r1',   newregs, self.regs)
    rdiff(1, 30, ' r2 %08x',  'r2',   newregs, self.regs)
    rdiff(1, 44, ' r3 %08x',  'r3',   newregs, self.regs)
    rdiff(2,  2, ' r4 %08x',  'r4',   newregs, self.regs)
    rdiff(2, 16, ' r5 %08x',  'r5',   newregs, self.regs)
    rdiff(2, 30, ' r6 %08x',  'r6',   newregs, self.regs)
    rdiff(2, 44, ' r7 %08x',  'r7',   newregs, self.regs)
    rdiff(3,  2, ' r8 %08x',  'r8',   newregs, self.regs)
    rdiff(3, 16, ' r9 %08x',  'r9',   newregs, self.regs)
    rdiff(3, 30, 'r10 %08x',  'r10',  newregs, self.regs)
    rdiff(3, 44, 'r11 %08x',  'r11',  newregs, self.regs)
    rdiff(4,  2, 'r12 %08x',  'r12',  newregs, self.regs)
    rdiff(4, 16, ' sp %08x',  'sp',   newregs, self.regs)
    rdiff(4, 30, ' lr %08x',  'lr',   newregs, self.regs)
    rdiff(4, 43, 'cpsr %08x', 'cpsr', newregs, self.regs)

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
    strs.append((5, 14, '%44s' % flstr))

    return strs

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
         DSVAL(0x00000400,0x00000400,' i0'),  DSVAL(0x00000200,0x00000200,' f0'),

         #DSVAL(0x00000100,0x00000100,' thmb'),
         DSVAL(0x0000001f,0x0000001f,'\a sys\t'), DSVAL(0x0000001f,0x0000001e,'\r UND\t'),
         DSVAL(0x0000001f,0x0000001d,'\r UND\t'), DSVAL(0x0000001f,0x0000001c,'\r UND\t'),
         DSVAL(0x0000001f,0x0000001b,'\a und\t'), DSVAL(0x0000001f,0x0000001a,'\r hyp\t'),
         DSVAL(0x0000001f,0x00000019,'\r UND\t'), DSVAL(0x0000001f,0x00000018,'\r UND\t'),
         DSVAL(0x0000001f,0x00000017,'\a abt\t'), DSVAL(0x0000001f,0x00000016,'\r mon\t'),
         DSVAL(0x0000001f,0x00000015,'\r UND\t'), DSVAL(0x0000001f,0x00000014,'\r UND\t'),
         DSVAL(0x0000001f,0x00000013,'\a svc\t'), DSVAL(0x0000001f,0x00000012,' irq'),
         DSVAL(0x0000001f,0x00000011,' fiq',),    DSVAL(0x0000001f,0x00000010,' usr')]),
)

ds_cpsr = DS('cpsr', 'program status register', 4, 1, 44, None, _cpsr_els)

data_structs = [ds_cpsr]

