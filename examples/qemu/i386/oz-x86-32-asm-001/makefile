

all: oz_fd oz_usb

oz_fd.img: oz_fd
	dd if=/dev/zero of=oz_fd.img bs=512 count=`expr 2 \* 80 \* 18`
	dd if=oz_fd of=oz_fd.img conv=notrunc

oz_fd: oz.asm
	nasm -DFLOPPY -l oz_fd.lst -o oz_fd oz.asm

oz_usb: oz.asm
	nasm -DUSB -l oz_usb.lst -o oz_usb oz.asm
	echo "very carefully as root: # dd if=oz_usb of=/dev/sdX"

clean:
	rm -f oz_fd oz_fd.img oz_usb *.lst

