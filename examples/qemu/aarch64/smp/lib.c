
#include <stdarg.h>
#include "global.h"
#include "gate.h"


static SPMC_GATE_INIT(con_puts, MAX_CPUS);

int
puts(const char * buf)
{
    // make puts re-entrant - con_puts() is not
    int token;
    wait_for_token(con_puts, token);

//#if 0
    // way useful debug: show which cpu is printing this line
    {
        char cb[4];
        cb[0] = '0' + cpu_id();
        cb[1] = ' ';
        cb[2] = '\0';
        con_puts(cb);
    }
//#endif

    con_puts(buf);
    return_token(con_puts, token);
}


static const char xdigits[16] = { "0123456789abcdef" };

/*
 * _vsprintf() returns a count of the printable characters,
 * but requires buf to be one character larger
 */
static int
_vsprintf(char * buf, const char * fmt, va_list ap)
{
    char nbuf[32];
    char fill = ' ';
    int mode = 0;           // state: 0 = normal, 1 = building format
    int b64 = 0;

    char * q = buf;
    for (const char * p = fmt; *p; p++) {
        u64 u;
        char * s;

        if (mode) {
            switch (*p) {
            case 'c':
                u = va_arg(ap, int);
                *q++ = u;
                mode = b64 = 0;
                break;
            case 'd':
                u = b64 ? va_arg(ap, u64) : va_arg(ap, int);
                s = nbuf;
                do {
                    *s++ = '0' + u % 10;
                    u /= 10;
                } while (u);
                while (s > nbuf)  *q++ = *--s;
                mode = b64 = 0;
                break;
            case 'l':
                b64 = 1;
                break;
            case 's':
                s = va_arg(ap, char *);
                if (s == 0) s = "(null)";
                while (*s)  *q++ = *s++;
                mode = b64 = 0;
                break;
            case 'x':
                u = b64 ? va_arg(ap, u64) : va_arg(ap, u32);
                s = nbuf;
                do {
                    *s++ = xdigits[u % 16];
                    u /= 16;
                } while (u);
                while (s > nbuf)  *q++ = *--s;
                mode = b64 = 0;
                break;
            case '0':
                fill = '0';
                break;
            }
        } else {
            if (*p == '%') {
                mode = 1;
            } else {
                *q++ = *p;
            }
        }
    }
    *q = 0;     // don't include the null delimiter in the count ...

    return q - buf;
}

int
sprintf(char * buf, const char * fmt, ...)
{
    int rc;
    va_list ap;
    va_start(ap, fmt);

    rc = _vsprintf(buf, fmt, ap);

    va_end(ap);
    return rc;
}

int
printf(const char * fmt, ...)
{
    struct thread * th = get_thread_data();
    int rc;
    va_list ap;
    va_start(ap, fmt);

    rc = _vsprintf(th->print_buf, fmt, ap);

    puts(th->print_buf);

    va_end(ap);
    return rc;
}


long
strlen(const char * s)
{
    int i = 0;
    while (s[i]) i++;
    return i;
}

char *
strcpy(char * dst, const char * src)
{
    while (*src)
        *dst++ = *src++;
    *dst = 0;
}

int
strcmp(const char * s1, const char * s2)
{
    while (*s1  &&  *s2) {
        if (*s1 != *s2)
            break;
        s1++;
        s2++;
    }
    return *s2 - *s1;
}

/*
 * memset() and memcpy() are only needed if -mstrict-align is enabled, or
 * if a mem* call is made with a variable length (lengths known at compile
 * time can be unrolled by the compiler); else the __builtin_mem* work.
 * (see global.h)
 */

void *
memset(void * s, int c, unsigned long n)
{
    u8 * d = s;
    while (n-- > 0)
        *d++ = c;
    return s;
}

void *
memcpy(void * dst, void * src, unsigned long n)
{
    u8 * d = dst;
    while (n-- > 0)
        *d++ = *((u8 *)src++);
    return dst;
}

