CROSS_COMPILE ?= aarch64-linux-gnu

OBJS = pcie.o lib.o

all: pcie.bin 

.s.o:
	$(CROSS_COMPILE)-as -g $< -o $@
	$(CROSS_COMPILE)-objdump -d $@ > $*.lst

.c.o:
	$(CROSS_COMPILE)-gcc -Iinclude -g -O1 -c $< -o $@
	$(CROSS_COMPILE)-objdump -S $@ > $*.lst

pcie.elf: pcie.ld crt.o $(OBJS)
	$(CROSS_COMPILE)-ld -T pcie.ld $(OBJS) -Map pcie.map -o pcie.elf
	$(CROSS_COMPILE)-objdump -S $@ > pcie.lst

pcie.bin: pcie.elf
	$(CROSS_COMPILE)-objcopy -O binary pcie.elf pcie.bin

clean:
	-rm -f *.o *.lst *.map *.bin *.elf
