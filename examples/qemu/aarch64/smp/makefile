CROSS_COMPILE ?= aarch64-linux-gnu
CFLAGS = -g -O1 -mstrict-align -march=armv8-a+nofp -nostdlib -fno-builtin-printf
# note: -mstrict-align fixes alignment faults caused by strcpy() but
# forces all memset/memcpy calls to go to lib.c (also see global.h)

HDRS = global.h pcie.h
OBJS = main.o mem.o smp.o lib.o

all: smp.bin 

lib.o: gate.h


.s.o:
	$(CROSS_COMPILE)-as -g $< -o $@
	$(CROSS_COMPILE)-objdump -d $@ > $*.lst

%.o: %.c types.h global.h
	$(CROSS_COMPILE)-gcc $(CFLAGS) -c $< -o $@
	$(CROSS_COMPILE)-objdump -S $@ > $*.lst

smp.elf: smp.ld boot.o exc.o $(OBJS)
	$(CROSS_COMPILE)-ld -T smp.ld $(OBJS) -Map smp.map -o smp.elf

smp.bin: smp.elf
	$(CROSS_COMPILE)-objcopy -O binary smp.elf smp.bin

clean:
	-rm -f *.o *.lst *.map *.bin *.elf
