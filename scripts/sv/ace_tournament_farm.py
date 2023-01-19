from __future__ import annotations

import argparse
import sys
import time

import serial

SERIAL_DEFAULT = 'COM1' if sys.platform == 'win32' else '/dev/ttyUSB0'


def _press(ser: serial.Serial, s: str, duration: float = .05) -> None:
	ser.write(s.encode())
	time.sleep(duration)
	ser.write(b'0')
	time.sleep(.075)


def _beep(ser: serial.Serial) -> None:
	ser.write(b'!')
	time.sleep(.25)
	ser.write(b'.')


def main() -> int:
	parser = argparse.ArgumentParser()
	parser.add_argument('--count', type=int, default=1)
	parser.add_argument('--serial', default=SERIAL_DEFAULT)
	args = parser.parse_args()

	with serial.Serial(args.serial, 9600) as ser:
   	i=0
   	while i <= 10:
    	_press(ser, 'A')
    	_beep(ser)

	return 0


if __name__ == '__main__':
	raise SystemExit(main())
