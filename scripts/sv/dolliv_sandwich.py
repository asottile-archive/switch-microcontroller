from __future__ import annotations

import argparse
import datetime
import os

import cv2
import numpy
import serial

from scripts._alarm import alarm
from scripts._clock import clock
from scripts._clock import States
from scripts._reset import reset
from scripts._timeout import Timeout
from scripts.engine import all_match
from scripts.engine import always_matches
from scripts.engine import Color
from scripts.engine import do
from scripts.engine import make_vid
from scripts.engine import match_px
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import Wait
from scripts.sv._bootup import bootup


def rain(frame: numpy.ndarray) -> bool:
    tl = Point(y=191, x=963).norm(frame.shape)
    br = Point(y=329, x=1171).norm(frame.shape)

    crop = frame[tl.y:br.y, tl.x:br.x]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, (0, 0, 125), (180, 255, 255))
    count = int(numpy.count_nonzero(mask))
    if count >= 10:
        print(f'rain! {count=}')
        return True
    else:
        return False


def dolliv_shiny(frame: numpy.ndarray) -> bool:
    tl = Point(y=315, x=748).norm(frame.shape)
    br = Point(y=351, x=810).norm(frame.shape)

    crop = frame[tl.y:br.y, tl.x:br.x]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    mask_dolliv = cv2.inRange(hsv, (55, 20, 130), (65, 55, 190))
    count_dolliv = int(numpy.count_nonzero(mask_dolliv))

    mask_dark = cv2.inRange(hsv, (0, 0, 0), (180, 255, 75))
    count_dark = int(numpy.count_nonzero(mask_dark))

    if count_dolliv >= 5 and count_dark >= 3:
        print(f'shiny! {count_dolliv=} {count_dark=}')
        return True
    else:
        return False


def save(name: str, frame: numpy.ndarray) -> None:
    d = f'dolliv/{name}'
    os.makedirs(d, exist_ok=True)
    cv2.imwrite(f'{d}/{len(os.listdir(d))}.png', frame)


def ignored_pokemon(frame: numpy.ndarray) -> bool:
    tl = Point(y=315, x=748).norm(frame.shape)
    br = Point(y=351, x=810).norm(frame.shape)

    crop = frame[tl.y:br.y, tl.x:br.x]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    mask_lilligant = cv2.inRange(hsv, (160, 10, 120), (180, 100, 170))
    count_lilligant = int(numpy.count_nonzero(mask_lilligant))

    mask_hoppip = cv2.inRange(hsv, (130, 25, 100), (150, 100, 200))
    count_hoppip = int(numpy.count_nonzero(mask_hoppip))

    mask_dolliv = cv2.inRange(hsv, (55, 20, 130), (70, 55, 190))
    count_dolliv = int(numpy.count_nonzero(mask_dolliv))

    mask_dark = cv2.inRange(hsv, (0, 0, 0), (180, 255, 75))
    count_dark = int(numpy.count_nonzero(mask_dark))

    if count_lilligant > 0:
        print(f'lilligant! {count_lilligant=}')
        save('lilligant', frame)
        return True
    elif count_hoppip > 0:
        print(f'hoppip! {count_hoppip=}')
        save('hoppip', frame)
        return True
    elif count_dolliv >= 5 and count_dark < 3:
        print(f'dolliv! {count_dolliv=} {count_dark=}')
        save('dolliv', frame)
        return True
    else:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--quiet', action='store_true'),
    args = parser.parse_args()

    picnic_timer = Timeout()
    reset_timer = Timeout()

    picnic = match_px(Point(y=292, x=1085), Color(b=30, g=185, r=210))

    states: States = {
        **clock(datetime.datetime(2023, 7, 5, 6, 56), 'INITIAL', 'START'),
        **bootup('START', 'OPEN_MENU', 'INITIAL'),
        'OPEN_MENU': (
            (
                always_matches,
                do(Press('X'), Wait(1), Press('d'), Wait(1)),
                'TO_PICNIC',
            ),
        ),
        'TO_PICNIC': (
            (picnic, do(), 'MAKE_SANDWICH'),
            (always_matches, do(Press('s'), Wait(.5)), 'TO_PICNIC'),
        ),
        'MAKE_SANDWICH': (
            (
                always_matches,
                do(
                    # press A on picnic menu
                    Wait(1), Press('A'), Wait(10),
                    # walk up to picnic
                    Press('w', duration=.5),
                    # sandwich time
                    Press('A'), Wait(1.5), Press('A'), Wait(5),
                    # creative
                    Press('X'), Wait(1),
                    # lettuce
                    Press('A'), Wait(.5),
                    Press('+'), Wait(.75),
                    # sour
                    Press('w'), Wait(.5),
                    Press('w'), Wait(.5),
                    Press('w'), Wait(.5),
                    Press('A'), Wait(.5),
                    # salty
                    Press('w'), Wait(.5),
                    Press('A'), Wait(.5),
                    Press('+'), Wait(.75),
                    # select pick
                    Press('A'), Wait(10),
                    # lettuce 1
                    Press('w', duration=1),
                    Press('s', duration=.2),
                    Press('@', duration=.5),
                    Wait(1),
                    # lettuce 2
                    Press('w', duration=1),
                    Press('s', duration=.2),
                    Press('@', duration=.5),
                    Wait(1),
                    # lettuce 3
                    Press('w', duration=1),
                    Press('s', duration=.2),
                    Press('@', duration=.5),
                    Wait(3),
                    # bread
                    Press('A'), Wait(3),
                    # pick
                    Press('A'), Wait(10),
                    # confirm
                    Press('A'), Wait(25),
                    # noice
                    Press('A'), Wait(5),
                    reset_timer.after(29 * 60),
                ),
                'CLOSE_PICNIC',
            ),
        ),
        'CLOSE_PICNIC': (
            (
                all_match(
                    match_px(Point(y=417, x=1073), Color(b=22, g=198, r=229)),
                    match_px(Point(y=575, x=850), Color(b=49, g=43, r=30)),
                ),
                do(Press('A'), Wait(2.5), picnic_timer.after(7)),
                'WAIT',
            ),
            (
                match_text(
                    'Pack Up and Go',
                    Point(y=667, x=75),
                    Point(y=690, x=196),
                    invert=True,
                ),
                do(Press('Y'), Wait(.5)),
                'CLOSE_PICNIC',
            ),
        ),
        'WAIT': (
            (reset_timer.expired, reset, 'INITIAL'),
            (rain, reset, 'INITIAL'),
            (ignored_pokemon, do(), 'OPEN_PICNIC'),
            (dolliv_shiny, Press('H'), 'ALARM'),
            (picnic_timer.expired, do(), 'OPEN_PICNIC'),
        ),
        'OPEN_PICNIC': (
            (picnic, Press('A'), 'CLOSE_PICNIC'),
            (always_matches, do(Press('X'), Wait(1)), 'OPEN_PICNIC'),
        ),
        **alarm('ALARM', quiet=args.quiet),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=make_vid(), ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
