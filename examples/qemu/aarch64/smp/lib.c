
#include <stdarg.h>         // for va_args
#include "global.h"
#include "gate.h"

static SPMC_GATE_INIT(con_puts, MAX_CPUS);

int
puts(const char * buf)
{
    // make puts re-entrant - con_puts() is not
    u32 token;
    wait_for_token(con_puts, token);
    con_puts(buf);
    return_token(con_puts, token);
}


static const char xdigits[16] = { "0123456789abcdef" };

static int
_vsprintf(char * buf, const char * fmt, va_list ap)
{
    char nbuf[32];
    char fill = ' ';
    int mode = 0;           // state: 0 = normal, 1 = building format
    int b64 = 0;
    int rc;

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
                //*q++ = '0';
                //*q++ = 'x';
                u = b64 ? va_arg(ap, u64) : va_arg(ap, int);
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
    *q = 0;

    return rc;
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
    char * buf = (char *)armv8_get_tp();
    int rc;
    va_list ap;
    va_start(ap, fmt);

    rc = _vsprintf(buf, fmt, ap);

    puts(buf);

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


void
hexdump(void * buf, int count, u64 addr)
{
    static char *hexmap = "0123456789abcdefgh";
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
        *hptr++ = hexmap[(b >> 4) & 0xf];
        *hptr++ = hexmap[b & 0xf];
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
// this stkdump version is only tuned for gcc -O1

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

    pc = (u64 *)sp[i+1];
    sp = (u64 *)sp[i];
    printf("stack:\n");
    while (1) {
        printf("    pc(%x) sp(%x) ret(%x)", pc, sp, sp[0]);

        if (sp[0] < (u64)sp  ||  sp[0] > ((u64)sp + MAX_LOCAL_ALLOC)) {
            printf("\n");
            break;
        }

        for (i = 2; (u64)(sp + i) < sp[0] ; i++)
            printf(" %x", sp[i]);
        pc = (u64 *)sp[1];
        sp = (u64 *)sp[0];
        printf("\n");
    }
}

#endif
#endif


#ifndef ___supported
void
stkdump(void)
{
}
#endif

