
#include "global.h"

struct thread Threads[MAX_CPUS];

static int smp_next_cpu = 1;    // 0 is the boot cpu


static inline void
armv8_set_tp(u64 tp)
{
    asm volatile("msr tpidr_el0, %0" : : "r" (tp) : );
}

void
smp_newcpu(struct thread * th)
{
    if (armv8_get_tp() == 0) {
        // initialize a new core
        switch (th->thno) {
        case 1:  armv8_set_tp(TLS(1));  break;
        case 2:  armv8_set_tp(TLS(2));  break;
        case 3:  armv8_set_tp(TLS(3));  break;
        case 4:  armv8_set_tp(TLS(4));  break;
        case 5:  armv8_set_tp(TLS(5));  break;
        case 6:  armv8_set_tp(TLS(6));  break;
        case 7:  armv8_set_tp(TLS(7));  break;
        }
    }

    printf("smp%d: el%d tls(%x) sp(%x)\n", th->thno, armv8_get_el(), armv8_get_tp(), &th);

    th->func(th);

    asm volatile("wfi");        // low power sleep
};

extern int _stack0_start;
extern int _stack1_start;
extern int _stack2_start;
extern int _stack3_start;
extern int _stack4_start;
extern int _stack5_start;
extern int _stack6_start;
extern int _stack7_start;

int
smp_start_thread(int cpu, int (* func)(struct thread *), void * arg0)
{
    // if unspecified, use the next cpu (FIXME need idle detect)
    if (cpu < 0)
        cpu = atomic_fetch_inc(smp_next_cpu);

    struct thread * th = Threads + cpu;

    switch (cpu) {
    case 0:  th->stack_start = &_stack0_start;  break;
    case 1:  th->stack_start = &_stack1_start;  break;
    case 2:  th->stack_start = &_stack2_start;  break;
    case 3:  th->stack_start = &_stack3_start;  break;
    case 4:  th->stack_start = &_stack4_start;  break;
    case 5:  th->stack_start = &_stack5_start;  break;
    case 6:  th->stack_start = &_stack6_start;  break;
    case 7:  th->stack_start = &_stack7_start;  break;
    }
    th->func = func;
    th->thno = cpu;
    th->arg0 = arg0;

    //  psci {
    //          migrate = < 0xc4000005 >;
    //          cpu_on = < 0xc4000003 >;
    //          cpu_off = < 0x84000002 >;
    //          cpu_suspend = < 0xc4000001 >;
    //          method = "hvc";
    //          compatible = "arm,psci-0.2\0arm,psci";
    //  };
    //
    // power on the cpuno core and point it at the smp_entry boot code
    // and use the th pointer as 'context'
    // http://wiki.baylibre.com/doku.php?id=psci
    asm volatile (
        "ldr  x0, =0xc4000003   \n" // cpu on
        "mov  x1, %0            \n" // cpu number
        "ldr  x2, =smp_entry    \n" // func addr
        "mov  x3, %1            \n" // context id
        "hvc  0                 \n" // hypervisor fn 0
    : : "r" (cpu), "r" (th) : "x0","x1","x2","x3");
    // hah, gcc is letting me return the hvc's x0 with no declarative warnings!
    // we'll see how long that lasts ...
}

int
thd(struct thread * th)
{
    printf("thread %d: cpu(%d) arg(%x)\n", th->thno, core_id(), th->arg0);

//#if 0
    if (th->thno == 1) {
        // test exc_handler
        printf("forcing a memory access exception on thread 1 ...\n");
        int * x = (void *)-1;
        printf("%x\n", *x);
    }
//#endif
}

void
smp_init(void)
{

    // smp_start_thread() with a zero or greater cpu number does not yet
    // restart a cpu on the new thread ... until then smp_start_thread()
    // must be called from main() with a -1
    int n = 0;
    do {
        if (n++ >= MAX_CPUS-1) break;
    } while (smp_start_thread(-1, thd, (void *)((n << 4) | (u64)0xa)) == 0);

    printf("smp_init complete %d cpus\n", n);
}
