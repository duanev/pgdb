#
# PGDB arm 32bit architecture module
#
# contributors:
#   djv - Duane Voth
#
# history:
#   2015/10/12 - v0.05 - djv - released

version = "PGDB arm v0.01 2015/10/12"

name = 'arm'

Log = None

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
gspec_len = 136


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

    return strs

def get_seg_register(self):
    # for architectures that don't use segments, return either a 0
    # or an overlay number.  Overlays (for our purposes here) have
    # the same definition as segments: ie. a set of address spaces
    # that overlap.
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

data_structs = []