int
n_bits_set(u64 x)
{
    int n = 0;
    for (int i = 0; i < 64; i++) {
        if (x & 1)
            n++;
        x >>= 1;
    }
    return n;
}

/* -------- debug functions */

void
hexdump(void * buf, int count, u64 addr)
{
    int     i, column, diff, lastdiff;
    char    hexbuf[49], asciibuf[17], last[17];
    char    *hptr, *aptr;

    hptr = hexbuf;
    aptr = asciibuf;
    i = column = 0;
    diff = 1;
    while (i < count) {
        unsigned char b = *((unsigned char *)buf + i);
        if (b != last[column]) diff = 1;
        last[column] = b;
        *hptr++ = xdigits[(b >> 4) & 0xf];
        *hptr++ = xdigits[b & 0xf];
        *hptr++ = column == 7 ? '-' : ' ';
        *aptr++ = (b >= ' ' && b <= '~') ? b : '.';
        if (++column == 16) {
            *hptr = *aptr = 0;
            if (diff == 0) {
                if (lastdiff == 1)
                    printf("(same)\n");
            } else {
                printf("%x: %s  %s\n", addr, hexbuf, asciibuf);
            }
            lastdiff = diff;
            diff = 0;
            addr += 16;
            column = 0;
            hptr = hexbuf;
            aptr = asciibuf;
        }
        i++;
    }
    if (column) {
        *hptr = *aptr = 0;
        printf("%x: %s  %s\n", addr, hexbuf, asciibuf);
    }
}


/*
 * stkdump()
 *
 * remember, compilers and their options can change the stack layout ...
 */

#ifdef __GNUC__
#ifdef __ARM_ARCH_8A
#define ___supported
// stkdump() may only work for gcc -g -O1

// this sould more correctly be set to the total size of the stack,
// I'm reducing it here to make the frame hunt more strict - with of
// course, the caveat that large stack allocations will break stkdump()
#define MAX_LOCAL_ALLOC 0x200

void
stkdump(void)
{
    u64 * sp;
    u64 * pc;
    //u64 * fp;
    int i;

    asm volatile("mov %0, sp" : "=r" (sp) : );
    //asm volatile("mov %0, fp" : "=r" (fp) : );

    //printf("sp(%x) sp[0](%x) sp[1](%x) sp[2](%x) sp[3](%x) sp[4](%x) sp[5](%x)\n",
    //        sp, sp[0], sp[1], sp[2], sp[3], sp[4], sp[5]);

    // find previous sp - it should not be far, stkdump has no args
    for (i = 0; i < 4; i++) {
        if (sp[i] > (u64)sp  &&  sp[i] < ((u64)sp + MAX_LOCAL_ALLOC))
            break;
    }

    if (i >= 4) {
        printf("frame not found ... %x,%x,%x,%x\n", sp[i], sp[i+1], sp[i+2], sp[i+3]);
        return;
    }

    struct thread * th = get_thread_data();
    char * q = th->print_buf;
    q += sprintf(q, "%s", "*** stack:\n");

    sp = (u64 *)sp[i];
    pc = (u64 *)sp[i+1];
    do {
        q += sprintf(q, "*** exc: cpu(%d) pc(%x) sp(%x) ret(%x)",
                                  cpu_id(), pc, sp, sp[0]);

        if (sp[0] < (u64)sp  ||  sp[0] > ((u64)sp + MAX_LOCAL_ALLOC)) {
            *q++ = '\n';
            break;
        }

        for (i = 2; (u64)(sp + i) < sp[0] ; i++)
            q += sprintf(q, " %x", sp[i]);
        pc = (u64 *)sp[1];
        sp = (u64 *)sp[0];
        *q++ = '\n';
    } while (1);
    *q = '\0';

    puts(th->print_buf);
}

#endif
#endif


#ifndef ___supported
void
stkdump(void) {}
#endif

