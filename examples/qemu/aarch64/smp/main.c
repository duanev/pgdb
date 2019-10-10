
#include "global.h"

static char * exc_vec_labels[16] = {
    "sp0_sync",  "sp0_irq",  "sp0_fiq",  "sp0_serror",
    "spx_sync",  "spx_irq",  "spx_fiq",  "spx_serror",
    "el64_sync", "el64_irq", "el64_fiq", "el64_serror",
    "el32_sync", "el32_irq", "el32_fiq", "el32_serror"
};

void
exc_handler(u64 vecno, u64 esr, u64 elr, u64 far)
{
    printf("*** exc: cpu(%d) %s esr(%lx) elr(%lx) far(%lx)\n",
            cpu_id(), exc_vec_labels[vecno], esr, elr, far);
    stkdump();
}


extern int _free_mem;
struct mem_pool * pool0  = 0;
struct mem_pool * pool4k = 0;

void
main(int ac, char * av[])
{
    printf("smp v0.91 2019/10/08 el%d\n", armv8_get_el());

    // establish the system memory pools from DRAM following the 'data' segment (see tasks.ld)

    pool0 = mem_pool_create("128k top", (u64)&_free_mem, 256 * 1024 * 1024, 128 * 1024);
    if (pool0 == 0)  return;
    pool4k = (struct mem_pool *)mem_alloc(pool0, 4);
    mem_pool_create("4k gp", (u64)pool4k, pool0->usize * 4, 4 * 1024);
    if (pool4k == 0)  return;

    smp_init();

    do {
    } while (con_peek() == 0);
    con_getc();

    // reset the system memory pools

    memset((void *)pool4k, 0, sizeof(struct mem_pool));
    memset((void *)pool0,  0, sizeof(struct mem_pool));
}
