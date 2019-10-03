
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
    printf("*** exc: %s cpu(%d) esr(%x) elr(%x) far(%x)\n",
            exc_vec_labels[vecno], core_id(), esr, elr, far);
    stkdump();
}


void
main(int ac, char * av[])
{
    printf("smp v0.90 2019/09/21 el%d\n", armv8_get_el());

    smp_init();

    do {
    } while (con_peek() == 0);
    con_getc();
}
