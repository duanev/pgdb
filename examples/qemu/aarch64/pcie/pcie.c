/*
 *  PCIe with ECAM
 *
 * notes:
 *  type 0 config header   PCI-Express-Base-Spec-v3.0.pdf  pg 595
 *                         https://en.wikipedia.org/wiki/PCI_configuration_space
 *
 *  https://stackoverflow.com/questions/19006632/how-is-a-pci-pcie-bar-size-determined
 *  https://wiki.osdev.org/PCI
 *  https://wiki.osdev.org/PCI_Express
 *  https://wiki.qemu.org/images/f/f6/PCIvsPCIe.pdf
 */

typedef unsigned char       u8;
typedef unsigned short      u16;
typedef unsigned int        u32;
typedef unsigned long long  u64;

typedef char                i8;
typedef short               i16;
typedef int                 i32;
typedef long long           i64;


/* crt functions */
void con_puts(char * s);
char con_getc(void);

/* library functions */
int printf(const char *fmt, ...);


// $ qemu-system-aarch64 -machine virt,dumpdtb=qemu.dtb
// $ dtc -O dtb -o qemu.dtb qemu.dts
// $ vim qemu.dts: pcie@10000000 { ... reg = < 0x40 0x10000000 0x00 0x10000000 >; ... }

#define PCIE_CONF_ADDR  0x4010000000ull
#define PCIE_CONF_END   0x4020000000ull
#define PCIE_CONF_SIZE  0x8000

#define PCI_CONF_BAR_IO          0x01
#define PCI_CONF_BAR_BELOW1MB    0x02
#define PCI_CONF_BAR_64BIT       0x04
#define PCI_CONF_BAR_PREFETCH    0x08

struct pci_confspace {
    u16 vendorId;
    u16 deviceId;
    u16 command;
    u16 status;
    u8  revisionId;
    u8  progIf;
    u8  subclass;
    u8  classCode;
    u8  cacheLineSize;
    u8  latTimer;
    u8  headerType;
    u8  bist;
    u32 bar[6];
    u32 cardbusCIS;
    u16 subsysVendorId;
    u16 subsysId;
    u32 expansionRomAddr;
    u8  capPtr;
    u8  reserved0;
    u16 reserved1;
    u32 reserved2;
    u8  intrLine;
    u8  intrPin;
    u8  minGrant;
    u8  maxLatency;
}; // __attribute__ ((__packed__));

struct pci_capability {
    u8  capId;
    u8  next;
    u16 expCap;
    u32 devCap;                 // v3.0 pg 608
    u16 devControl;             // v3.0 pg 613
    u16 devStatus;              // v3.0 pg 620
    u32 linkCap;                // v3.0 pg 622
    u16 linkControl;            // v3.0 pg 627
    u16 linkStatus;             // v3.0 pg 635
    u32 slotCap;                // v3.0 pg 638
    u16 slotControl;            // v3.0 pg 640
    u16 slotStatus;             // v3.0 pg 644
    u16 rootControl;            // v3.0 pg 646
    u16 rootCap;                // v3.0 pg 647
    u32 rootStatus;             // v3.0 pg 648
    // dev2
    // link2
    // slot2
};



static inline void dc_flush(u64 va)
{
    __asm__ __volatile__("dc cvac, %0\n\t" : : "r" (va) : "memory");
}

static inline void dc_invalidate(u64 va)
{
    __asm__ __volatile__("dc civac, %0\n\t" : : "r" (va) : "memory");
}


int
pci_scan(void)
{
    struct pci_confspace * conf;

    for (u64 i = PCIE_CONF_ADDR; i < PCIE_CONF_END; i += PCIE_CONF_SIZE) {
        conf = (void *)i;

        if (conf->vendorId  &&  conf->vendorId != 0xffff) {
            printf("  %x %x %x\n", i, conf->vendorId, conf->deviceId);

            // signal the BARs to expose their size
            for (int j = 0; j < 6; j++)
                conf->bar[j] = 0xffffffff;

            // hilarious, but awesome!  qemu aarch64 requires this cache
            // line invalidate in order to correctly read the the BARs.
            // does this mean real caching is implemented in qemu?  :o
            dc_invalidate((u64)conf->bar);

            for (int j = 0; j < 6; j++) {
                if (conf->bar[j]) {
                    u64 siz = 0xffffffff00000000ull | (conf->bar[j] & 0xfffffff0);
                    if (conf->bar[j] & PCI_CONF_BAR_64BIT)
                        siz |= ((u64)conf->bar[++j] << 32);
                    siz = ~siz + 1;
                    printf("    %x bar%d class(%x,%x) prg(%x) size(%x)\n", conf->bar + j, j,
                            conf->classCode, conf->subclass, conf->progIf, siz);
                }
            }

            // list the capabilities
            if (conf->capPtr) {
                struct pci_capability * cap = (void *)i + conf->capPtr;
                for (; cap->next; cap = (void *)i + cap->next) {
                    printf("        %x cap", cap);
                    if (cap->expCap)  printf(" exp(%x)", cap->expCap);
                    if (cap->devCap)  printf(" dev(%x,%x)", cap->devCap, cap->devStatus);
                    if (cap->linkCap) printf(" link(%x,%x)", cap->linkCap, cap->linkStatus);
                    if (cap->slotCap) printf(" slot(%x,%x)", cap->slotCap, cap->slotStatus);
                    con_puts("\n");         // gcc uses putchar for printf("\n")
                }
            }
        }
    }
}


void
main(int ac, char * av[])
{
    char c;
    do {
        pci_scan();
        c = con_getc();
        printf("-------- %c\n", c);
    } while (c != 'q');
}
