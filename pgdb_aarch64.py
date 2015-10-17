#
# PGDB arm 64bit architecture module
#
# contributors:
#   djv - Duane Voth
#
# history:
#   2015/10/16 - v0.01 - djv - released

version = "PGDB aarch64 v0.01 2015/10/16"

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

def generate_gspec(xml_tree):
    global gspec, gspec_idx
    #Log.write(pprint.pformat(xml_tree) + '\n')
    #                   +- xml
    #                   |     +- !DOCTYPE
    #                   |     |     +- feature
    #                   |     |     |
    features = xml_tree[0][3][1][3][0][3]
    for feature in features:
        if feature[0] == 'reg':
            attrs = feature[1]
            rname = attrs[0].split('"')[1]
            n = int(attrs[1].split('"')[1]) // 4    # 4 bits per nibble
            gspec.append((rname, gspec_idx, gspec_idx+n))
            gspec_idx += n
    #Log.write(pprint.pformat(gspec) + '\n')


# The length of the rdp 'g' register dump which is likely not
# the best way to tell which architecture qemu is emulating
gspec_len = 536


# ok, THIS is a challenging register display format!  we'd really like
# to bring up pgdb in an 80x24 terminal minimally, but 32 64bit regs
# really don't fit in 80x24 in any sensible way ... so I'm lopping off
# the two top nibbles - thats right, I'm only displaying 56 bits of each
# register! (except the pc gets all 64)  If this doesn't work then cpu_maxx
# will have to go to 87 and for an 80x24 terminal the pgdb cpu windows will
# be off the screen to the right AND locked in place (cause thats what
# curses does to panels that are partially off the screen, it currently
# refuses to allow them to be moved).  Somewhere we'll have to tell users
# that they need to use minimally a 90x24 terminal to start pgdb if they
# want the cpu windows to be movable.
cpu_maxy = 11
cpu_maxx = 79

# Cpu methods

def cpu_reg_update(self, newregs):
    strs = []

    def rdiff(y, x, fmt, rname, newr, oldr):
        new = newr[rname]
        old = oldr[rname] if rname in oldr else new
        attr = '' if new == old else '\a'
        strs.append((y, x, attr + fmt % new))

    # the zero row is the title row
    # register names have to match what gdb rdp returns in the xml
    rdiff(0, 10, ' %016x ',   'pc',   newregs, self.regs)
    rdiff(1,  2, ' x0 %014x', 'x0',   newregs, self.regs)
    rdiff(1, 21, ' x1 %014x', 'x1',   newregs, self.regs)
    rdiff(1, 40, ' x2 %014x', 'x2',   newregs, self.regs)
    rdiff(1, 59, ' x3 %014x', 'x3',   newregs, self.regs)
    rdiff(2,  2, ' x4 %014x', 'x4',   newregs, self.regs)
    rdiff(2, 21, ' x5 %014x', 'x5',   newregs, self.regs)
    rdiff(2, 40, ' x6 %014x', 'x6',   newregs, self.regs)
    rdiff(2, 59, ' x7 %014x', 'x7',   newregs, self.regs)
    rdiff(3,  2, ' x8 %014x', 'x8',   newregs, self.regs)
    rdiff(3, 21, ' x9 %014x', 'x9',   newregs, self.regs)
    rdiff(3, 40, 'x10 %014x', 'x10',  newregs, self.regs)
    rdiff(3, 59, 'x11 %014x', 'x11',  newregs, self.regs)
    rdiff(4,  2, 'x12 %014x', 'x12',  newregs, self.regs)
    rdiff(4, 21, 'x13 %014x', 'x13',  newregs, self.regs)
    rdiff(4, 40, 'x14 %014x', 'x14',  newregs, self.regs)
    rdiff(4, 59, 'x15 %014x', 'x15',  newregs, self.regs)
    rdiff(5,  2, 'x16 %014x', 'x16',  newregs, self.regs)
    rdiff(5, 21, 'x17 %014x', 'x17',  newregs, self.regs)
    rdiff(5, 40, 'x18 %014x', 'x18',  newregs, self.regs)
    rdiff(5, 59, 'x19 %014x', 'x19',  newregs, self.regs)
    rdiff(6,  2, 'x20 %014x', 'x20',  newregs, self.regs)
    rdiff(6, 21, 'x21 %014x', 'x21',  newregs, self.regs)
    rdiff(6, 40, 'x22 %014x', 'x22',  newregs, self.regs)
    rdiff(6, 59, 'x23 %014x', 'x23',  newregs, self.regs)
    rdiff(7,  2, 'x24 %014x', 'x24',  newregs, self.regs)
    rdiff(7, 21, 'x25 %014x', 'x25',  newregs, self.regs)
    rdiff(7, 40, 'x26 %014x', 'x26',  newregs, self.regs)
    rdiff(7, 59, 'x27 %014x', 'x27',  newregs, self.regs)
    rdiff(8,  2, 'x28 %014x', 'x28',  newregs, self.regs)
    rdiff(8, 21, 'x29 %014x', 'x29',  newregs, self.regs)
    rdiff(8, 40, 'x30 %014x', 'x30',  newregs, self.regs)
    rdiff(8, 64, 'cpsr %08x', 'cpsr', newregs, self.regs)

    rdiff(9,  2, ' sp %016x', 'sp',   newregs, self.regs)
#   rdiff(4, 30, ' lr %08x',  'lr',   newregs, self.regs)

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
    strs.append((9, 35, '%44s' % flstr))

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
         DSVAL(0x00000400,0x00000400,' id'),  DSVAL(0x00000200,0x00000200,' fd'),

         DSVAL(0x0000001f,0x0000000f,'\a sys\t'), DSVAL(0x0000001f,0x0000000e,'\r UND\t'),
         DSVAL(0x0000001f,0x0000000d,'\r UND\t'), DSVAL(0x0000001f,0x0000000c,'\r UND\t'),
         DSVAL(0x0000001f,0x0000000b,'\r und\t'), DSVAL(0x0000001f,0x0000000a,'\r UND\t'),
         DSVAL(0x0000001f,0x00000009,'\r UND\t'), DSVAL(0x0000001f,0x00000008,'\r UND\t'),
         DSVAL(0x0000001f,0x00000007,'\a abt\t'), DSVAL(0x0000001f,0x00000006,'\r UND\t'),
         DSVAL(0x0000001f,0x00000005,'\r UND\t'), DSVAL(0x0000001f,0x00000004,'\r UND\t'),
         DSVAL(0x0000001f,0x00000003,'\a sup\t'), DSVAL(0x0000001f,0x00000002,' irq'),
         DSVAL(0x0000001f,0x00000001,' fiq',),    DSVAL(0x0000001f,0x00000000,' usr')]),
)

ds_cpsr = DS('cpsr', 'program status register', 4, 1, 44, None, _cpsr_els)

data_structs = [ds_cpsr]

