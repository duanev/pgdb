
#include "global.h"

static int smp_next_cpu = 1;    // 0 is the boot cpu


static inline void
armv8_set_tp(u64 tp)
{
    asm volatile("msr tpidr_el0, %0" : : "r" (tp) : );
}

void
smp_newcpu(struct thread * th)
{
    armv8_set_tp(th->stack - 0x1000);

    printf("smp%d: el%d tls(%x) sp(%x)\n", th->thno, armv8_get_el(),
                                    armv8_get_tp(), armv8_get_sp());

    th->func(th);

    asm volatile("wfi");        // low power sleep
};

static int
smp_start_thread(int (* func)(struct thread *), void * arg0)
{
    int cpu = smp_next_cpu++;

    struct thread * th = (struct thread *)mem_alloc(pool4k, 1);

    th->stack = (u64)th + 0x1000;
    th->func  = func;
    th->thno  = cpu;
    th->arg0  = arg0;

    // http://wiki.baylibre.com/doku.php?id=psci
    //   psci {
    //          migrate = < 0xc4000005 >;
    //          cpu_on = < 0xc4000003 >;
    //          cpu_off = < 0x84000002 >;
    //          cpu_suspend = < 0xc4000001 >;
    //          method = "hvc";
    //          compatible = "arm,psci-0.2\0arm,psci";
    //   };
    //
    // power on cpu N, point it at the smp_entry boot code,
    // and use the 'th' pointer as 'context'
    int rc;
    asm volatile (
        "ldr  x0, =0xc4000003   \n" // cpu on
        "mov  x1, %1            \n" // cpu number
        "ldr  x2, =smp_entry    \n" // func addr
        "mov  x3, %2            \n" // context id (th)
        "hvc  0                 \n" // hypervisor fn 0
        "mov  %0, x0            \n"
    : "=r" (rc) : "r" (cpu), "r" (th) : "x0","x1","x2","x3");
    return rc;
}

static int
thd(struct thread * th)
{
    printf("thread %d: cpu(%d) arg(%x)\n", th->thno, cpu_id(), th->arg0);

//#if 0
    if (th->thno == 1) {
        // test exc_handler
        printf("forcing a memory access exception on thread 1 ...\n");
        int * x = (void *)-1;
        printf("%x\n", *x);
    }
//#endif
}

int
smp_init(void)
{
    // announce the boot thread
    printf("smp0: el%d tls(%x) sp(%x)\n", armv8_get_el(), armv8_get_tp(), armv8_get_sp());

    int n = 1;      // the boot cpu counts as 1
    while (smp_start_thread(thd, (void *)(u64)n) == 0)
        if (++n >= MAX_CPUS)
            break;

    printf("smp_init complete %d cpus\n", n);

    return n;
}
