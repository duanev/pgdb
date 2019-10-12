
#include "global.h"
#include "gate.h"


/* ---- bitmap functions
 * needed for slab memory management (that's why they are here)
 */

#define ALL_BITS_ON     ((u64)-1)
#define BLK_SIZE        (sizeof(u64) * BITS_PER_BYTE)

void
bitmap_create(struct bitmap * map, int size)
{
    map->nblks = (size + BLK_SIZE - 1) / BLK_SIZE;
    map->count = 0;
    return;
}

void
bitmap_set(struct bitmap * map, int n)
{
    int blk = n / BLK_SIZE;
    int bit = n % BLK_SIZE;
    if ((map->blks[blk] & (1UL << bit)) == 0) {
        map->blks[blk] |= (1UL << bit);
        map->count++;
    }
}

void
bitmap_clear(struct bitmap * map, int n)
{
    int blk = n / BLK_SIZE;
    int bit = n % BLK_SIZE;
    if (map->blks[blk] & (1UL << bit)) {
        map->blks[blk] &= ~(1UL << bit);
        map->count--;
    }
}

/*
 * find the first free object index,
 * -1 means the bitmap is full
 */
int
bitmap_first_1_free(struct bitmap * map)
{
    int blk;
    int bit;

    for (blk = 0; blk < map->nblks; blk++)
        if (map->blks[blk] != ALL_BITS_ON)
            for (bit = 0; bit < BLK_SIZE; bit++)
                if ((map->blks[blk] & (1UL << bit)) == 0)
                    return blk * BLK_SIZE + bit;
    return -1;
}

/*
 * find the index of the first N free objects,
 * -1 means no N contiguous objects
 */
int
bitmap_first_n_free(struct bitmap * map, int n)
{
    int blk;
    int bit;
    int i = 0;
    int idx = -1;

    for (blk = 0; blk < map->nblks; blk++)
        if (map->blks[blk] != ALL_BITS_ON)
            for (bit = 0; bit < BLK_SIZE; bit++)
                if ((map->blks[blk] & (1UL << bit)) == 0) {
                    if (idx == -1)
                        idx = blk * BLK_SIZE + bit;
                    i++;
                    if (i >= n)
                        return idx;
                } else {
                    idx = -1;
                    i = 0;
                }
    return -1;
}


/* -------- slab memory management
 * imo the ONLY proper way to manage linear address space
 */

// ugh, I hate global locks, but until I rewrite gate.h
// to allow placing a gate struct inside another struct ...
static SPMC_GATE_INIT(pool, MAX_CPUS);

/*
 * the caller must remember what N was ...
 */
u64
mem_alloc(struct mem_pool * pool, int n)
{
    if (pool == 0) {
        printf("mem_alloc error: pool uninitialized\n");
        stkdump();
        return 0;
    }

    u32 token;
    wait_for_token(pool, token);
    int idx = bitmap_first_n_free(&pool->map, n);
    if (idx == -1) {
        return_token(pool, token);
        printf("mem_alloc error: pool map %s is full\n", pool->name);
        stkdump();
        return 0;
    }
    u64 addr = idx * pool->usize + pool->base;
    // bitmap_first_n_free can run off the end, double check the addr
    if (addr > pool->base + pool->size - pool->usize) {
        return_token(pool, token);
        printf("mem_alloc error: pool %s is empty\n", pool->name);
        stkdump();
        return 0;
    }

    for (int i = 0; i < n; i++)
        bitmap_set(&pool->map, idx + i);
    return_token(pool, token);

    return addr;
}

void
mem_free(struct mem_pool * pool, u64 addr, int n, int zero)
{
    if (addr < pool->base  ||  addr >= pool->base + pool->size) {
        printf("mem_free error: 0x%lx is not within pool %s\n", addr, pool->name);
        stkdump();
        return;
    }

    if (zero)
        memset((void *)addr, 0, pool->usize * n);

    int idx = (addr - pool->base) / pool->usize;
    u32 token;
    wait_for_token(pool, token);
    for (int i = 0; i < n; i++)
        bitmap_clear(&pool->map, idx + i);
    return_token(pool, token);
}


/*
 * mem_pool_create()
 *
 *  name  - for error and info messages
 *  base  - physical start of new region
 *  size  - size of the region; will be split into mgt structs, and blocks
 *          (note: the resulting available pool size will be smaller)
 *  usize - unit size of the blocks in this region
 *  init  - zero all blocks
 *
 *  returns 0 on error, else a pointer to be used for
 *  subsequent mam_alloc() and mem_free() functions.
 */
struct mem_pool *
mem_pool_create(char * name, u64 base, u64 size, u64 usize, int zero)
{
    // the first block(s) are reserved for the
    // pool data structure and bitmap

    struct mem_pool * pool = (struct mem_pool *)base;

    int err = 0;
    if (n_bits_set(usize) != 1) {
        printf("mem_pool_create error: usize must be a power of 2 (%d)\n", usize);
        stkdump();
        err++;
    }
    if (size < usize * 2) {
        printf("mem_pool_create error: size (%ld) must mimally be 2x unit size (only %ld)\n",
                name, size, usize);
        stkdump();
        err++;
    }
    if ((size % usize) != 0) {
        printf("mem_pool_create error: size must be a multiple of usize\n");
        stkdump();
        err++;
    }
    if (err)
        return 0;

    // estimate nblks
    int eblks = (size + usize - 1) / usize;
    // actual nblks
    int nblks = (size - sizeof(struct mem_pool)
                      - (eblks + BITS_PER_BYTE - 1) / BITS_PER_BYTE
                 ) / usize;

    pool->base  = base + usize * (eblks - nblks);
    pool->size  = size - usize * (eblks - nblks);
    pool->name  = name;
    pool->usize = usize;

    memset((void *)(pool->map.blks), 0, nblks / BLK_SIZE);
    if (zero)
        memset((void *)pool->base, 0, pool->size);

    bitmap_create(&pool->map, nblks);
    printf("mem_pool %-8s at 0x%lx end 0x%lx   %d units\n", name, base, base + size, nblks);
    return pool;
}


#if 0
void
mem_pool_debug(struct mem_pool * pool)
{
    printf("pool %s: base(0x%x) size(0x%x) usize(%d) nblks(%d)\n",
            pool->name, pool->base, pool->size, pool->usize, pool->map.nblks);
    for (int i = 0; i < pool->map.nblks; i++)
        printf("    %016lx\n", pool->map.blks[i]);
}
#endif
