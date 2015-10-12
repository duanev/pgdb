
volatile unsigned int * const UART0DR = (unsigned int *)0x101f1000;
 
void
print_uart0(const char *s)
{
    while (*s) {
        *UART0DR = (unsigned int)(*s);
        s++;
    }
}
 
void
c_entry()
{
    print_uart0("Hello world!\n");
}
