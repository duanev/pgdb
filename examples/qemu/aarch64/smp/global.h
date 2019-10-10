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

#define MAX_CPUS    8

void con_puts(const char * s);
char con_getc(void);
char con_peek(void);
void reboot(void);

/* -------- bitmaps */

struct bitmap {
    int nblks;
    int count;
    u64 blks[0];
};

void  bitmap_create(struct bitmap * map, int size);
void  bitmap_set(struct bitmap * map, int n);
void  bitmap_clear(struct bitmap * map, int n);
int   bitmap_first_free(struct bitmap * map);

/* -------- memory */

struct mem_pool {
    u64           base;
    u64           size;
    u64           usize;
    char *        name;
    struct bitmap map;      // must be last - bitmap blks array at end ...
};

extern struct mem_pool * pool0;
extern struct mem_pool * pool4k;

u64    mem_alloc(struct mem_pool * pool, int n);
void   mem_free(struct mem_pool * pool, u64 addr, int n);
struct mem_pool * mem_pool_create(char * name, u64 base, u64 size, u64 unit_size);

/* -------- library functions */

int    sprintf(char * buf, const char *fmt, ...);
int    printf(const char *fmt, ...);
int    puts(const char *);
long   strlen(const char *);
char * strcpy(char * dst, const char * src);
int    strcmp(const char * s1, const char * s2);
void * memset(void * s, int c, unsigned long n);
void * memcpy(void * dst, void * src, unsigned long n);
int    n_bits_set(u64 x);
void   hexdump(void * buf, int count, u64 addr);
void   stkdump(void);

/* -------- smp support */

struct thread {
    u64             stack;      // boot.s expects this to be first
    u64             thno;
    struct task *   tsk;
    int          (* func)(struct thread *);
    void *          arg0;
    u64             _res1;
    u64             _res2;      // align scratch/print_buf to
    u64             _res3;      // cache lines (easier to debug)

    char            scratch[64];
    char            print_buf[0];
};

int    smp_init(void);

/* -------- cpu functions */

// time delay (uncalibrated ...)
#define delay(n)    for (volatile int x = 0; x < (n) * 1000; x++)

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

static inline u64
armv8_get_sp(void)
{
    u64 sp;
    asm volatile("mov %0, sp"  : "=r" (sp) : );
    return sp;
}

static inline struct thread *
get_thread_data(void)
{
    return (struct thread *)armv8_get_tp();
}

// will only work after tp has been established (in smp_init)
static inline int
cpu_id(void)
{
    struct thread * th = (struct thread *)armv8_get_tp();
    return th->thno;
}

