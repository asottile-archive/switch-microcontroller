from __future__ import annotations

import argparse

import cv2
import numpy
import serial

from scripts._alarm import alarm
from scripts.engine import Action
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
from scripts.engine import States
from scripts.engine import Wait


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument('--detect-alpha', action='store_true')
    args = parser.parse_args()

    hp_world = match_px(Point(y=694, x=1118), Color(b=133, g=228, r=63))
    hp_battle = match_px(Point(y=663, x=181), Color(b=124, g=223, r=59))

    def orient(direction: str) -> Action:
        return do(
            Press(direction, duration=.2), Wait(.5),
            Press('l', duration=.2), Wait(.5),
        )

    def battle(start: str, end: str) -> States:
        def is_alpha(frame: numpy.ndarray) -> bool:
            crop = frame[97:111, 962:978]
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            thres = cv2.inRange(hsv, (168, 25, 25), (180, 255, 255))
            count = numpy.count_nonzero(thres)
            print(f'red pixels: {count}')
            return args.detect_alpha and count > 0

        def is_shiny(frame: numpy.ndarray) -> bool:
            crop = frame[92:117, 929:957]
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            thres = cv2.inRange(hsv, (0, 0, 0), (255, 255, 215))
            count = numpy.count_nonzero(thres)
            print(f'dark pixels: {count}')
            return count > 0

        return {
            start: (
                (hp_world, do(), end),
                (
                    all_match(
                        hp_battle,
                        match_text(
                            'L',
                            Point(y=667, x=1015),
                            Point(y=681, x=1030),
                            invert=False,
                        ),
                    ),
                    do(Wait(.5), Press('+'), Wait(1), Press('R'), Wait(1)),
                    f'{start}_CHECK_SHINY',
                ),
            ),
            f'{start}_CHECK_SHINY': (
                (is_alpha, do(), 'ALARM'),
                (is_shiny, do(), 'ALARM'),
                (
                    always_matches,
                    do(
                        Press('B'), Wait(1),
                        Press('B'), Wait(1),
                        Press('A'), Wait(1),
                    ),
                    'MAP_BACK',
                ),
            ),
        }

    states: States = {
        'INITIAL': (
            (
                all_match(
                    match_px(Point(y=532, x=46), Color(b=202, g=227, r=231)),
                    match_px(Point(y=621, x=78), Color(b=204, g=227, r=229)),
                    match_px(Point(y=677, x=80), Color(b=198, g=228, r=229)),
                    match_text(
                        'L',
                        Point(y=667, x=1013),
                        Point(y=683, x=1030),
                        invert=False,
                    ),
                    match_text(
                        'R',
                        Point(y=667, x=1229),
                        Point(y=685, x=1244),
                        invert=False,
                    ),
                ),
                do(),
                'SWITCH_TO_POKEMON',
            ),
        ),
        'SWITCH_TO_POKEMON': (
            (hp_world, do(Press('s', duration=1.25), Wait(1)), 'TO_TRAVEL'),
            (always_matches, do(Press('X'), Wait(.75)), 'SWITCH_TO_POKEMON'),
        ),
        'TO_TRAVEL': (
            (
                match_text(
                    'Ress',
                    Point(y=519, x=394),
                    Point(y=541, x=443),
                    invert=True,
                ),
                do(Press('A'), Wait(1)),
                'TO_TRAVEL',
            ),
            (always_matches, do(), 'WAIT_FOR_MAP'),
        ),
        'WAIT_FOR_MAP': (
            (
                all_match(
                    match_px(Point(y=267, x=304), Color(b=147, g=163, r=99)),
                    match_px(Point(y=238, x=207), Color(b=190, g=215, r=217)),
                    match_px(Point(y=67, x=1093), Color(b=192, g=219, r=223)),
                    match_text(
                        'ZR',
                        Point(y=59, x=1093),
                        Point(y=76, x=1113),
                        invert=False,
                    ),
                ),
                do(),
                'MAP_TRAVEL',
            ),
        ),
        'MAP_TRAVEL': (
            (
                match_text(
                    'Coronet Highlands',
                    Point(y=54, x=70),
                    Point(y=81, x=242),
                    invert=True,
                ),
                do(
                    Press('A'), Wait(.5),
                    Press('w'), Wait(.25), Press('w'), Wait(.25),
                    Press('A'), Wait(1),
                ),
                'TREE1',
            ),
            (always_matches, do(Press('1'), Wait(.5)), 'MAP_TRAVEL'),
        ),
        'TREE1': (
            (
                hp_world,
                do(
                    Wait(1),
                    orient('z'),
                    Press('w', duration=3.75), Wait(.25),
                    orient('e'),
                    Press('r'), Wait(1),
                ),
                'BATTLE1',
            ),
        ),
        **battle('BATTLE1', 'TREE2'),
        'TREE2': (
            (
                hp_world,
                do(
                    Wait(1),
                    orient('a'),
                    Press('w', duration=5), Wait(.25),
                    orient('e'),
                    Press('w', duration=1.75), Wait(.25),
                    Press('j', duration=.3), Wait(.25),
                    Press('r'), Wait(1),
                ),
                'BATTLE2',
            ),
        ),
        **battle('BATTLE2', 'TREE3'),
        'TREE3': (
            (
                hp_world,
                do(
                    Wait(1),
                    orient('a'),
                    Press('q', duration=4),
                    Press('w', duration=3), Wait(.5),
                    Press('j', duration=.2), Wait(.5),
                    Press('r'), Wait(1),
                ),
                'BATTLE3',
            ),
        ),
        **battle('BATTLE3', 'MAP_BACK'),
        'MAP_BACK': (
            (
                hp_world,
                do(
                    Wait(1),
                    Press('-'), Wait(1),
                    Press('X'), Wait(.75),
                    Press('A'), Wait(1),
                ),
                'BACK',
            ),
        ),
        'BACK': (
            (
                hp_world,
                do(
                    Press('a', duration=5), Wait(.5),
                    Press('A'), Wait(1),
                    Press('A'), Wait(1),
                ),
                'INITIAL',
            ),
        ),
        **alarm('ALARM', quiet=args.quiet),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=make_vid(), ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
