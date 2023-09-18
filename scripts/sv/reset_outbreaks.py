from __future__ import annotations

import argparse

import cv2
import numpy
import serial

from scripts.engine import do
from scripts.engine import make_vid
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import request_box
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    args = parser.parse_args()

    vid = make_vid()

    print('select the area to search by drawing a box')
    tl, br = request_box(vid)

    i = 0
    masks = 0
    clean: numpy.ndarray | None = None
    mask = numpy.zeros((br.y - tl.y, br.x - tl.x), dtype=numpy.uint8)

    def _is_clean() -> bool:
        while True:
            try:
                s = input('clean? (y/n) ').lower()
            except (EOFError, KeyboardInterrupt):
                print('\nbye!')
                raise SystemExit()
            else:
                if s not in 'yn':
                    print(f'say what? {s=}')
                else:
                    return s == 'y'

    def check(frame: numpy.ndarray) -> bool:
        nonlocal clean, i, masks, mask
        i += 1
        print(f' (masks={masks}, n={i}) '.center(79, '='))

        crop = frame[tl.y:br.y, tl.x:br.x]

        if clean is None:
            do(Press('!'), Wait(.1), Press('.'))(vid, ser)
            if _is_clean():
                clean = crop
            return True

        crop = cv2.bitwise_and(crop, crop, mask=cv2.bitwise_not(mask))

        cv2.imwrite('clean.png', clean)
        cv2.imwrite('cand.png', crop)

        diff = cv2.absdiff(clean, crop)
        m = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, m = cv2.threshold(m, 12, 255, cv2.THRESH_BINARY)

        if not numpy.count_nonzero(m):
            print('already seen!')
            return True

        do(Press('!'), Wait(.1), Press('.'))(vid, ser)
        if _is_clean():
            if numpy.count_nonzero(m) in {0, mask.size}:
                print('ignoring mask (whole image?')
                return True

            masks += 1

            clean = cv2.bitwise_and(clean, clean, mask=cv2.bitwise_not(m))
            mask = cv2.bitwise_or(mask, m)

            kernel = numpy.ones((2, 2), numpy.uint8)
            m = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            clean = cv2.bitwise_and(clean, clean, mask=cv2.bitwise_not(m))
            mask = cv2.bitwise_or(mask, m)

        return True

    states: States = {
        'INITIAL': (
            (
                match_text(
                    'Map',
                    Point(y=89, x=224),
                    Point(y=125, x=280),
                    invert=False,
                ),
                do(
                    Press('H'), Wait(1),
                    Press('s'),
                    Press('d', duration=.55),
                    Press('A'), Wait(1),
                    Press('s', duration=1.3),
                    Press('A'), Wait(.75),
                    Press('s', duration=.7),
                    Press('A'), Wait(.75),
                    Press('s'), Press('s'),
                    Press('A'), Wait(.75),
                    Press('d'), Press('w'),
                    Press('d', duration=.6), Wait(.2), Press('A'), Wait(.75),
                    Press('H'), Wait(1), Press('H'), Wait(2),
                    Press('Y'), Wait(1),
                    Press('Y'), Wait(2),
                    Press('l'), Wait(1),
                ),
                'CONFIRM',
            ),
        ),
        'CONFIRM': ((check, do(), 'INITIAL'),),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=vid, ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
