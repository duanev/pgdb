CROSS_COMPILE ?= aarch64-linux-gnu
CFLAGS = -mstrict-align -march=armv8-a+nofp -nostdlib -fno-builtin-printf
# -mstrict-align fixes strcpy faults

HDRS = global.h pcie.h
OBJS = main.o mem.o smp.o lib.o

all: smp.bin 

lib.o: gate.h


.s.o:
	$(CROSS_COMPILE)-as -g $< -o $@
	$(CROSS_COMPILE)-objdump -d $@ > $*.lst

%.o: %.c types.h global.h
	$(CROSS_COMPILE)-gcc $(CFLAGS) -g -O1 -c $< -o $@
	$(CROSS_COMPILE)-objdump -S $@ > $*.lst

smp.elf: smp.ld boot.o exc.o $(OBJS)
	$(CROSS_COMPILE)-ld -T smp.ld $(OBJS) -Map smp.map -o smp.elf

smp.bin: smp.elf
	$(CROSS_COMPILE)-objcopy -O binary smp.elf smp.bin

clean:
	-rm -f *.o *.lst *.map *.bin *.elf
