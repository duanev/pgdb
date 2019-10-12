/*
 * Serialization functions (spin locks)
 *
 * notes:
 *   https://barrgroup.com/Embedded-Systems/How-To/C-Volatile-Keyword
 */

#include "types.h"

// A multi-consumer / single producer queue based on the
// 'take a ticket' system found in stores/post-offices
// where people wait in a first-come first-served order.
// spin-lock performance optimizations are included.
//
// When a new consumer arrives (to ship a package...) it takes
// the next consumer ticket and waits for 'now serving ticket X',
// which is signaled by a non-zero value placed in the queue
// array at it's ticket's index.  When a consumer's ticket is
// called, it does it's business, and then returns the ticket
// to the next consumer's ticket index.
//
// Performance is achieved by reducing the inter-processor
// cache coherency traffic.  Each cpu polls a location in the
// queue distant enough from other pollers as to not cause
// constant overlapping cache snoop or brodcast cycles.  This
// distance may need to be an entire cache line (instead of
// a u64, but if an architecture has a 'monitor' opcode with
// sufficient address granularity the u64 may even be replaced
// with a u8.
//
// NOTE: pretty sure you don't want to declare the gate on a stack ...

#define QUEUE_SIZE_MASK(name)       (sizeof(name##_gate.queue)/sizeof(name##_gate.queue[0]) - 1)

// single producer / multi-consumer
// take turns with a single ticket (ie. a token)
//
// the queue starts with a single initial value (the token).
// arrival order is maintained.  here gate->end 'points' to the
// next ticket to be taken, ie. one past the end of the queue.
// note that gate->end is *not* a queue index, (gate->end & mask) is.

#define SPMC_GATE_INIT(name, size)  \
    struct name##_gate {            \
        volatile u64 queue[size];   \
        volatile long end;          \
    } name##_gate = {{1}, 0};


#define wait_for_token(name, t) {                                   \
    t = atomic_fetch_inc(name##_gate.end) & QUEUE_SIZE_MASK(name);  \
    while (name##_gate.queue[t] == 0);                              \
    name##_gate.queue[t] = 0;                                       \
    (t)++;                                                          \
}

#define return_token(name, t)  \
    { name##_gate.queue[(t) & QUEUE_SIZE_MASK(name)] = 1; }

#define debug_spmc_gate(name) {                             \
    printf("%s end(%d)\n", #name, name##_gate.end);         \
    for (int k = 0; k <= QUEUE_SIZE_MASK(name); k++)        \
        printf("%s q(%lx)\n", #name, name##_gate.queue[k]); \
}

