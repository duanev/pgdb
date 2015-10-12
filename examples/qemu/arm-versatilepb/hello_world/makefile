
all: test.bin startup.lst test.lst

startup.o: startup.s
	arm-none-eabi-as -mcpu=arm926ej-s -g startup.s -o startup.o

startup.lst: startup.o
	arm-none-eabi-objdump -S startup.o > startup.lst

test.o: test.c makefile
	arm-none-eabi-gcc -c -mcpu=arm926ej-s -g test.c -o test.o

test.lst: test.o
	arm-none-eabi-objdump -S test.o > test.lst

test.elf: test.ld test.o startup.o
	arm-none-eabi-ld -T test.ld test.o startup.o -Map test.map -o test.elf

test.bin: test.elf
	arm-none-eabi-objcopy -O binary test.elf test.bin

clean:
	-rm -f *.o *.lst *.map *.bin
