
#include <stdarg.h>

/* crt functions */
void con_puts(char * s);

static const char xdigits[16] = { "0123456789abcdef" };

int
printf(const char * fmt, ...)
{
    static char buf[1024];
    char nbuf[32];
    int rc;
    va_list ap;
    va_start(ap, fmt);

    char * q = buf;
    for (const char * p = fmt; *p; p++) {
        unsigned long u;
        char * s;
        if (*p == '%') {
            switch (*++p) {
            case 'c':
                u = va_arg(ap, int);
                *q++ = u;
                break;
            case 'd':
                u = va_arg(ap, int);
                s = nbuf;
                do {
                    *s++ = '0' + u % 10;
                    u /= 10;
                } while (u);
                while (s > nbuf)  *q++ = *--s;
                break;
            case 's':
                s = va_arg(ap, char *);
                if (s == 0) s = "(null)";
                while (*s)  *q++ = *s++;
                break;
            case 'x':
                *q++ = '0';
                *q++ = 'x';
                u = va_arg(ap, unsigned long);
                s = nbuf;
                do {
                    *s++ = xdigits[u % 16];
                    u /= 16;
                } while (u);
                while (s > nbuf)  *q++ = *--s;
                break;
            default:
                /* fall-through */
                break;
            }
        } else {
            *q++ = *p;
        }
    }
    *q = 0;

    con_puts(buf);

    va_end(ap);
    return rc;
}

