
all: startup.lst test.bin 

startup.o: startup.s
	aarch64-linux-gnu-as -g startup.s -o startup.o

startup.lst: startup.o
	aarch64-linux-gnu-objdump -d startup.o > startup.lst

test.elf: test.ld startup.o
	aarch64-linux-gnu-ld -T test.ld startup.o -Map test.map -o test.elf

test.bin: test.elf
	aarch64-linux-gnu-objcopy -O binary test.elf test.bin

clean:
	-rm -f *.o *.lst *.map *.bin
