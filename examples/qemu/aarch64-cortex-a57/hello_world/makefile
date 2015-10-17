CROSS_COMPILE ?= aarch64-linux-gnu

all: startup.lst test.bin 

startup.o: startup.s
	$(CROSS_COMPILE)-as -g startup.s -o startup.o

startup.lst: startup.o
	$(CROSS_COMPILE)-objdump -d startup.o > startup.lst

test.elf: test.ld startup.o
	$(CROSS_COMPILE)-ld -T test.ld startup.o -Map test.map -o test.elf

test.bin: test.elf
	$(CROSS_COMPILE)-objcopy -O binary test.elf test.bin

clean:
	-rm -f *.o *.lst *.map *.bin
