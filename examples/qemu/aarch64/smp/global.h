/*
 * Global definitions and declarations for bare metal ARMv8
 */

#include "types.h"

#define atomic_fetch_inc(x) __sync_fetch_and_add(&(x), 1)

// defining these as builtin ASSUMES the 'size' arg is *fixed* at compile time, if it isn't
// you will get "relocation truncated to fit: R_AARCH64_CALL26 against undefined symbol <symbol>"
// and need to use the lib.c versions.  -mstrict-align also disables __builtin_mem*
//#define memset  __builtin_memset
//#define memcpy  __builtin_memcpy
#define strcat  __builtin_strcat

/* -------- boot.s exports */

extern void * boot_args;

extern int _tls0;
extern int _tls1;
extern int _tls2;
extern int _tls3;
extern int _tls4;
extern int _tls5;
extern int _tls6;
extern int _tls7;

#define TLS(t)      ((u64)&(_tls##t))

#define MAX_CPUS    8

void con_puts(const char * s);
char con_getc(void);
char con_peek(void);
void reboot(void);

/* -------- library functions */
int    sprintf(char * buf, const char *fmt, ...);
int    printf(const char *fmt, ...);
int    puts(const char *);
long   strlen(const char *);
char * strcpy(char * dst, const char * src);
int    strcmp(const char * s1, const char * s2);
void * memset(void * s, int c, unsigned long n);
void * memcpy(void * dst, void * src, unsigned long n);
void   hexdump(void * buf, int count, u64 addr);
void   stkdump(void);

/* -------- smp support */

struct thread {
    void * stack_start;
    int    (* func)(struct thread *);
    int    thno;
    void * arg0;
};

void smp_init(void);
int  smp_start_thread(int cpu, int (* func)(struct thread *), void * arg0);

// time delay (uncalibrated ...)
#define delay(n)    for (volatile int x = 0; x < (n) * 1000; x++)

/* -------- cpu functions */

static inline void dc_flush(u64 va)
{
    asm volatile("dc cvac, %0\n\t" : : "r" (va) : "memory");
}

static inline void dc_invalidate(u64 va)
{
    asm volatile("dc civac, %0\n\t" : : "r" (va) : "memory");
}

static inline u32 armv8_get_el(void)
{
    u32 status;
    asm("mrs %0, currentel; lsr %0, %0, 2" : "=r" (status) : : );
    return status;
}

static inline u64
armv8_get_tp(void)
{
    u64 tp;
    asm volatile("mrs %0, tpidr_el0" : "=r" (tp) : : );
    return tp;
}

// compute the core id from the tp value - this assumes knowledge of
// where the thread local storage areas are defined in nui.ld, and
// will only work after the tp has been established (in smp_init).
static inline int
core_id(void)
{
    return (armv8_get_tp() - TLS(0)) / (TLS(1) - TLS(0));
}

