from __future__ import annotations

import argparse
import json
import os

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
    parser.add_argument('--save', required=True)
    args = parser.parse_args()

    vid = make_vid()

    os.makedirs(args.save, exist_ok=True)
    save_json = os.path.join(args.save, 't.json')
    if os.path.exists(save_json):
        with open(save_json) as f:
            contents = json.load(f)
        tl = Point(*contents['tl'])
        br = Point(*contents['br'])
    else:
        print('select the area to search by drawing a box')
        tl, br = request_box(vid)
        with open(save_json, 'w') as f:
            json.dump({'tl': tl, 'br': br}, f)

    i = 0
    seen = [
        cv2.imread(os.path.join(args.save, fname))
        for fname in os.listdir(args.save)
        if fname.endswith('.png')
    ]

    def check(frame: numpy.ndarray) -> bool:
        nonlocal i
        i += 1
        print(f' (seen={len(seen)}, n={i}) '.center(79, '='))
        crop = frame[tl.y:br.y, tl.x:br.x]
        for img in seen:
            if numpy.array_equal(img, crop):
                print('already seen!')
                return True

        do(Press('!'), Wait(.1), Press('.'))(vid, ser)
        try:
            input('is this the right raid? (enter to skip, ^D to exit)')
        except (EOFError, KeyboardInterrupt):
            print('\nbye!')
            raise SystemExit(0)
        else:
            seen.append(crop)
            cv2.imwrite(os.path.join(args.save, f'{len(seen)}.png'), crop)
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
                    Press('H'), Wait(1), Press('H'), Wait(4),
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
